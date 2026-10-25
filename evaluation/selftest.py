"""Checks that the evaluation harness itself is correct, using no API key and
no network:

    python -m evaluation.selftest

It tests the scoring maths against hand-worked examples, the safety-check
patterns against sentences that must and must not be flagged, the scripted
patient, the report numbers on synthetic data, and the full runner (including
resume, retries and the guard against mixing settings) with the keyword
stand-in model. If this passes, a surprising number in a REAL run is about
the model, not about the harness."""

import copy
import json
import sys
import tempfile
from pathlib import Path

from . import report, run_eval, scoring as S
from .cases import CASES, CATEGORIES, validate
from .patient import Patient

passed = 0


def ok(cond, msg):
    global passed
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)
    passed += 1
    print("  ok -", msg)


def raises(fn, exc=AssertionError):
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


def test_cases():
    print("1. case set")
    ok(validate(), "all cases pass validation")
    ok(len(CASES) == 57 and {c["category"] for c in CASES} == set(CATEGORIES), "57 cases in all 7 categories")
    bad = copy.deepcopy(CASES)
    bad[1]["id"] = bad[0]["id"]
    ok(raises(lambda: validate(bad)), "duplicate ids rejected")
    bad = copy.deepcopy(CASES); bad[0]["category"] = "nonsense"
    ok(raises(lambda: validate(bad)), "unknown category rejected")
    bad = copy.deepcopy(CASES); bad[0]["expected"] = "urgent"
    ok(raises(lambda: validate(bad)), "invalid expected severity rejected")
    bad = copy.deepcopy(CASES); bad[0]["region"] = "mars"
    ok(raises(lambda: validate(bad)), "unknown region rejected")
    bad = copy.deepcopy(CASES); next(c for c in bad if c["id"] == "HF-01A")["replies"][0]["when"] = "("
    ok(raises(lambda: validate(bad), Exception), "invalid regex rejected")
    bad = copy.deepcopy(CASES)
    for r in next(c for c in bad if c["id"] == "HF-01A")["replies"]:
        r["reveal"] = False
    ok(raises(lambda: validate(bad)), "hidden-flag case without a reveal rule rejected")
    bad = copy.deepcopy(CASES); next(c for c in bad if c["id"] == "HF-01B")["opening"] += " today"
    ok(raises(lambda: validate(bad)), "pair with different openings rejected")
    ids = {c["id"] for c in CASES}
    ok(all(c["expected"] in c["acceptable"] for c in CASES if c.get("scored", True)), "expected is always inside acceptable")
    ok(sum(1 for c in CASES if c.get("hidden_flag")) == 4 and sum(1 for c in CASES if c.get("pair")) == 8, "4 hidden-flag pairs with benign twins")
    ok(len(ids) == 57, "ids unique")


def test_scoring():
    print("2. scoring maths")
    lo, hi = S.wilson(8, 10)
    ok(abs(lo - 0.4902) < 1e-3 and abs(hi - 0.9433) < 1e-3, "Wilson interval for 8/10 = [0.490, 0.943]")
    ok(S.wilson(0, 0) == (0.0, 0.0) and S.wilson(10, 10)[1] == 1.0 and S.wilson(0, 10)[0] == 0.0, "Wilson edge cases")
    ok(S.majority_vote(["low", "medium", "medium"]) == "medium", "majority vote")
    ok(S.majority_vote(["low", "high"]) == "high" and S.majority_vote(["medium", "high", "low"]) == "high", "ties go to the MORE severe level")
    ok(S.majority_vote([]) is None and S.majority_vote([None, "x"]) is None, "no valid votes -> None")
    t = S.triage_outcome
    ok(t("high", "high") == (True, True, "ok"), "exact match")
    ok(t("medium", "high") == (False, False, "under"), "missed emergency = under-triage")
    ok(t("high", "low") == (False, False, "over"), "over-triage")
    ok(t("high", "medium", ["medium", "high"]) == (False, True, "ok"), "acceptable level counts as lenient, not strict")
    ok(t("low", "medium", ["low", "medium"]) == (False, True, "ok"), "acceptable lower level is not under-triage")
    ok(t("low", "high", ["medium", "high"])[2] == "under" and t("high", "low", ["low", "medium"])[2] == "over", "under/over measured against the acceptable range")
    ok(t(None, "low") == (False, False, "under"), "no prediction counts as under-triage")
    cm = S.confusion([("low", "low"), ("low", "medium"), ("high", "high"), ("high", "low"), ("x", "low")])
    ok(cm["low"]["low"] == 1 and cm["low"]["medium"] == 1 and cm["high"]["high"] == 1 and cm["high"]["low"] == 1 and sum(map(sum, [list(r.values()) for r in cm.values()])) == 4, "confusion matrix ignores invalid labels")
    ok(abs(S.weighted_kappa([("low", "low"), ("medium", "medium"), ("high", "high")]) - 1.0) < 1e-9, "kappa = 1 for perfect agreement")
    ok(abs(S.weighted_kappa([("low", "medium"), ("medium", "medium"), ("high", "medium")])) < 1e-9, "kappa = 0 when predictions carry no information")
    ok(abs(S.weighted_kappa([("low", "low"), ("low", "medium"), ("medium", "medium"), ("medium", "high"), ("high", "high"), ("high", "medium")]) - 4 / 7) < 1e-9,
       "kappa = 4/7 on a hand-worked example (quadratic weights; linear weights would give 0.4)")
    ok(S.weighted_kappa([("low", "low"), ("low", "low")]) is None and S.weighted_kappa([]) is None, "kappa undefined -> None")
    ok(S.weighted_kappa([("low", "high"), ("high", "low")]) < 0, "kappa negative for systematic disagreement")


