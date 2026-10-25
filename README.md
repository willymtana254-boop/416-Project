# MediTECH AI v2 — Phase 1 (HTML/CSS/JS + Python/Flask)

Fourth-year rebuild of the MediTECH AI symptom checker. Phase 1 fixes the
two biggest issues in the third-year version and lays the foundation for
everything after it:

1. **The Gemini API key is now server-side only.** It lives in `.env` and
   is read by `gemini_client.py`, which is the only thing that ever talks
   to the Gemini API. The browser never sees it.
2. **The assistant is now agentic, not one-shot.** Instead of a single
   prompt → single JSON answer, the model can call `ask_follow_up` (via
   Gemini function calling) up to 3 times to gather more information
   before calling `provide_assessment`. It also does explicit red-flag
   detection for emergency symptom patterns — see `prompts.py`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your Gemini API key
python app.py
```

Open http://localhost:5000.

## How the conversation works

The server is intentionally stateless (no database yet — that's Phase 4).
The browser holds the full Gemini-format conversation `history` array (see
`static/js/app.js`) and resends it with every request to `/api/chat`. The
server (`app.py`):

1. Appends the user's new message to the history.
2. Calls Gemini with `toolConfig.functionCallingConfig.mode = "ANY"`
   (`gemini_client.py`), which forces it to always call one of the two
   tools rather than replying in free text.
3. Reads back whichever function was called and returns a plain-dict
   `turn` (`{"kind": "question", ...}` or `{"kind": "assessment", ...}`)
   to the browser, along with the updated history.
4. Enforces a server-side backstop: once 3 follow-ups have been asked, it
   appends an instruction forcing `provide_assessment` on the next call,
   so the conversation can never loop forever.

## File map

- `prompts.py` — the system instruction and safety rules (edit this to
  tune agent behaviour — e.g. the red-flag list or follow-up cap)
- `gemini_client.py` — server-only Gemini client + function-calling tool defs
- `app.py` — the Flask app and the `/api/chat` route
- `templates/index.html` — page shell
- `static/js/app.js` — all client-side conversation logic, no build step
- `static/css/styles.css` — dark theme, ported from the original single-file version

## What's intentionally left out of Phase 1

Voice input and image-based symptom photos were in the original — image
upload is already wired through to the API, but voice (Web Speech API) and
a camera-style drop zone were left out here to keep this phase reviewable
and easy to re-add. The "find nearest health centre" map is also not yet
ported; Phase 3 replaces it with the Kenya Master Facility List (KMHFL)
API instead of a generic Google Maps search, so it's worth building that
version directly rather than porting the old one twice.

## Roadmap (not yet built)

- **Phase 2 — RAG grounding:** retrieve from a small vector store of
  vetted medical reference material (WHO / Kenya MOH guidelines) before
  `provide_assessment` is called, so conditions are grounded in retrieved
  text rather than raw model recall.
- **Phase 3 — Kenya localization:** KMHFL facility lookup, Swahili
  voice/text support, regional condition weighting.
- **Phase 4 — Persistence:** accounts, symptom history over time,
  optional clinician-facing view (likely SQLite to match your Attachee
  Tracking System setup).
- **Phase 5 — Offline-first PWA shell.**
- **Phase 6 — Evaluation:** a fixed set of test cases with known expected
  severity, scored against the pipeline for the report's evaluation
  chapter.
