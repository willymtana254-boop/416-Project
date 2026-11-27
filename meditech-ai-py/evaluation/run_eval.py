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
retried.

This file also holds the scripted patient (class Patient) and the keyword stand-in
for Gemini used by --mock (fake_agent, fake_retrieve)."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time


HERE = Path(__file__).parent
MAX_STEPS = 6            # opening + up to 5 answers; the server forces an assessment after 3 follow-ups
RETRIES = 3              # per request, on server errors
SLEEP = time.sleep       # replaced in tests


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_case(client, case, rag, delay=0.0, repeat=0):
    """Plays one case. Returns the run record (see report.py for its use)."""
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
    import ai

    rag = not args.no_rag
    if args.mock:
        appmod.call_gemini_agent = fake_agent
        appmod.retrieve = fake_retrieve if rag else (lambda *a, **k: [])
        model = "mock (keyword stand-in)"
    else:
        if not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("GEMINI_API_KEY is not set. Add it to .env, or use --mock for a dry run.")
        if rag and not ai.load_index():
            raise SystemExit("No reference-note index found. Run `python manage.py index` first, or use --no-rag.")
        if not rag:
            appmod.retrieve = lambda *a, **k: []
        model = ai.MODEL

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


# ==========================================================================
# SCRIPTED PATIENT  (was patient.py)
# ==========================================================================
# A scripted patient. It answers the assistant's follow-up questions from
# the case's own rules, so every run of a case sees the same answers and no
# extra model calls are needed.
#
# Order of answers: the case's `replies` (first regex match wins) -> generic
# answers (duration, temperature, age, pregnancy) -> the case's default reply
# ("No, I don't think so." unless the case sets `default_reply`).
#
# `revealed` is True when the answer given disclosed a hidden red flag, which
# lets the report measure whether the assistant asked the right question.

GENERIC = {
    "en": [
        (r"how long|since when|when did|when was|for how many|how many (days|hours|weeks)", "duration", "About two days."),
        (r"temperature|how high|degrees|thermometer|measured", None, "I have not measured it, but it feels high."),
        (r"how old|your age|what age", "age", "I am 28 years old."),
        (r"pregnan", None, "No, I am not pregnant."),
    ],
    "sw": [
        (r"muda gani|tangu lini|siku ngapi|lini ilianza|ilianza lini", "duration", "Takriban siku mbili."),
        (r"joto|kipimo|nyuzi", None, "Sijapima, lakini ninahisi joto kali."),
        (r"umri|miaka mingapi", "age", "Nina umri wa miaka 28."),
        (r"mjamzito|mimba", None, "Hapana, si mjamzito."),
    ],
}
DEFAULT_REPLY = {"en": "No, I don't think so.", "sw": "Hapana, sidhani."}


class Patient:
    def __init__(self, case: dict):
        self.case = case
        self.lang = case.get("language", "en")
        self.fired = []          # indexes of case rules that matched
        self.revealed = False    # did any answer disclose a hidden red flag?

    def reply(self, question: str) -> str:
        q = (question or "").lower()
        for i, rule in enumerate(self.case.get("replies", [])):
            if re.search(rule["when"], q, re.I):
                self.fired.append(i)
                if rule.get("reveal"):
                    self.revealed = True
                return rule["say"]
        for pattern, field, text in GENERIC[self.lang]:
            if re.search(pattern, q, re.I):
                return self.case.get(field, text) if field else text
        return self.case.get("default_reply") or DEFAULT_REPLY[self.lang]


# ==========================================================================
# MOCK MODEL  (was mock_model.py)
# ==========================================================================
# A crude stand-in for Gemini and for retrieval, used ONLY by
# `run_eval --mock` to test the harness without an API key or any cost.
#
# It is keyword-based and nothing like the real model. Its numbers mean
# nothing about MediTECH AI. run_eval marks every mock run and every mock
# report so they cannot be mistaken for real results.

_HIGH = [
    "slurred", "drooping", "crushing", "struggling to breathe", "lips look blue", "worst headache",
    "purple spots", "do not fade", "will not stop", "rock hard", "not responding", "bulging",
    "stiff neck", "neck is stiff", "very stiff", "bright light hurts", "confused and very sleepy",
    "spreads down my left arm", "spreads to my left arm", "sweating a lot", "sweating heavily",
    "hurts a lot when i cough", "hard and very tender", "moved to the lower right",
    "refused all drinks", "hard to wake", "has not passed urine", "cold and blotchy",
    "few words at a time", "kifua", "umepinda", "shingo ngumu", "visivyofifia",
]
_MEDIUM = ["fever", "homa", "diarrhoea", "kuharisha", "cough", "burns when i pass urine", "ear pain",
           "sore throat", "wheezing", "spreading", "chills", "rash", "kikohozi"]
