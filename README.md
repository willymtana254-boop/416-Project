# MediTECH AI v2 — Phase 1 + Phase 2 (HTML/CSS/JS + Python/Flask)

Fourth-year rebuild of the MediTECH AI symptom checker.

**Phase 1** fixed the two biggest issues in the third-year version:

1. **The Gemini API key is now server-side only.** It lives in `.env` and
   is read by `gemini_client.py`, which is the only thing that ever talks
   to the Gemini API. The browser never sees it.
2. **The assistant is now agentic, not one-shot.** Instead of a single
   prompt → single JSON answer, the model can call `ask_follow_up` (via
   Gemini function calling) up to 3 times to gather more information
   before calling `provide_assessment`. It also does explicit red-flag
   detection for emergency symptom patterns — see `prompts.py`.

**Phase 2** adds RAG grounding: `knowledge_base.py` holds ~18 original,
short reference summaries of common conditions. `retrieve()` in
`retrieval.py` embeds the patient's conversation with Gemini's embedding
model and ranks the knowledge base by cosine similarity, and the top
matches get appended to the system prompt for that call (`prompts.py`'s
`build_system_instruction`). The assessment card shows which entries were
used ("Informed by reference notes on: ..."), so grounding is visible and
checkable rather than a black box — useful for your evaluation chapter.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your Gemini API key
python build_index.py           # builds data/kb_embeddings.json (Phase 2)
python app.py
```

Open http://localhost:5000.

**Important:** run `python build_index.py` once before `python app.py` (and
again any time you edit `knowledge_base.py`). It calls Gemini's embedding
model once per knowledge base entry and writes `data/kb_embeddings.json`.
If you skip this step, the app still works — `retrieve()` degrades
gracefully to "no extra context" when the index file doesn't exist — you
just won't get Phase 2's grounding until you run it.

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

- `prompts.py` — the system instruction, safety rules, and
  `build_system_instruction()` which appends retrieved context
- `gemini_client.py` — server-only Gemini client + function-calling tool defs
- `knowledge_base.py` — Phase 2's reference content (edit/extend this)
- `retrieval.py` — embedding + cosine-similarity retrieval over the KB
- `build_index.py` — one-time script to embed `knowledge_base.py` into
  `data/kb_embeddings.json`
- `app.py` — the Flask app, the `/api/chat` route, and where retrieval
  gets called before the agent reasons
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

- **Phase 3 — Kenya localization:** KMHFL facility lookup, Swahili
  voice/text support, regional condition weighting. Also a natural point
  to extend `knowledge_base.py` with Kenya MOH-aligned guidance, and to
  swap the current plain-Python retrieval for Chroma/pgvector if the
  knowledge base grows a lot.
- **Phase 4 — Persistence:** accounts, symptom history over time,
  optional clinician-facing view (likely SQLite to match your Attachee
  Tracking System setup).
- **Phase 5 — Offline-first PWA shell.**
- **Phase 6 — Evaluation:** a fixed set of test cases with known expected
  severity, scored against the pipeline for the report's evaluation
  chapter.
