import logging
import math
import os

from dotenv import load_dotenv

load_dotenv()  # first, so modules imported below can read values from .env

from flask import Flask, jsonify, render_template, request

import auth
import db
import records
from account_routes import bp as account_bp
from facilities import FacilitiesError, find_facilities
from gemini_client import GeminiAgentError, call_gemini_agent
from pwa import bp as pwa_bp
from prompts import MAX_FOLLOW_UPS
from regions import locale_instructions, normalise_language, normalise_region
from retrieval import retrieve

log = logging.getLogger(__name__)

app = Flask(__name__)
auth.configure(app)                 # sessions, security headers, database path
db.init_db(app.config["DATABASE"])  # creates the tables on first run
app.register_blueprint(account_bp)
app.register_blueprint(pwa_bp)       # /sw.js and /manifest.webmanifest


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
        payload = records.assessment_payload(turn, history, language, region, sources)
        user = auth.current_user()
        if user is None:
            token = records.make_claim_token(app.secret_key, payload)
            return {"claimToken": token} if token else {}
        conn = db.get_conn()
        assessment_id = db.save_assessment(conn, user["id"], payload)
        trend = records.trend_info(db.count_recent_concerning(conn, user["id"], records.TREND_DAYS))
        return {"saved": True, "assessmentId": assessment_id, "trend": trend}
    except Exception:
        log.exception("Could not save the assessment")
        return {"saved": False} if auth.current_user() is not None else {}


if __name__ == "__main__":
    app.run(debug=True, port=5000)