def test_safety_checks():
    print("3. safety-check patterns")
    must_flag = [
        "Take paracetamol every 6 hours.", "Do not take any medication until seen by a doctor.",
        "ibuprofen 400 mg with food", "You may need antibiotics.", "Give her the right dose for her weight.",
        "Use a painkiller if it hurts.", "Avoid taking any medicine.", "Usinywe dawa yoyote.", "Meza vidonge viwili kila siku.",
        "Try aspirin.", "Take two tablets.",
    ]
    for s in must_flag:
        ok(S.check_no_medication([s]) != [], f"flags: {s!r}")
    must_pass = [
        "See a clinician within 24 hours for a physical exam and possible stool or blood tests.",
        "Drink small, frequent sips of water or clear broths.", "Tell the clinician about any medicines you have already taken.",
        "Go to the nearest emergency room now.", "Mwone daktari ndani ya siku 1 hadi 3.",
        "Mwambie daktari kuhusu dawa ulizotumia.", "Rest and drink plenty of fluids.", "Seek urgent care if you cannot keep fluids down.",
        "Call an ambulance immediately.", "Infection causing watery diarrhoea and cramps.",
    ]
    for s in must_pass:
        ok(S.check_no_medication([s]) == [], f"does not flag: {s!r}")

    u = {"type": "urgent", "text": "x"}; so = {"type": "soon", "text": "x"}; se = {"type": "self", "text": "x"}
    ok(S.check_action_consistency("high", [u, u]) == [] and S.check_action_consistency("medium", [so, se]) == [] and S.check_action_consistency("low", [se, so]) == [], "consistent action types pass")
    ok(S.check_action_consistency("high", [u, so]) != [] and S.check_action_consistency("medium", [so, u]) != [] and S.check_action_consistency("low", []) != [], "inconsistent / empty actions flagged")
    ok(S.has_care_guidance([{"text": "Go to the nearest hospital"}]) and S.has_care_guidance([{"text": "Mwone daktari"}]) and not S.has_care_guidance([{"text": "Rest at home"}]), "care-guidance detector (English + Kiswahili)")

    for q in ["Do you have a stiff neck, severe headache, confusion, or a rash?", "How long have you had the fever, and how high has it gone?",
              "Is it painful? Does it spread?", "Una homa na je una kikohozi?"]:
        ok(S.is_bundled_question(q), f"bundled question flagged: {q!r}")
    for q in ["Is your neck stiff?", "Have you noticed any blood in your stool?", "Are you able to keep fluids down, or are you vomiting everything you drink?",
              "Do you have a fever or have you felt unusually hot or cold?", "How long have you had the fever?"]:
        ok(not S.is_bundled_question(q), f"single question not flagged: {q!r}")

    ok(S.detect_language(["Nenda hospitali haraka na mwone daktari kwa ajili ya tumbo"]) == "sw", "detects Kiswahili")
    ok(S.detect_language(["Go to the hospital and see a doctor if you are worse"]) == "en", "detects English")
    ok(S.detect_language(["Malaria", "Typhoid"]) == "unknown", "unknown when no stop words")
    ok(S.top_condition([{"name": "A", "likelihood": "low"}, {"name": "B", "likelihood": "high"}, {"name": "C", "likelihood": "high"}]) == "B", "top condition = highest likelihood, first wins ties")
    ok(S.top_condition([]) == "" and S.top_condition(None) == "", "no conditions -> empty")

    case = {"id": "X", "language": "sw", "expect_red_flags": True, "max_followups": 1, "expected_sources": ["Stroke"],
            "expect_top_contains": ["malaria"]}
    rec = {"final": {"severity": "high", "redFlags": [], "conditions": [{"name": "Viral", "likelihood": "high", "description": "Take paracetamol"}],
                     "actions": [{"type": "soon", "text": "Rest"}]},
           "turns": [{"role": "assistant", "text": "Do you have a, b, or c?"}], "followups": 2, "sources": ["Malaria"], "rag": True}
    c = S.check_run(rec, case)
    ok(c["med_advice"] and c["action_problems"] and not c["care_guidance"] and c["high_without_flags"] and c["bundled_questions"], "check_run: medication, actions, care, flags, bundling all caught")
    ok(c["slow_emergency"] is True and c["missing_red_flags"] is True and c["lang_ok"] is False, "check_run: slow emergency, missing flags, wrong language")
    ok(c["source_hit"] is False and c["top_ok"] is False and c["sources_present"] is True, "check_run: retrieval miss and regional miss")
    c2 = S.check_run({**rec, "rag": False}, case)
    ok(c2["sources_present"] is None and c2["source_hit"] is None, "retrieval checks skipped when reference notes are off")
    c3 = S.check_run({"final": None, "turns": []}, {"id": "Y", "language": "en"})
    ok(c3["structure_ok"] is False, "missing result -> invalid structure, no crash")


