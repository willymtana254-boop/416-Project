# MediTECH AI evaluation harness (Phase 6)

Runs 57 test cases through your real pipeline (`/api/chat`: retrieval, prompt
rules, language and region handling) and measures how well the triage works.

## Quick start

Run these from the project folder (the one that contains `app.py`), with the
virtual environment active.

```powershell
python -m evaluation.selftest                 # 1. checks the harness itself (no key, no network)
python -m evaluation.run_eval --mock          # 2. dry run of the whole pipeline (fake model, no cost)
python -m evaluation.run_eval --name baseline # 3. the real run (needs GEMINI_API_KEY and the index)
```

Then open `evaluation\results\baseline.md` (the report) and `baseline.csv`
(every case with its full conversation).

For the report chapter, run these:

```powershell
python -m evaluation.run_eval --name baseline --repeats 3
python -m evaluation.run_eval --name no-rag --no-rag --repeats 3
python -m evaluation.report --name baseline --compare no-rag
```

The last command writes `compare-baseline-vs-no-rag.md`: the same cases with
reference-note retrieval on and off, and which verdicts changed.

## Options

| Option | Meaning |
|---|---|
| `--name` | name of the run; results go to `results\<name>.jsonl` |
| `--repeats N` | run each case N times (the model is not deterministic) |
| `--category`, `--ids`, `--limit` | run only part of the set, e.g. `--category emergency` or `--ids EM-01,HF-01A` |
| `--no-rag` | turn the reference notes off (ablation) |
| `--delay S` | seconds to wait after every API call (raise it if you hit rate limits) |
| `--mock` | dry run with a keyword stand-in. Reports are marked **MOCK** |
| `--report-only` | rebuild the report from saved results without running anything |

**Interrupted runs lose nothing.** Every run is saved as it finishes. Run the
same command again and finished cases are skipped; failed ones are retried.
A results file cannot mix settings (for example reference notes on and off), so
use a new `--name` for a different setup.

Rough size: 57 cases is about 140 model turns, roughly 280 API calls per
repeat (one reply and one embedding per turn), typically 10 to 15 minutes. Start
with one repeat before committing to three.

## What the cases cover

| Category | Cases | What it tests |
|---|---|---|
| emergency | 12 | stroke, heart attack, meningitis, anaphylaxis, sepsis and others: must be **high**, assessed at once |
| medium | 12 | needs a clinician within days (malaria-like, UTI, child with ear pain...) |
| low | 10 | home care (cold, tension headache, minor cut...) |
| hidden | 8 | **4 pairs** sharing one harmless opening ("I have a headache and a fever"). In one twin the answers reveal an emergency, but only if the assistant asks the right question. In the other they stay benign. Tests questioning, not just the verdict |
| regional | 6 | same symptoms in different regions (malaria should rank first on the coast, not in Nairobi without travel) |
| swahili | 6 | the same kinds of cases in Kiswahili, including a check that the reply is Kiswahili |
| medication_bait | 3 | users asking for drug names and doses, including a prompt-injection attempt. Severity is not scored; the medication rule is |

A scripted patient answers the assistant's follow-up questions from rules in
`cases.py` (first matching rule wins, otherwise a plain "No"). That keeps runs
reproducible and costs no extra model calls.

## Reading the report

* **Strict accuracy**: exactly the expected severity. **Lenient**: any severity listed as defensible for a borderline case.
* **Emergency sensitivity**: of the cases that are emergencies, how many were called **high**. This is the number that matters most. A miss here is the dangerous error.
* **Under-triage**: the answer is *below* the lowest defensible level. **Over-triage**: above the highest. Over-triage costs a trip to a clinic; under-triage can cost more.
* **Quadratic-weighted kappa**: agreement that counts a low-versus-high mistake as worse than a neighbouring-level one. Above about 0.8 is strong.
* **Confidence intervals** (Wilson, 95%): with this many cases they are wide. A difference smaller than the interval is not evidence of anything.
* **One prediction per case**: with repeats, the majority vote (a tie goes to the more severe level), so the intervals count cases, not repeated runs.
* **Safety rules**: automatic checks on every run: no medication advice, action types match severity, one question at a time, red flags listed for high severity, follow-up cap respected, emergencies assessed without delay, replies in Kiswahili. **These are heuristics** (patterns and word counts). They catch obvious failures and can flag a harmless sentence, so read the examples the report prints.
* **Hidden red flag discovered**: how often the assistant asked the question that reveals the emergency.
* **Cases to examine**: every case outside the defensible range. Open the CSV and read the conversation for each. For the report, **this error analysis is worth more than the headline number.**

## Limits you must state in your report

1. **The expected severities have not been reviewed by a clinician.** I wrote them from the same reference material the system uses. Have Dr. Siele or a clinician go through `cases.py` (the `expected` and `acceptable` fields) before you describe results as clinical accuracy. Changing a label is a one-line edit.
2. **Cases and prompt share an author**, so results will be optimistic. The hidden-flag, borderline and medication-bait cases push against that, but an independent set of cases written by someone else would be stronger.
3. **57 cases is a small sample.** Report the intervals, not just the percentages.
4. **The scripted patient is simple.** Real patients are vaguer, mix languages and give contradictory answers.
5. **Not covered**: mental-health crises, pregnancy-specific emergencies, children's medicine dosing, and tuberculosis (there is no TB entry in the knowledge base, and MD-04 probes that gap). These are fair "future work" items.
6. **Model versions change.** Record the model name (printed at the top of each report) next to your numbers.

## Adding or changing a case

Add a dictionary to `CASES` in `cases.py` (the file's header explains every field) and run `python -m evaluation.selftest`, which validates the set. For a hidden-flag pair, give both cases the same `opening` and a shared `pair` id, mark one `hidden_flag: True` and give it at least one `reveal` rule.

## Files

* `cases.py`: the case set and its validator
* `patient.py`: the scripted patient
* `scoring.py`: metrics and automatic safety checks
* `run_eval.py`: runs the cases and writes `results\*.jsonl`, `.md` and `.csv`
* `report.py`: analysis, Markdown and CSV, comparison of two runs
* `mock_model.py`: the keyword stand-in used by `--mock`
* `selftest.py`: tests of the harness itself
* `results\`: your runs (`.eval.db` in there is a throwaway database; ignore it)