_QUESTIONS = [
    ("headache", "Is your neck stiff?", "Una shingo ngumu?"),
    ("chest", "Does the discomfort spread to your arm or jaw?", "Maumivu yanasambaa hadi mkono au taya?"),
    ("stomach pain", "Does it hurt more when you cough or move?", "Inauma zaidi unapokohoa au kusogea?"),
    ("year-old", "Is she drinking and alert?", "Anakunywa na yuko macho?"),
]


def _history_text(history):
    return " ".join(p.get("text", "") for m in history if m.get("role") == "user" for p in m.get("parts", [])).lower()


def _asked(history):
    return sum(
        1 for m in history if m.get("role") == "model"
        and any(p.get("functionCall", {}).get("name") == "ask_follow_up" for p in m.get("parts", []))
    )


def fake_agent(history, retrieved_context="", extra_instructions=""):
    sw = "Kiswahili" in extra_instructions
    raw = _history_text(history)
    # drop negated clauses ("no rash", "No, my neck is fine") before keyword matching
    text = re.sub(r"\b(no|not|without|hakuna|hapana)\b[^.,;]{0,40}", " ", raw)
    high = any(k in text for k in _HIGH)
    medium = any(k in text for k in _MEDIUM)
    asked = _asked(history)

    if not high and asked == 0:
        for key, q_en, q_sw in _QUESTIONS:
            if key in text and (medium or key != "year-old"):
                q = q_sw if sw else q_en
                return (
                    {"kind": "question", "question": q, "reason": "mock"},
                    {"role": "model", "parts": [{"functionCall": {"name": "ask_follow_up", "args": {"question": q}}}]},
                )

    severity = "high" if high else "medium" if medium else "low"
    endemic = any(k in extra_instructions for k in ("coastal Kenya", "Lake Victoria")) or "kilifi" in text
    if severity == "high":
        conditions = [{"name": "Emergency condition (mock)", "likelihood": "high", "description": "Mock description."}]
        actions = [{"type": "urgent", "text": "Hospitali haraka, nenda sasa." if sw else "Go to the nearest emergency room now."},
                   {"type": "urgent", "text": "Piga simu ya dharura." if sw else "Call an ambulance if you can."}]
        flags = ["Dalili hatari zimeripotiwa" if sw else "Emergency warning signs reported"]
    else:
        top = "Malaria" if (endemic and "fever" in text) else ("Viral infection (mock)" if medium else "Minor self-limiting problem (mock)")
        conditions = [{"name": top, "likelihood": "high" if medium else "medium", "description": "Mock description."},
                      {"name": "Something else (mock)", "likelihood": "low", "description": "Mock description."}]
        if severity == "medium":
            actions = [{"type": "soon", "text": "Mwone daktari ndani ya siku 1 hadi 3." if sw else "See a clinician within 1-3 days."},
                       {"type": "self", "text": "Pumzika na unywe maji mengi." if sw else "Rest and drink plenty of fluids."}]
        else:
            actions = [{"type": "self", "text": "Pumzika na unywe maji mengi." if sw else "Rest and drink plenty of fluids."},
                       {"type": "soon", "text": "Mwone daktari kama haipungui." if sw else "See a clinician if it does not improve."}]
        flags = []
    return (
        {"kind": "assessment", "severity": severity, "redFlags": flags, "conditions": conditions, "actions": actions},
        {"role": "model", "parts": [{"functionCall": {"name": "provide_assessment", "args": {}}}]},
    )


_SOURCES = [
    ("slurred|drooping|umepinda", "Stroke"), ("chest|kifua", "Heart attack"),
    ("stiff|purple|shingo", "Meningitis"), ("fever|chills|homa", "Malaria"),
    ("diarrh|kuharisha", "Gastroenteritis (stomach flu / food poisoning)"),
    ("runny nose|mafua|sneez", "Common cold / upper respiratory infection"),
    ("burns when i pass", "Urinary tract infection"), ("headache|kichwa", "Tension-type headache"),
]


def fake_retrieve(text, k=4):
    t = (text or "").lower()
    out = [{"title": title, "text": "mock"} for pattern, title in _SOURCES if re.search(pattern, t)]
    return out[:k]


if __name__ == "__main__":
    main()
