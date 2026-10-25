"""Turns a results file (.jsonl) into numbers, a Markdown report and a CSV.

analyse() computes everything; the render_* functions only format it. All
headline severity metrics use ONE prediction per case (the majority vote
across repeats, ties going to the more severe level), so the confidence
intervals count independent cases, not repeated runs of the same case."""

import csv
import io
import json
import statistics
from collections import Counter, defaultdict

from . import scoring as S
from .cases import CASES, CATEGORIES

MAX_FOLLOW_UPS = 3


# ───────────── Loading ─────────────
def read_results(path):
    """Returns (meta, runs). `runs` maps key -> record; a later line for the
    same key replaces an earlier one (that is how a retried run wins)."""
    meta, runs = {}, {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # a half-written last line from an interrupted run
                if rec.get("type") == "meta":
                    meta = rec
                elif rec.get("type") == "run":
                    runs[rec["key"]] = rec
    except FileNotFoundError:
        pass
    return meta, runs


# ───────────── Analysis ─────────────
def _rate(k, n):
    return None if n == 0 else k / n


def analyse(meta, runs, cases=None):
    cases = CASES if cases is None else cases
    cmap = {c["id"]: c for c in cases}
    good = [r for r in runs.values() if not r.get("error") and r.get("final") and r["case_id"] in cmap]
    errors = [r for r in runs.values() if r.get("error")]
    for r in good:
        r["_checks"] = S.check_run(r, cmap[r["case_id"]], MAX_FOLLOW_UPS)

    by_case = defaultdict(list)
    for r in good:
        by_case[r["case_id"]].append(r)

    rows = []
    for c in cases:  # keep the case file's order
        rs = by_case.get(c["id"])
        if not rs:
            continue
        sevs = [r["final"].get("severity") for r in rs]
        pred = S.majority_vote(sevs)
        scored = c.get("scored", True)
        outcome = S.triage_outcome(pred, c["expected"], c.get("acceptable")) if scored else None
        rows.append({
            "id": c["id"], "category": c["category"], "language": c["language"], "region": c["region"],
            "opening": c["opening"], "expected": c.get("expected"), "acceptable": c.get("acceptable") or [],
            "scored": scored, "predicted": pred, "votes": dict(Counter(sevs)), "n_runs": len(rs),
            "followups": statistics.mean(r["followups"] for r in rs),
            "strict": outcome[0] if outcome else None, "lenient": outcome[1] if outcome else None,
            "direction": outcome[2] if outcome else None,
            "consistent": len(set(sevs)) == 1,
            "top_condition": rs[0]["_checks"]["top_condition"],
            "sources": rs[0].get("sources") or [],
            "reveal_runs": sum(1 for r in rs if r.get("revealed")),
            "hidden_flag": c.get("hidden_flag"), "pair": c.get("pair"),
            "transcript": rs[0].get("turns", []),
        })
    scored_rows = [r for r in rows if r["scored"]]

    # ── headline ──
    n = len(scored_rows)
    strict_k = sum(1 for r in scored_rows if r["strict"])
    lenient_k = sum(1 for r in scored_rows if r["lenient"])
    under_k = sum(1 for r in scored_rows if r["direction"] == "under")
    over_k = sum(1 for r in scored_rows if r["direction"] == "over")
    emerg = [r for r in scored_rows if r["expected"] == "high"]
    non_emerg = [r for r in scored_rows if r["expected"] != "high"]
    multi = [r for r in rows if r["n_runs"] >= 2]
    headline = {
        "n": n, "strict_k": strict_k, "lenient_k": lenient_k, "under_k": under_k, "over_k": over_k,
        "emerg_n": len(emerg), "emerg_k": sum(1 for r in emerg if r["predicted"] == "high"),
        "nonemerg_n": len(non_emerg), "nonemerg_k": sum(1 for r in non_emerg if r["predicted"] != "high"),
        "kappa": S.weighted_kappa([(r["expected"], r["predicted"]) for r in scored_rows]),
        "consistent_n": len(multi), "consistent_k": sum(1 for r in multi if r["consistent"]),
        "confusion": S.confusion([(r["expected"], r["predicted"]) for r in scored_rows]),
    }

    # ── by category ──
    by_cat = {}
    for cat in CATEGORIES:
        rs = [r for r in rows if r["category"] == cat]
        if not rs:
            continue
        sc = [r for r in rs if r["scored"]]
        by_cat[cat] = {
            "cases": len(rs), "scored": len(sc),
            "strict_k": sum(1 for r in sc if r["strict"]), "lenient_k": sum(1 for r in sc if r["lenient"]),
            "under_k": sum(1 for r in sc if r["direction"] == "under"),
            "over_k": sum(1 for r in sc if r["direction"] == "over"),
            "followups": statistics.mean(r["followups"] for r in rs),
        }

    # ── safety rules (per run) ──
    def rule(label, denom_fn, viol_fn, detail_fn):
        runs_d = [r for r in good if denom_fn(r["_checks"], r)]
        bad = [r for r in runs_d if viol_fn(r["_checks"], r)]
        return {"label": label, "n": len(runs_d), "violations": len(bad),
                "examples": [(r["case_id"], detail_fn(r["_checks"], r)) for r in bad[:5]]}

    safety = [
        rule("No medication advice", lambda c, r: True, lambda c, r: bool(c["med_advice"]), lambda c, r: ", ".join(c["med_advice"])),
        rule("Action types match severity", lambda c, r: True, lambda c, r: bool(c["action_problems"]), lambda c, r: "; ".join(c["action_problems"])),
        rule("Tells the patient to seek care", lambda c, r: True, lambda c, r: not c["care_guidance"], lambda c, r: "no care guidance in actions"),
        rule("High severity lists red flags", lambda c, r: r["final"].get("severity") == "high", lambda c, r: c["high_without_flags"], lambda c, r: "high severity, no red flags"),
        rule("One question at a time", lambda c, r: r["followups"] > 0, lambda c, r: bool(c["bundled_questions"]), lambda c, r: " | ".join(c["bundled_questions"])[:140]),
        rule(f"Follow-up cap respected (max {MAX_FOLLOW_UPS})", lambda c, r: True, lambda c, r: c["over_follow_up_cap"], lambda c, r: f"{c['followups']} follow-ups"),
        rule("Obvious emergencies assessed promptly", lambda c, r: c["slow_emergency"] is not None, lambda c, r: c["slow_emergency"], lambda c, r: f"{c['followups']} follow-ups"),
        rule("Valid result structure", lambda c, r: True, lambda c, r: not c["structure_ok"], lambda c, r: "missing severity, conditions or actions"),
        rule("Replies in Kiswahili (Kiswahili cases)", lambda c, r: c["lang_ok"] is not None, lambda c, r: not c["lang_ok"], lambda c, r: "reply not detected as Kiswahili"),
    ]

    # ── agentic behaviour ──
    hidden = [r for r in rows if r["hidden_flag"]]
    pairs = defaultdict(list)
    for r in rows:
        if r["pair"] and r["scored"]:
            pairs[r["pair"]].append(r)
    full_pairs = {p: m for p, m in pairs.items() if len(m) == 2}
    agentic = {
        "followups_mean": statistics.mean(r["followups"] for r in rows) if rows else None,
        "hidden_runs": sum(r["n_runs"] for r in hidden),
        "hidden_revealed": sum(r["reveal_runs"] for r in hidden),
        "pairs_n": len(full_pairs),
        "pairs_k": sum(1 for m in full_pairs.values() if all(x["lenient"] for x in m)),
    }

    # ── retrieval and regional behaviour ──
    rag = bool(meta.get("rag"))
    src_runs = [r for r in good if r["_checks"]["sources_present"] is not None]
    hit_runs = [r for r in good if r["_checks"]["source_hit"] is not None]
    top_runs = [r for r in good if r["_checks"]["top_ok"] is not None]
    retrieval = {
        "rag": rag,
        "present_n": len(src_runs), "present_k": sum(1 for r in src_runs if r["_checks"]["sources_present"]),
        "hit_n": len(hit_runs), "hit_k": sum(1 for r in hit_runs if r["_checks"]["source_hit"]),
    }
    regional = {
        "n": len(top_runs), "k": sum(1 for r in top_runs if r["_checks"]["top_ok"]),
        "rows": [(r["id"], r["region"] or "(none)", r["top_condition"], r["predicted"]) for r in rows if r["category"] == "regional"],
    }

    # ── latency ──
    totals = [r["latency_s"] for r in good if r.get("latency_s") is not None]
    per_turn = [x for r in good for x in r.get("turn_latencies", [])]
    latency = {
        "run_median": statistics.median(totals) if totals else None,
        "run_p90": sorted(totals)[min(len(totals) - 1, int(0.9 * len(totals)))] if totals else None,
        "turn_median": statistics.median(per_turn) if per_turn else None,
    }

    return {
        "meta": meta, "rows": rows, "headline": headline, "by_cat": by_cat, "safety": safety,
        "agentic": agentic, "retrieval": retrieval, "regional": regional, "latency": latency,
        "errors": [(r["case_id"], r["error"]) for r in errors],
        "n_cases": len(rows), "n_runs": len(good),
        "failures": [r for r in scored_rows if not r["lenient"]],
    }


# ───────────── Rendering ─────────────
def pct(k, n, ci=True):
    if n == 0:
        return "n/a"
    s = f"{100 * k / n:.0f}% ({k}/{n})"
    if ci:
        lo, hi = S.wilson(k, n)
        s += f" [95% CI {100 * lo:.0f}-{100 * hi:.0f}%]"
    return s


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _votes(v):
    return ", ".join(f"{k}:{n}" for k, n in v.items())


def _fmt(x, nd=1, suffix=""):
    return "n/a" if x is None else f"{x:.{nd}f}{suffix}"


def render_markdown(A):
    m, h = A["meta"], A["headline"]
    L = []
    mock = bool(m.get("mock"))
    L.append(f"# MediTECH AI evaluation: {m.get('name', '(unnamed)')}")
    if mock:
        L.append("\n> **MOCK RUN. These numbers come from a keyword stand-in, not from Gemini. "
                 "They say nothing about MediTECH AI. Do not cite them.**")
    L.append(f"\n- Model: `{m.get('model', '?')}`  |  Reference notes (RAG): **{'on' if m.get('rag') else 'off'}**"
             f"  |  Started: {m.get('started', '?')}")
    L.append(f"- Cases scored: **{h['n']}** of {A['n_cases']} run  |  Runs analysed: {A['n_runs']}"
             f"  |  Repeats per case: {m.get('repeats', '?')}")
    L.append("- **Expected severities are the author's labels and have not been clinician-reviewed.** "
             "Cases and prompt share an author, so treat results as optimistic. "
             "With this many cases the confidence intervals are wide.")

    L.append("\n## 1. Triage accuracy\n")
    L.append(_table(["Metric", "Result"], [
        ["Strict accuracy (exact match)", pct(h["strict_k"], h["n"])],
        ["Lenient accuracy (any defensible level)", pct(h["lenient_k"], h["n"])],
        ["**Emergency sensitivity** (expected high, predicted high)", pct(h["emerg_k"], h["emerg_n"])],
        ["Non-emergencies kept out of 'high'", pct(h["nonemerg_k"], h["nonemerg_n"])],
        ["**Under-triage** (below the lowest acceptable level)", pct(h["under_k"], h["n"])],
        ["Over-triage (above the highest acceptable level)", pct(h["over_k"], h["n"])],
        ["Quadratic-weighted kappa", _fmt(h["kappa"], 2)],
        ["Consistency across repeats", pct(h["consistent_k"], h["consistent_n"]) if h["consistent_n"] else "n/a (one repeat)"],
    ]))
    L.append("\nConfusion matrix (rows = expected, columns = predicted):\n")
    cm = h["confusion"]
    L.append(_table(["expected \\ predicted", "low", "medium", "high"],
                    [[g] + [cm[g][p] for p in S.LEVELS] for g in S.LEVELS]))

    L.append("\n## 2. By category\n")
    L.append(_table(["Category", "Cases", "Scored", "Strict", "Lenient", "Under", "Over", "Avg follow-ups"], [
        [cat, d["cases"], d["scored"], pct(d["strict_k"], d["scored"], False), pct(d["lenient_k"], d["scored"], False),
         d["under_k"], d["over_k"], f"{d['followups']:.1f}"] for cat, d in A["by_cat"].items()]))

    L.append("\n## 3. Safety rules (automatic checks)\n")
    L.append("_Heuristics: regular expressions and word counts. They catch obvious failures and can flag "
             "harmless sentences, so read the examples._\n")
    L.append(_table(["Rule", "Violations / runs checked", "Rate"], [
        [s["label"], f"{s['violations']} / {s['n']}", pct(s["violations"], s["n"], False)] for s in A["safety"]]))
    flagged = [s for s in A["safety"] if s["violations"]]
    if flagged:
        L.append("\nExamples of violations:\n")
        for s in flagged:
            L.append(f"- **{s['label']}**: " + "; ".join(f"{cid}: \"{d}\"" for cid, d in s["examples"]))

    a = A["agentic"]
    L.append("\n## 4. Questioning behaviour (agentic triage)\n")
    L.append(_table(["Measure", "Result"], [
        ["Average follow-up questions per case", _fmt(a["followups_mean"], 1)],
        ["Hidden red flag discovered (the assistant asked the question that reveals it)", pct(a["hidden_revealed"], a["hidden_runs"])],
        ["Hidden-flag pairs handled correctly (emergency twin AND benign twin both right)", pct(a["pairs_k"], a["pairs_n"])],
    ]))

    r = A["retrieval"]
    L.append("\n## 5. Reference notes and regional behaviour\n")
    if r["rag"]:
        L.append(_table(["Measure", "Result"], [
            ["Assessments that cite reference notes", pct(r["present_k"], r["present_n"])],
            ["Expected reference note retrieved (top 4)", pct(r["hit_k"], r["hit_n"])],
            ["Regional expectation met on the top condition", pct(A["regional"]["k"], A["regional"]["n"])],
        ]))
    else:
        L.append("Reference notes were **off** for this run, so retrieval measures are not applicable.\n")
        L.append(_table(["Measure", "Result"], [["Regional expectation met on the top condition", pct(A["regional"]["k"], A["regional"]["n"])]]))
    if A["regional"]["rows"]:
        L.append("\nTop condition per regional case:\n")
        L.append(_table(["Case", "Region", "Top condition", "Severity"], A["regional"]["rows"]))

    lat = A["latency"]
    L.append("\n## 6. Speed\n")
    L.append(f"Median time per case: {_fmt(lat['run_median'], 1, ' s')}  |  90th percentile: {_fmt(lat['run_p90'], 1, ' s')}"
             f"  |  Median per model turn: {_fmt(lat['turn_median'], 1, ' s')}")

    L.append("\n## 7. Cases to examine (not within the defensible range)\n")
    if A["failures"]:
        L.append(_table(["Case", "Category", "Expected (acceptable)", "Predicted (votes)", "Opening message"], [
            [f["id"], f["category"], f"{f['expected']} ({', '.join(f['acceptable'])})", f"{f['predicted']} ({_votes(f['votes'])})",
             f["opening"][:90] + ("..." if len(f["opening"]) > 90 else "")] for f in A["failures"]]))
        L.append("\nThe full conversation for every case is in the CSV.")
    else:
        L.append("None.")

    if A["errors"]:
        L.append("\n## 8. Runs that failed (excluded from all numbers)\n")
        L.append(_table(["Case", "Error"], [[cid, str(err)[:120]] for cid, err in A["errors"]]))
        L.append("\nRe-run the same command to retry them: finished cases are skipped.")
    return "\n".join(L) + "\n"


CSV_COLUMNS = ["id", "category", "language", "region", "expected", "acceptable", "predicted", "votes", "outcome",
               "avg_followups", "top_condition", "sources", "hidden_flag_revealed_runs", "opening", "transcript"]


def render_csv(A):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for r in A["rows"]:
        outcome = "unscored" if not r["scored"] else ("match" if r["strict"] else "acceptable" if r["lenient"] else r["direction"])
        transcript = " || ".join(f"{t['role']}: {t['text']}" for t in r["transcript"])
        w.writerow([r["id"], r["category"], r["language"], r["region"], r["expected"] or "", "/".join(r["acceptable"]),
                    r["predicted"] or "", json.dumps(r["votes"]), outcome, f"{r['followups']:.1f}", r["top_condition"],
                    "; ".join(r["sources"]), r["reveal_runs"], r["opening"], transcript])
    return buf.getvalue()


def render_comparison(A, B, name_a, name_b):
    ha, hb = A["headline"], B["headline"]

    def line(label, ka, na, kb, nb):
        ra, rb = _rate(ka, na), _rate(kb, nb)
        delta = "n/a" if ra is None or rb is None else f"{100 * (rb - ra):+.0f} pts"
        return [label, pct(ka, na, False), pct(kb, nb, False), delta]

    L = [f"# Comparison: {name_a} vs {name_b}"]
    if A["meta"].get("mock") or B["meta"].get("mock"):
        L.append("\n> **At least one run is a MOCK run. Do not cite these numbers.**")
    L.append(f"\n- A = `{name_a}` (reference notes {'on' if A['meta'].get('rag') else 'off'})"
             f"  |  B = `{name_b}` (reference notes {'on' if B['meta'].get('rag') else 'off'})")
    L.append("\n" + _table(["Metric", "A", "B", "B minus A"], [
        line("Strict accuracy", ha["strict_k"], ha["n"], hb["strict_k"], hb["n"]),
        line("Lenient accuracy", ha["lenient_k"], ha["n"], hb["lenient_k"], hb["n"]),
        line("Emergency sensitivity", ha["emerg_k"], ha["emerg_n"], hb["emerg_k"], hb["emerg_n"]),
        line("Under-triage", ha["under_k"], ha["n"], hb["under_k"], hb["n"]),
        line("Over-triage", ha["over_k"], ha["n"], hb["over_k"], hb["n"]),
        line("Hidden red flags discovered", A["agentic"]["hidden_revealed"], A["agentic"]["hidden_runs"],
             B["agentic"]["hidden_revealed"], B["agentic"]["hidden_runs"]),
        line("Regional expectation met", A["regional"]["k"], A["regional"]["n"], B["regional"]["k"], B["regional"]["n"]),
    ]))
    rows_a = {r["id"]: r for r in A["rows"] if r["scored"]}
    rows_b = {r["id"]: r for r in B["rows"] if r["scored"]}
    flips = []
    for cid in rows_a:
        if cid in rows_b and rows_a[cid]["lenient"] != rows_b[cid]["lenient"]:
            ra, rb = rows_a[cid], rows_b[cid]
            flips.append([cid, ra["category"], ra["expected"], ra["predicted"], rb["predicted"],
                          "B better" if rb["lenient"] else "A better"])
    L.append("\n## Cases where the verdict changed\n")
    L.append(_table(["Case", "Category", "Expected", f"A ({name_a})", f"B ({name_b})", "Result"], flips) if flips else "None.")
    L.append("\n_Small differences are within the confidence intervals and are not evidence that either setting is better. "
             "Look at which cases changed and why._")
    return "\n".join(L) + "\n"


# ───────────── CLI ─────────────
def main(argv=None):
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Rebuild the report for a finished (or partly finished) run.")
    p.add_argument("--name", required=True, help="run name, as given to run_eval")
    p.add_argument("--compare", help="a second run name to compare against")
    p.add_argument("--results-dir", default=str(Path(__file__).parent / "results"))
    args = p.parse_args(argv)
    d = Path(args.results_dir)
    meta, runs = read_results(d / f"{args.name}.jsonl")
    if not runs:
        raise SystemExit(f"No results found at {d / (args.name + '.jsonl')}")
    A = analyse(meta, runs)
    (d / f"{args.name}.md").write_text(render_markdown(A), encoding="utf-8")
    (d / f"{args.name}.csv").write_text(render_csv(A), encoding="utf-8", newline="")
    print(f"Wrote {d / (args.name + '.md')} and {d / (args.name + '.csv')}")
    if args.compare:
        meta_b, runs_b = read_results(d / f"{args.compare}.jsonl")
        if not runs_b:
            raise SystemExit(f"No results found for {args.compare}")
        B = analyse(meta_b, runs_b)
        out = d / f"compare-{args.name}-vs-{args.compare}.md"
        out.write_text(render_comparison(A, B, args.name, args.compare), encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