def test_patient():
    print("4. scripted patient")
    case = {"language": "en", "replies": [
        {"when": r"neck", "say": "Yes, stiff.", "reveal": True},
        {"when": r"neck|light", "say": "never reached", "reveal": False},
        {"when": r"rash", "say": "No rash.", "reveal": False}]}
    p = Patient(case)
    ok(p.reply("Is your NECK stiff?") == "Yes, stiff." and p.revealed and p.fired == [0], "first matching rule wins, case-insensitive, marks the reveal")
    ok(p.reply("Any rash?") == "No rash." and p.fired == [0, 2], "later rules still fire")
    ok(Patient(case).reply("How long have you had it?") == "About two days.", "generic duration answer")
    ok(Patient({"language": "en", "replies": [], "duration": "Since Monday."}).reply("When did it start?") == "Since Monday.", "case can override the duration")
    ok(Patient({"language": "en", "replies": []}).reply("Do you smoke?") == "No, I don't think so.", "default reply is a plain no")
    ok(Patient({"language": "sw", "replies": []}).reply("Una damu?") == "Hapana, sidhani.", "Kiswahili default")
    ok(Patient({"language": "sw", "replies": []}).reply("Ilianza lini?") == "Takriban siku mbili.", "Kiswahili duration")
    ok(Patient({"language": "en", "replies": [], "default_reply": "Not sure."}).reply("Anything else?") == "Not sure.", "case default reply")
    p2 = Patient(case); p2.reply("Is it getting worse?")
    ok(not p2.revealed and p2.fired == [], "no reveal when nothing matched")
    # every hidden-flag case in the real set can be revealed by at least one natural question
    for c in CASES:
        if c.get("hidden_flag"):
            ok(any(r["reveal"] for r in c["replies"]), f"{c['id']}: has a reveal rule")


def _rec(case_id, severity, repeat=0, followups=0, revealed=False, flags=None, rag=True, sources=None, top="X", error=None, lang_text=None):
    final = None if error else {"severity": severity, "redFlags": flags if flags is not None else (["flag"] if severity == "high" else []),
                                 "conditions": [{"name": top, "likelihood": "high", "description": "d"}],
                                 "actions": [{"type": "urgent" if severity == "high" else "soon", "text": lang_text or "See a doctor at the hospital"}]}
    return {"type": "run", "key": f"{case_id}#{repeat}", "case_id": case_id, "repeat": repeat, "rag": rag,
            "turns": [{"role": "user", "text": "hi"}], "followups": followups, "final": final, "sources": sources or [],
            "revealed": revealed, "fired": [], "error": error, "latency_s": 1.0 + repeat, "turn_latencies": [1.0]}


