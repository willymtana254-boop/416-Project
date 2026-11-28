"""MediTECH AI: the Flask app.  Start here:  python app.py

Where things live
  app.py             this file: the web routes (/, /api/chat, /api/facilities) and the offline routes
  ai.py              language rules, system prompt, retrieval over the notes, Gemini client
  knowledge_base.py  the 22 reference notes the model is grounded on
  accounts.py        database, saved assessments, sign-in, clinician queue
  facilities.py      nearby hospitals and clinics (OpenStreetMap)
  manage.py          one-off jobs: build the note index, make a clinician, check the project
  evaluation/        the 57-case test harness
"""

import hashlib
import json
import logging
import math
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # first, so modules imported below can read values from .env

from flask import Flask, Response, jsonify, render_template, request

from accounts import (
    TREND_DAYS,
    account_bp,
    assessment_payload,
    configure,
    count_recent_concerning,
    current_user,
    get_conn,
    init_db,
    make_claim_token,
    save_assessment,
    trend_info,
)
from ai import (
    MAX_FOLLOW_UPS,
    GeminiAgentError,
    call_gemini_agent,
    locale_instructions,
    normalise_language,
    normalise_region,
    retrieve,
)
from facilities import FacilitiesError, find_facilities

log = logging.getLogger(__name__)

app = Flask(__name__)
configure(app)                 # sessions, security headers, database path
init_db(app.config["DATABASE"])  # creates the tables on first run
app.register_blueprint(account_bp)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/facilities", methods=["POST"])
def facilities():
    """Nearest hospitals, clinics and pharmacies for the given coordinates.
    POST (not GET) so the patient's coordinates don't end up in URLs and
    server logs."""
    body = request.get_json(silent=True) or {}
    try:
        lat = float(body.get("lat"))
        lon = float(body.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid lat and lon are required."}), 400
    if math.isnan(lat) or math.isnan(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"error": "Coordinates are out of range."}), 400

    try:
        return jsonify(find_facilities(lat, lon))
    except FacilitiesError as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Invalid JSON body."}), 400

    history = body.get("history") or []
    message = (body.get("message") or "").strip()
    image = body.get("image")  # {"mimeType": ..., "data": ...} or None
    body_area = body.get("bodyArea")
    # Both are optional hints. Unknown values fall back to English / no region.
    language = normalise_language(body.get("language"))
    region = normalise_region(body.get("region"))

    if not message and not image:
        return jsonify({"error": "Please describe your symptoms or attach an image."}), 400

    # How many follow-up questions has the model already asked this
    # conversation? Count prior model functionCall turns named ask_follow_up.
    follow_up_count = sum(
        1
        for m in history
        if m.get("role") == "model"
        and any(p.get("functionCall", {}).get("name") == "ask_follow_up" for p in m.get("parts", []))
    )

    user_parts = []
    if image:
        user_parts.append({"inlineData": {"mimeType": image.get("mimeType"), "data": image.get("data")}})

    text = message or "(see attached image)"
    if body_area and not history:
        text += f" | Affected area: {body_area}"
    if follow_up_count >= MAX_FOLLOW_UPS and history:
        # Server-side backstop in case the model tries to ask a 4th
        # question: forces it to conclude with whatever it has.
        text += (
            f"\n\n(You have reached the maximum of {MAX_FOLLOW_UPS} follow-up questions. "
            "You must call provide_assessment now.)"
        )
    user_parts.append({"text": text})

    new_history = history + [{"role": "user", "parts": user_parts}]

    # Pull together everything the patient has said so far (all user turns'
    # text, this one included) and retrieve relevant knowledge base entries
    # to ground the agent's reasoning. retrieve() degrades to [] on any
    # failure (no index built yet, embedding call fails, etc.) rather than
    # raising: RAG grounding is an enhancement, never a hard dependency.
    symptom_text = " ".join(
        p.get("text", "")
        for m in new_history
        if m.get("role") == "user"
        for p in m.get("parts", [])
        if p.get("text")
    )
    retrieved = retrieve(symptom_text, k=4)
    retrieved_context = "\n\n".join(f"- {r['title']}: {r['text']}" for r in retrieved)

    # Language and regional context, rebuilt every turn so the patient can
    # switch language mid-conversation.
    extra_instructions = locale_instructions(language, region)

    try:
        turn, model_message = call_gemini_agent(
            new_history,
            retrieved_context=retrieved_context,
            extra_instructions=extra_instructions,
        )
    except GeminiAgentError as exc:
        return jsonify({"error": str(exc)}), 502

    updated_history = new_history + [model_message]
    # Gemini expects a functionResponse turn acknowledging the call before
    # the next user turn, even though we resolve it client-side.
    acked_history = updated_history + [
        {
            "role": "function",
            "parts": [
                {
                    "functionResponse": {
                        "name": "ask_follow_up" if turn["kind"] == "question" else "provide_assessment",
                        "response": {"acknowledged": True},
                    }
                }
            ],
        }
    ]

    response = {
        "history": acked_history,
        "turn": turn,
        "followUpCount": follow_up_count + 1 if turn["kind"] == "question" else follow_up_count,
    }
    # Only surface sources alongside the final assessment: showing them on
    # every follow-up question would be noisy and premature.
    if turn["kind"] == "assessment" and retrieved:
        response["sources"] = [r["title"] for r in retrieved]

    if turn["kind"] == "assessment":
        response.update(_persist_assessment(turn, acked_history, language, region, response.get("sources", [])))

    return jsonify(response)


