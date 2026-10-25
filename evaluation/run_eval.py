"""Runs the evaluation cases through the real MediTECH AI pipeline.

    python -m evaluation.run_eval --name baseline
    python -m evaluation.run_eval --name no-rag --no-rag
    python -m evaluation.report --name baseline --compare no-rag
    python -m evaluation.run_eval --mock            (dry run, no API key, no cost)

Each case is played through POST /api/chat exactly as the browser does it:
the scripted patient sends the opening message, answers each follow-up, and
the run ends when the assistant gives its assessment. Retrieval, the prompt
rules, language and region handling are all the real ones.

Results are appended to results/<name>.jsonl after EVERY run, so an
interrupted run (network drop, rate limit, Ctrl+C) loses nothing: run the
same command again and finished cases are skipped. Runs that errored are
retried."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
MAX_STEPS = 6            # opening + up to 5 answers; the server forces an assessment after 3 follow-ups
RETRIES = 3              # per request, on server errors
SLEEP = time.sleep       # replaced in tests


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_case(client, case, rag, delay=0.0, repeat=0):
    """Plays one case. Returns the run record (see report.py for its use)."""
    from .patient import Patient

    patient = Patient(case)
    rec = {"type": "run", "key": f"{case['id']}#{repeat}", "case_id": case["id"], "repeat": repeat,
           "rag": rag, "turns": [], "followups": 0, "final": None, "sources": [], "revealed": False,
           "fired": [], "error": None, "latency_s": None, "turn_latencies": [], "ts": now_iso()}
    history, message = [], case["opening"]
    started = time.time()

    for _ in range(MAX_STEPS):
        body = {"history": history, "message": message, "language": case["language"], "region": case["region"] or None}
        data, status, took = None, None, 0.0
        for attempt in range(RETRIES + 1):
            t0 = time.time()
            resp = client.post("/api/chat", json=body)
            took = time.time() - t0
            status, data = resp.status_code, resp.get_json(silent=True) or {}
            if status == 200 or status < 500:
                break
            SLEEP(2 ** (attempt + 1))  # 2s, 4s, 8s on a server/model error
        rec["turn_latencies"].append(round(took, 2))
        if delay:
            SLEEP(delay)
        if status != 200:
            rec["error"] = f"HTTP {status}: {data.get('error', 'no detail')}"
            break

        history = data["history"]
        rec["turns"].append({"role": "user", "text": message})
        turn = data["turn"]
        if turn["kind"] == "question":
            rec["turns"].append({"role": "assistant", "text": turn["question"]})
            rec["followups"] += 1
            message = patient.reply(turn["question"])
        else:
            rec["final"] = {k: turn.get(k) for k in ("severity", "redFlags", "conditions", "actions")}
            rec["sources"] = data.get("sources", [])
            break
    else:
        rec["error"] = f"no assessment after {MAX_STEPS} steps"

    rec["revealed"], rec["fired"] = patient.revealed, patient.fired
    rec["latency_s"] = round(time.time() - started, 2)
    return rec


def build_parser():
    p = argparse.ArgumentParser(description="Run the evaluation cases through MediTECH AI.")
    p.add_argument("--name", default="baseline", help="name of this run (results/<name>.jsonl)")
    p.add_argument("--repeats", type=int, default=1, help="runs per case (the model is not deterministic)")
    p.add_argument("--category", action="append", help="only these categories (repeatable)")
    p.add_argument("--ids", help="comma-separated case ids, e.g. EM-01,HF-01A")
    p.add_argument("--limit", type=int, help="only the first N selected cases")
    p.add_argument("--no-rag", action="store_true", help="turn reference-note retrieval off (ablation)")
    p.add_argument("--delay", type=float, default=0.5, help="seconds to wait after every API call")
    p.add_argument("--mock", action="store_true", help="dry run with a keyword stand-in for the model")
    p.add_argument("--report-only", action="store_true", help="skip running, rebuild the report from saved results")
    p.add_argument("--results-dir", default=str(HERE / "results"))
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    name = args.name if not args.mock or args.name.endswith("-mock") else args.name + "-mock"
    path = results_dir / f"{name}.jsonl"

    from . import report
    from .cases import get_cases, validate

    validate()
    if not args.report_only:
        _run(args, name, path, results_dir, get_cases)

    meta, runs = report.read_results(path)
    if not runs:
        raise SystemExit(f"No results at {path}")
    A = report.analyse(meta, runs)
    (results_dir / f"{name}.md").write_text(report.render_markdown(A), encoding="utf-8")
    (results_dir / f"{name}.csv").write_text(report.render_csv(A), encoding="utf-8", newline="")
    h = A["headline"]
    print(f"\nReport: {results_dir / (name + '.md')}\nCSV:    {results_dir / (name + '.csv')}")
    print(f"Scored {h['n']} cases | strict {h['strict_k']}/{h['n']} | lenient {h['lenient_k']}/{h['n']} | "
          f"emergencies caught {h['emerg_k']}/{h['emerg_n']} | under-triaged {h['under_k']}")
    if meta.get("mock"):
        print("MOCK RUN: these numbers are not from the real model.")
    return A


def _run(args, name, path, results_dir, get_cases):
    # The app reads these when it is imported, so set them first. Evaluation
    # uses a throwaway database and never touches your real accounts.
    os.environ["MEDITECH_DB"] = str(results_dir / ".eval.db")
    os.environ.setdefault("SECRET_KEY", "evaluation-only-secret-key-not-for-real-use")
    from dotenv import load_dotenv

    load_dotenv()
    sys.path.insert(0, str(HERE.parent))
    import app as appmod
    import gemini_client
    import retrieval

    rag = not args.no_rag
    if args.mock:
        from . import mock_model

        appmod.call_gemini_agent = mock_model.fake_agent
        appmod.retrieve = mock_model.fake_retrieve if rag else (lambda *a, **k: [])
        model = "mock (keyword stand-in)"
    else:
        if not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("GEMINI_API_KEY is not set. Add it to .env, or use --mock for a dry run.")
        if rag and not retrieval.load_index():
            raise SystemExit("No reference-note index found. Run `python build_index.py` first, or use --no-rag.")
        if not rag:
            appmod.retrieve = lambda *a, **k: []
        model = gemini_client.MODEL

    from . import report

    meta_old, runs_old = report.read_results(path)
    wanted = {"rag": rag, "mock": bool(args.mock), "model": model}
    if meta_old and any(meta_old.get(k) != v for k, v in wanted.items()):
        raise SystemExit(f"{path.name} was started with different settings ({ {k: meta_old.get(k) for k in wanted} }). "
                         "Use a new --name rather than mixing runs.")

    cases = get_cases(args.category, set(args.ids.split(",")) if args.ids else None, args.limit)
    if not cases:
        raise SystemExit("No cases match those filters.")
    if not meta_old:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "meta", "name": name, "started": now_iso(), "repeats": args.repeats, **wanted}) + "\n")

    client = appmod.app.test_client()
    todo = [(c, r) for c in cases for r in range(args.repeats)
            if f"{c['id']}#{r}" not in runs_old or runs_old[f"{c['id']}#{r}"].get("error")]
    skipped = len(cases) * args.repeats - len(todo)
    print(f"{name}: {len(todo)} run(s) to do" + (f", {skipped} already finished" if skipped else "")
          + f" | model: {model} | reference notes: {'on' if rag else 'off'}" + (" | MOCK" if args.mock else ""))
    try:
        for i, (case, rep) in enumerate(todo, 1):
            rec = run_case(client, case, rag, args.delay, rep)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            verdict = rec["error"] or f"{rec['final']['severity']:<6} ({rec['followups']} follow-up{'s' if rec['followups'] != 1 else ''}, {rec['latency_s']}s)"
            print(f"[{i}/{len(todo)}] {rec['key']:<10} expected {str(case.get('expected', '-')):<6} -> {verdict}")
    except KeyboardInterrupt:
        print("\nInterrupted. Progress is saved: run the same command to continue.")


if __name__ == "__main__":
    main()