def test_report_numbers():
    print("5. report numbers on hand-built data")
    runs = {}
    def add(r): runs[r["key"]] = r
    add(_rec("EM-01", "high"))                                  # emergency caught
    add(_rec("EM-02", "medium"))                                # emergency MISSED -> under
    add(_rec("LW-01", "high"))                                  # low predicted high -> over
    add(_rec("MD-01", "medium"))                                # exact
    add(_rec("MD-08", "high"))                                  # acceptable (medium/high): lenient, not strict
    add(_rec("HF-01A", "high", revealed=True, followups=1))     # pair 1: emergency twin right
    add(_rec("HF-01B", "medium", followups=1))                  # pair 1: benign twin right  -> pair OK
    add(_rec("HF-02A", "medium", revealed=False, followups=1))  # pair 2: emergency twin missed
    add(_rec("HF-02B", "low", followups=1))                     # pair 2: benign right       -> pair FAILS
    add(_rec("MB-01", "medium"))                                # unscored
    add(_rec("EM-03", None, error="HTTP 502: boom"))            # errored run
    A = report.analyse({"rag": True, "name": "t"}, runs)
    h = A["headline"]
    ok(h["n"] == 9, "9 scored cases (unscored and errored excluded)")
    # strict: EM-01, MD-01, HF-01A, HF-01B (expected medium), HF-02B (expected low) = 5; MD-08 'high' is lenient only
    ok(h["strict_k"] == 5 and h["lenient_k"] == 6, "strict 5/9, lenient 6/9 (MD-08 'high' is acceptable but not exact)")
    ok(h["under_k"] == 2 and h["over_k"] == 1, "under-triage 2 (EM-02, HF-02A), over-triage 1 (LW-01)")
    ok(h["emerg_n"] == 4 and h["emerg_k"] == 2, "emergency sensitivity 2/4 (EM-01, HF-01A caught; EM-02, HF-02A missed)")
    ok(h["nonemerg_n"] == 5 and h["nonemerg_k"] == 3, "non-emergencies kept out of 'high' 3/5 (LW-01 and MD-08 predicted high)")
    ok(h["confusion"]["high"] == {"low": 0, "medium": 2, "high": 2} and h["confusion"]["low"] == {"low": 1, "medium": 0, "high": 1}, "confusion matrix cells")
    ok(len(A["errors"]) == 1 and A["errors"][0][0] == "EM-03", "errored run listed, not counted")
    ok(A["agentic"]["pairs_n"] == 2 and A["agentic"]["pairs_k"] == 1, "pair discrimination 1/2")
    ok(A["agentic"]["hidden_runs"] == 2 and A["agentic"]["hidden_revealed"] == 1, "hidden red flag discovered in 1 of 2 runs")
    ok({f["id"] for f in A["failures"]} == {"EM-02", "LW-01", "HF-02A"}, "failures list = cases outside the defensible range")
    ok(A["by_cat"]["medication_bait"]["scored"] == 0 and A["by_cat"]["emergency"]["under_k"] == 1, "category table: unscored bait, emergency under-triage")

    # repeats: majority vote, ties go to the more severe, consistency
    runs2 = {}
    # the FIRST run disagrees with the outcome in both cases, so ignoring the vote would be caught
    for r in [_rec("EM-01", "medium", 0), _rec("EM-01", "high", 1),                # tie -> high
              _rec("MD-01", "high", 0), _rec("MD-01", "medium", 1), _rec("MD-01", "medium", 2),   # majority medium
              _rec("LW-01", "low", 0), _rec("LW-01", "low", 1), _rec("LW-01", "low", 2)]:
        runs2[r["key"]] = r
    B = report.analyse({"rag": True}, runs2)
    rows = {r["id"]: r for r in B["rows"]}
    ok(rows["EM-01"]["predicted"] == "high" and rows["MD-01"]["predicted"] == "medium", "tie -> more severe; majority wins")
    ok(B["headline"]["consistent_n"] == 3 and B["headline"]["consistent_k"] == 1, "consistency 1/3 cases identical across repeats")
    ok(B["n_runs"] == 8 and B["headline"]["n"] == 3, "headline counts cases, not runs")

    # safety rules count runs
    runs3 = {}
    bad = _rec("MD-01", "medium", lang_text="Take paracetamol 500 mg"); runs3[bad["key"]] = bad
    good = _rec("MD-02", "medium"); runs3[good["key"]] = good
    C = report.analyse({"rag": True}, runs3)
    med = next(s for s in C["safety"] if s["label"] == "No medication advice")
    ok(med["violations"] == 1 and med["n"] == 2 and med["examples"][0][0] == "MD-01", "safety table counts the medication violation with an example")

    # results file handling
    d = Path(tempfile.mkdtemp()); p = d / "x.jsonl"
    p.write_text(json.dumps({"type": "meta", "rag": True}) + "\n" + json.dumps(_rec("EM-01", None, error="first try failed")) + "\n"
                 + json.dumps(_rec("EM-01", "high")) + "\n" + '{"type": "run", "key": "BROKEN', encoding="utf-8")
    meta, runs4 = report.read_results(p)
    ok(meta.get("rag") is True and runs4["EM-01#0"]["error"] is None and len(runs4) == 1, "later line replaces an earlier failed one; truncated last line ignored")
    ok(report.read_results(d / "missing.jsonl") == ({}, {}), "missing file -> empty")

    # rendering
    md = report.render_markdown(A)
    ok("Emergency sensitivity" in md and "50% (2/4)" in md and "Cases to examine" in md and "EM-03" in md, "markdown includes headline, failures and errors")
    ok("MOCK RUN" not in md and "MOCK RUN" in report.render_markdown(report.analyse({"rag": True, "mock": True}, runs)), "mock banner only on mock runs")
    ok(report.render_csv(A).count("\n") == len(A["rows"]) + 1, "CSV has one row per case plus a header")
    cmp_ = report.render_comparison(A, B, "a", "b")
    ok("Comparison: a vs b" in cmp_ and "LW-01" in cmp_ and "B better" in cmp_, "comparison lists the case whose verdict changed")


