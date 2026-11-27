"""MediTECH AI: the Flask app.  Start here:  python app.py

Where things live
  app.py             this file: the web routes (/, /api/chat, /api/facilities), the nearby-facility
                     lookup, and the offline routes
  ai.py              language rules, system prompt, retrieval over the notes, Gemini client
  knowledge_base.py  the 22 reference notes the model is grounded on
  accounts.py        database, saved assessments, sign-in, clinician queue
  manage.py          one-off jobs: build the note index, make a clinician, check the project
  evaluation/        the 57-case test harness
"""

import hashlib
import json
import logging
import math
import re
import time
from pathlib import Path

import requests
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
# NEARBY FACILITIES  (was facilities.py)
# ==========================================================================
# Nearby health facility lookup (Phase 3).
#
# Data source: OpenStreetMap, queried through the Overpass API. It is free,
# needs no key, and covers hospitals, clinics and pharmacies with
# coordinates. Coverage in rural Kenya is uneven, so results can be
# incomplete; the UI says so.
#
# The Kenya Master Health Facility List (KMHFL) is the authoritative source
# for licensed facilities, but its API needs credentials from the Ministry
# of Health / HealthIT (University of Nairobi). If you get access, replace
# find_facilities() with a KMHFL-backed version that returns the same shape;
# nothing else in the app needs to change.
#
# Only find_facilities() is called from app.py. parse_elements() is pure
# (no network) so it can be tested on its own.


OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "MediTECH-AI/0.3 (fourth-year university project)"

# Search progressively wider: rural areas may have nothing within 5 km.
RADII_M = [5000, 15000, 40000]
MIN_RESULTS = 5
MAX_RESULTS = 40
CACHE_TTL_SECONDS = 600

# The public Overpass servers are shared and are often busy (HTTP 429/504).
# Try every mirror, pause briefly, then do one more round, but give up after
# TIME_BUDGET_S so the patient is not left waiting on a spinner.
ROUNDS = 2
ROUND_PAUSE_S = 1.5
REQUEST_TIMEOUT_S = 20
TIME_BUDGET_S = 45

_cache: dict = {}


class FacilitiesError(Exception):
    """Raised when facilities can't be fetched. The message is safe to show."""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _classify(tags: dict):
    amenity = tags.get("amenity")
    health = tags.get("healthcare")
    if amenity == "hospital" or health == "hospital":
        return "hospital"
    if amenity == "pharmacy" or health == "pharmacy":
        return "pharmacy"
    if amenity in ("clinic", "doctors") or health in ("clinic", "doctor", "centre"):
        return "clinic"
    return None


def _clean_phone(tags: dict) -> str:
    raw = tags.get("phone") or tags.get("contact:phone") or ""
    first = str(raw).split(";")[0]
    return re.sub(r"[^\d+\-\s()]", "", first).strip()[:30]


def parse_elements(elements: list, lat: float, lon: float) -> list:
    """Turns raw Overpass elements into a distance-sorted list of
    facilities, dropping unnamed duplicates of the same place."""
    found = []
    for el in elements:
        tags = el.get("tags") or {}
        kind = _classify(tags)
        if not kind:
            continue
        if "lat" in el and "lon" in el:
            f_lat, f_lon = el["lat"], el["lon"]
        else:
            center = el.get("center") or {}
            if "lat" not in center or "lon" not in center:
                continue
            f_lat, f_lon = center["lat"], center["lon"]

        name = (tags.get("name") or "").strip()
        found.append(
            {
                "name": name[:80],
                "kind": kind,
                "distanceKm": round(haversine_km(lat, lon, f_lat, f_lon), 1),
                "_dist": haversine_km(lat, lon, f_lat, f_lon),
                "lat": f_lat,
                "lon": f_lon,
                "phone": _clean_phone(tags),
                "emergency": tags.get("emergency") == "yes",
                "openingHours": str(tags.get("opening_hours") or "")[:80],
                "directionsUrl": (
                    f"https://www.google.com/maps/dir/?api=1&destination={f_lat},{f_lon}"
                ),
            }
        )

    found.sort(key=lambda f: f["_dist"])

    # OSM often has both a node and a building outline for one hospital.
    # Drop a later entry with the same name and kind within 150 m.
    unique = []
    for f in found:
        dup = any(
            u["kind"] == f["kind"]
            and f["name"]
            and u["name"].lower() == f["name"].lower()
            and haversine_km(u["lat"], u["lon"], f["lat"], f["lon"]) < 0.15
            for u in unique
        )
        if not dup:
            unique.append(f)

    for f in unique:
        f.pop("_dist", None)
    return unique


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    return (
        "[out:json][timeout:20];\n"
        "(\n"
        f'  nwr["amenity"~"^(hospital|clinic|doctors|pharmacy)$"](around:{radius_m},{lat},{lon});\n'
        f'  nwr["healthcare"~"^(hospital|clinic|doctor|pharmacy|centre)$"](around:{radius_m},{lat},{lon});\n'
        ");\n"
        "out tags center 150;\n"
    )


def _overpass(query: str) -> list:
    """POSTs the query, trying each mirror in turn and retrying once after a
    short pause. Returns raw elements. Every failed attempt is logged so the
    reason is visible in the server terminal."""
    started = time.time()
    last_problem = "no response"
    for round_no in range(ROUNDS):
        if round_no:
            time.sleep(ROUND_PAUSE_S)
        for url in OVERPASS_URLS:
            if time.time() - started > TIME_BUDGET_S:
                break
            try:
                res = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=REQUEST_TIMEOUT_S,
                )
            except requests.RequestException as exc:
                last_problem = f"{exc.__class__.__name__}"
                log.warning("Overpass %s failed: %s", url, last_problem)
                continue
            if res.status_code != 200:
                last_problem = f"HTTP {res.status_code}"
                log.warning("Overpass %s failed: %s", url, last_problem)
                continue
            try:
                return res.json().get("elements", [])
            except ValueError:
                last_problem = "invalid JSON"
                log.warning("Overpass %s returned invalid JSON", url)
    raise FacilitiesError(
        "Could not reach the map data service right now. Please try again in a moment. "
        f"({last_problem})"
    )


def _elements_for(lat: float, lon: float, radius_m: int) -> list:
    key = (round(lat, 2), round(lon, 2), radius_m)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    elements = _overpass(_build_query(lat, lon, radius_m))
    _cache[key] = (time.time(), elements)
    return elements


def find_facilities(lat: float, lon: float) -> dict:
    """Returns {"facilities": [...], "radiusKm": n}, nearest first."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise FacilitiesError("Invalid coordinates.")

    facilities: list = []
    radius_m = RADII_M[-1]
    for radius_m in RADII_M:
        facilities = parse_elements(_elements_for(lat, lon, radius_m), lat, lon)
        if len(facilities) >= MIN_RESULTS:
            break

    return {"facilities": facilities[:MAX_RESULTS], "radiusKm": radius_m / 1000}


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
