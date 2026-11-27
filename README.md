# MediTECH AI

A bilingual (English and Kiswahili) symptom-triage assistant for Kenya. The patient describes their
symptoms; the app asks up to three follow-up questions, grounds its answer in 22 reference notes, and
returns a severity level (low, medium, high), advice, and nearby facilities. It gives guidance, not a
diagnosis, and never names medicines or doses. It works as an installable, partly offline web app.

## Run it

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then paste your GEMINI_API_KEY into .env
python manage.py index          # one time: builds the reference-note index
python manage.py check          # optional: confirms everything is in place
python app.py                   # open http://localhost:5000
```

## The code in five files

| File | What it does | Read it for |
| --- | --- | --- |
| `app.py` | The web server: the page, `/api/chat`, `/api/facilities`, and the offline (PWA) routes | The whole request flow |
| `ai.py` | The AI side: language and region rules, the system prompt, retrieval over the notes, the Gemini client | Safety rules, RAG, agentic behaviour |
| `knowledge_base.py` | The 22 reference notes the model is grounded on | The clinical content |
| `accounts.py` | Database, saved results, passwords and sessions, sign-in and clinician routes | Privacy and access control |
| `facilities.py` | Nearby hospitals and clinics from OpenStreetMap | Local fit |

Each of the larger files is split into numbered, labelled sections, so you can follow it top to bottom.

Around them:

| Path | What it is |
| --- | --- |
| `manage.py` | One-off jobs: `index` (build the note index), `clinician` (make a clinician account), `check` (is the folder complete?) |
| `templates/index.html`, `templates/sw.js` | The page and the offline service worker |
| `static/` | `js/app.js` (chat flow and English/Kiswahili text), `js/account.js` (sign-in and history), `js/pwa.js` (install and offline banners), `css/styles.css`, fonts, icons |
| `evaluation/` | The 57-case test harness (see `evaluation/README.md`) |
| `data/` | Created at run time: note index, database, secret key (not in git) |

## One message, start to finish

1. The browser (`static/js/app.js`) sends `POST /api/chat` with the message, history, language and region.
2. `app.py` counts earlier follow-up questions. After three, it forces a final assessment.
3. `ai.py` section 3 embeds what the patient said and returns the 4 most similar reference notes.
4. `ai.py` section 1 adds the language and regional instructions for this turn.
5. `ai.py` section 4 sends everything to Gemini and forces one of two tool calls: `ask_follow_up` or
   `provide_assessment`, so the answer is always structured.
6. For a final assessment, `app.py` saves it: signed-in users to the database, guests get a two-hour
   signed token so they can save it after signing in.
7. The browser shows the next question, or the result with severity, advice, sources and facilities.

## Safety rules

1. The model must answer through a tool call, never free text.
2. The prompt bans medication names and doses (`ai.py` section 2).
3. At most three follow-up questions, enforced on the server.
4. High severity shows 999 and 112 and a facility search.
5. If retrieval fails, the patient still gets an answer (no extra context).
6. Patients see only their own records. Clinicians see only records a patient chose to share, never the
   email address, and every view is written to an audit log (`accounts.py` section 4).

## Where to look when asked...

| Question | Answer lives in |
| --- | --- |
| How do you stop it naming drugs? | `ai.py`, section 2 |
| How is the 3-question limit enforced? | `app.py`, `chat()`, and `MAX_FOLLOW_UPS` in `ai.py` |
| What is RAG here? | `ai.py` section 3 and `knowledge_base.py` |
| How does Kiswahili work? | `ai.py` section 1 (model) and the text dictionaries in `static/js/*.js` (interface) |
| How are passwords and logins protected? | `accounts.py`, section 3 |
| Who can see a patient's record? | `accounts.py`, sections 1 and 4 |
| How does offline mode work? | `app.py` (offline section), `templates/sw.js`, `static/js/pwa.js` |
| How was it tested? | `evaluation/` and `python -m evaluation.selftest` |

## Testing

```powershell
python -m evaluation.selftest                       # 130 checks of the harness, no API key needed
python -m evaluation.run_eval --mock --name dry     # full pipeline with a stand-in model
python -m evaluation.run_eval --name real           # the 57 cases against Gemini (needs the key)
```

## Five-minute demo

1. English case: "headache and fever for two days". Show a follow-up question and the progress hint.
2. Kiswahili case: switch the toggle and show the Kiswahili result.
3. Emergency case: "chest pain and cannot breathe". Show high severity, 999 and 112, and the facility search.
4. Sources: point out the reference notes under the result.
5. Account: register, run a case, open History, share it.
6. Clinician view: sign in as a clinician (`python manage.py clinician`), open the queue, add a review note.
7. Offline: switch the browser to offline and reload; the app shell still opens.
8. Evaluation: open the report from `evaluation/` and read the under-triage line.

Keep a screen recording of this run in case the internet fails.