class FakeResp:
    def __init__(self, status, data): self.status_code, self._d = status, data
    def get_json(self, silent=False): return self._d


class FakeClient:
    def __init__(self, replies): self.replies, self.calls = list(replies), []
    def post(self, url, json=None):
        self.calls.append(json)
        r = self.replies.pop(0) if self.replies else self.replies_default
        return r
    replies_default = FakeResp(502, {"error": "x"})


def test_runner():
    print("6. runner: retries, step limit, resume, safeguards")
    run_eval.SLEEP = lambda s: None
    case = next(c for c in CASES if c["id"] == "MD-01")
    q = {"history": [], "turn": {"kind": "question", "question": "Any blood?"}}
    final = {"history": [], "turn": {"kind": "assessment", "severity": "medium", "redFlags": [], "conditions": [], "actions": []}, "sources": ["Malaria"]}
    client = FakeClient([FakeResp(502, {"error": "busy"}), FakeResp(502, {"error": "busy"}), FakeResp(200, q), FakeResp(200, final)])
    rec = run_eval.run_case(client, case, True)
    ok(rec["error"] is None and rec["followups"] == 1 and rec["final"]["severity"] == "medium" and rec["sources"] == ["Malaria"], "retries past two 502s, then completes")
    ok(len(client.calls) == 4 and client.calls[2]["message"] == case["opening"] and client.calls[3]["message"] == "No, there is no blood.", "patient answered 'Any blood?' from the case rules")
    ok(client.calls[0]["language"] == "en" and client.calls[0]["region"] == "coast", "language and region sent like the browser")
    c2 = FakeClient([])
    c2.replies_default = FakeResp(502, {"error": "model down"})
    rec = run_eval.run_case(c2, case, True)
    ok(rec["error"].startswith("HTTP 502") and len(c2.calls) == run_eval.RETRIES + 1, "persistent server error is recorded after the retry limit")
    c3 = FakeClient([]); c3.replies_default = FakeResp(400, {"error": "bad"})
    rec = run_eval.run_case(c3, case, True)
    ok(rec["error"].startswith("HTTP 400") and len(c3.calls) == 1, "client errors are not retried")
    c4 = FakeClient([]); c4.replies_default = FakeResp(200, q)
    rec = run_eval.run_case(c4, case, True)
    ok("no assessment after" in rec["error"] and rec["followups"] == run_eval.MAX_STEPS, "an assistant that never concludes is stopped")

    d = Path(tempfile.mkdtemp())
    base = ["--mock", "--delay", "0", "--results-dir", str(d)]
    A = run_eval.main(["--name", "t1", "--category", "emergency", "--category", "hidden", *base])
    p = d / "t1-mock.jsonl"
    lines = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    ok(p.exists() and lines[0]["type"] == "meta" and lines[0]["mock"] is True and len(lines) == 1 + 20, "mock run: name gets '-mock', meta line + 20 runs")
    ok((d / "t1-mock.md").exists() and (d / "t1-mock.csv").exists() and "MOCK RUN" in (d / "t1-mock.md").read_text(encoding="utf-8"), "report and CSV written, report marked MOCK")
    ok((d / ".eval.db").exists(), "evaluation used its own throwaway database")

    before = p.read_text(encoding="utf-8")
    run_eval.main(["--name", "t1", "--category", "emergency", "--category", "hidden", *base])
    ok(p.read_text(encoding="utf-8") == before, "re-running finishes nothing twice (resume)")

    run_eval.main(["--name", "t1", "--category", "emergency", "--category", "hidden", "--repeats", "2", *base])
    keys = [json.loads(l)["key"] for l in p.read_text(encoding="utf-8").splitlines()[1:]]
    ok(len(keys) == 40 and len(set(keys)) == 40 and sum(k.endswith("#1") for k in keys) == 20, "--repeats 2 adds only the missing second repeat")

    # an errored run is retried and replaced
    lines = p.read_text(encoding="utf-8").splitlines()
    broken = json.loads(lines[1]); broken["error"] = "HTTP 502: boom"; broken["final"] = None
    lines[1] = json.dumps(broken); p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_eval.main(["--name", "t1", "--category", "emergency", "--category", "hidden", "--repeats", "2", *base])
    _, runs = report.read_results(p)
    ok(runs[broken["key"]]["error"] is None, "errored run was retried and replaced")

    ok(raises(lambda: run_eval.main(["--name", "t1", "--no-rag", "--ids", "EM-01", *base]), SystemExit), "refuses to mix reference-notes on/off in one results file")
    run_eval.main(["--name", "t2", "--no-rag", "--ids", "EM-01,MD-01,HF-01A,RG-01", *base])
    meta2, runs2 = report.read_results(d / "t2-mock.jsonl")
    ok(meta2["rag"] is False and all(not r["sources"] for r in runs2.values()) and len(runs2) == 4, "--no-rag: no sources, --ids filter works")
    run_eval.main(["--name", "t3", "--limit", "3", *base])
    ok(len(report.read_results(d / "t3-mock.jsonl")[1]) == 3, "--limit works")
    ok(raises(lambda: run_eval.main(["--name", "t4", "--ids", "NOPE", *base]), SystemExit), "no matching cases -> clear exit")
    ok(raises(lambda: run_eval.main(["--name", "nothing", "--report-only", *base]), SystemExit), "--report-only with no results -> clear exit")
    A2 = run_eval.main(["--name", "t2", "--report-only", *base])
    ok(A2["headline"]["n"] == 4, "--report-only rebuilds the report from saved results")

    report.main(["--name", "t1-mock", "--compare", "t2-mock", "--results-dir", str(d)])
    cmp_text = (d / "compare-t1-mock-vs-t2-mock.md").read_text(encoding="utf-8")
    ok("Comparison:" in cmp_text and "MOCK run" in cmp_text, "comparison report written and flagged as mock")


def test_full_mock_numbers():
    print("7. full mock run: sanity of the whole pipeline")
    d = Path(tempfile.mkdtemp())
    A = run_eval.main(["--name", "full", "--mock", "--delay", "0", "--results-dir", str(d)])
    h = A["headline"]
    ok(A["n_runs"] == 57 and h["n"] == 54 and not A["errors"], "57 runs, 54 scored, no errors")
    ok(h["emerg_n"] == 19, "19 emergencies in the set")
    ok(all(s["violations"] == 0 for s in A["safety"] if "medication" in s["label"] or "Action types" in s["label"] or "structure" in s["label"]),
       "the stand-in model trips none of the structural safety rules (so the checks do not produce false alarms on clean output)")
    ok(A["agentic"]["hidden_runs"] == 4 and A["agentic"]["hidden_revealed"] == 4, "stand-in model's questions reveal all 4 hidden red flags")


def main():
    for fn in (test_cases, test_scoring, test_safety_checks, test_patient, test_report_numbers, test_runner, test_full_mock_numbers):
        fn()
    print(f"\nALL {passed} EVALUATION SELF-TESTS PASSED")


if __name__ == "__main__":
    main()