def _persist_assessment(turn, history, language, region, sources) -> dict:
    """Signed-in patients: save the result to their history. Guests: return a
    signed, expiring token so they can save it if they sign in straight
    after. Saving must never stop the patient seeing their result, so every
    failure here is logged and swallowed."""
    try:
        payload = assessment_payload(turn, history, language, region, sources)
        user = current_user()
        if user is None:
            token = make_claim_token(app.secret_key, payload)
            return {"claimToken": token} if token else {}
        conn = get_conn()
        assessment_id = save_assessment(conn, user["id"], payload)
        trend = trend_info(count_recent_concerning(conn, user["id"], TREND_DAYS))
        return {"saved": True, "assessmentId": assessment_id, "trend": trend}
    except Exception:
        log.exception("Could not save the assessment")
        return {"saved": False} if current_user() is not None else {}


# ==========================================================================
# OFFLINE SUPPORT: manifest and service worker  (was pwa.py)
# ==========================================================================
# Progressive Web App support (Phase 5): the web app manifest and the service worker.
#
# The service worker must be served from the site root (/sw.js) so it controls
# the whole app, which is why it is a route here and not a file in static/.
#
# Versioning: the worker's cache name contains a hash of every file it
# precaches (plus the worker's own code). Change any of those files and /sw.js
# changes, so browsers install the new version and the page offers an update.
# Nobody gets stuck on stale code, and nothing needs a manual version bump.
#
# What the worker caches: the app shell only (page, scripts, styles, fonts,
# icons). It never touches /api/: assessments, sign-in and saved history are
# never stored by the service worker. See templates/sw.js.

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SW_TEMPLATE = ROOT / "templates" / "sw.js"

# URL -> the file whose bytes decide the cache version (None = generated)
SHELL = [
    ("/", ROOT / "templates" / "index.html"),
    ("/manifest.webmanifest", None),
    ("/static/css/styles.css", STATIC / "css" / "styles.css"),
    ("/static/js/app.js", STATIC / "js" / "app.js"),
    ("/static/js/account.js", STATIC / "js" / "account.js"),
    ("/static/js/pwa.js", STATIC / "js" / "pwa.js"),
    ("/static/fonts/syne-latin-400-normal.woff2", STATIC / "fonts" / "syne-latin-400-normal.woff2"),
    ("/static/fonts/syne-latin-500-normal.woff2", STATIC / "fonts" / "syne-latin-500-normal.woff2"),
    ("/static/fonts/syne-latin-600-normal.woff2", STATIC / "fonts" / "syne-latin-600-normal.woff2"),
    ("/static/fonts/fraunces-latin-400-normal.woff2", STATIC / "fonts" / "fraunces-latin-400-normal.woff2"),
    ("/static/fonts/fraunces-latin-600-normal.woff2", STATIC / "fonts" / "fraunces-latin-600-normal.woff2"),
    ("/static/icons/icon-192.png", STATIC / "icons" / "icon-192.png"),
    ("/static/icons/icon-512.png", STATIC / "icons" / "icon-512.png"),
    ("/static/icons/icon-maskable-512.png", STATIC / "icons" / "icon-maskable-512.png"),
    ("/static/icons/apple-touch-icon.png", STATIC / "icons" / "apple-touch-icon.png"),
    ("/static/icons/favicon-32.png", STATIC / "icons" / "favicon-32.png"),
]

MANIFEST = {
    "name": "MediTECH AI",
    "short_name": "MediTECH",
    "description": "Symptom triage assistant for Kenya, in English and Kiswahili.",
    "id": "/",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#080c0a",
    "theme_color": "#080c0a",
    "lang": "en",
    "categories": ["health", "medical"],
    "icons": [
        {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
    "shortcuts": [
        {
            "name": "Emergency signs",
            "short_name": "Emergency",
            "description": "When to get emergency help now (works offline)",
            "url": "/?view=emergency",
            "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"}],
        }
    ],
}


def manifest_bytes() -> bytes:
    return json.dumps(MANIFEST, indent=2).encode("utf-8")


def precache_urls() -> list:
    """The shell URLs that exist on disk. A missing file is logged and left
    out: one absent icon must not stop the whole worker from installing."""
    urls = []
    for url, path in SHELL:
        if path is not None and not path.exists():
            log.warning("PWA shell file is missing, not cached: %s", path)
            continue
        urls.append(url)
    return urls


def cache_version() -> str:
    """12-hex-digit hash of every shell file and of the worker's own code."""
    h = hashlib.sha256()
    for url, path in SHELL:
        h.update(url.encode("utf-8"))
        if path is None:
            h.update(manifest_bytes())
        elif path.exists():
            h.update(path.read_bytes())
    h.update(SW_TEMPLATE.read_bytes())
    return h.hexdigest()[:12]


@app.get("/sw.js")
def service_worker():
    source = SW_TEMPLATE.read_text(encoding="utf-8")
    source = source.replace("__VERSION__", cache_version()).replace("__PRECACHE__", json.dumps(precache_urls()))
    resp = Response(source, mimetype="application/javascript")
    # Browsers must re-check the worker file every time, or updates never arrive.
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.get("/manifest.webmanifest")
def manifest():
    resp = Response(manifest_bytes(), mimetype="application/manifest+json")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


if __name__ == "__main__":
    app.run(debug=True, port=5000)
