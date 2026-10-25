"""Turning a finished conversation into a stored record, and back into JSON
for the browser (Phase 4). Nothing here touches Flask or the database, so
it is easy to test.

Everything stored is normalised first: unknown keys are dropped, strings are
clipped and enums are coerced. The model's output and the browser's
conversation history are both treated as untrusted data."""

import json
import re
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

from regions import normalise_language, normalise_region

SEVERITIES = ("low", "medium", "high")
LIKELIHOODS = ("low", "medium", "high")
ACTION_TYPES = ("urgent", "soon", "self")

MAX_TRANSCRIPT = 30
CLAIM_MAX_AGE_S = 2 * 60 * 60   # a guest has two hours to sign in and keep a result
CLAIM_MAX_CHARS = 16000
TREND_DAYS = 30
TREND_THRESHOLD = 3

# The server appends this to a patient message once the follow-up limit is hit
# (app.py). It is an instruction to the model, not something the patient wrote.
_BACKSTOP_RE = re.compile(r"\n\n\(You have reached the maximum of \d+ follow-up questions\..*?\)\s*$", re.S)
_AREA_RE = re.compile(r"\s*\|\s*Affected area:.*$", re.S)


def clip(value, n: int) -> str:
    s = "" if value is None else str(value)
    return s.strip()[:n]


def _list(v) -> list:
    return v if isinstance(v, list) else []


def build_transcript(history) -> list:
    """Patient messages and the assistant's follow-up questions, as plain
    text. Photos are never kept."""
    out = []
    for m in _list(history):
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        parts = _list(m.get("parts"))
        if role == "user":
            texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
            has_image = any(isinstance(p, dict) and p.get("inlineData") for p in parts)
            text = _BACKSTOP_RE.sub("", " ".join(texts)).strip()
            if text == "(see attached image)":
                text = "(photo attached, not stored)"
            elif has_image:
                text += " (photo attached, not stored)"
            if text:
                out.append({"from": "user", "text": clip(text, 1000)})
        elif role == "model":
            for p in parts:
                fc = p.get("functionCall") if isinstance(p, dict) else None
                if isinstance(fc, dict) and fc.get("name") == "ask_follow_up":
                    q = clip((fc.get("args") or {}).get("question"), 1000)
                    if q:
                        out.append({"from": "model", "text": q})
    return out[:MAX_TRANSCRIPT]


def normalise_assessment(raw: dict) -> dict:
    sev = raw.get("severity")
    conditions = []
    for c in _list(raw.get("conditions"))[:10]:
        if isinstance(c, dict) and clip(c.get("name"), 120):
            conditions.append(
                {
                    "name": clip(c.get("name"), 120),
                    "likelihood": c.get("likelihood") if c.get("likelihood") in LIKELIHOODS else "medium",
                    "description": clip(c.get("description"), 400),
                }
            )
    actions = []
    for a in _list(raw.get("actions"))[:10]:
        if isinstance(a, dict) and clip(a.get("text"), 400):
            actions.append(
                {
                    "type": a.get("type") if a.get("type") in ACTION_TYPES else "self",
                    "text": clip(a.get("text"), 400),
                }
            )
    transcript = []
    for m in _list(raw.get("transcript"))[:MAX_TRANSCRIPT]:
        if isinstance(m, dict) and m.get("from") in ("user", "model") and clip(m.get("text"), 1000):
            transcript.append({"from": m["from"], "text": clip(m.get("text"), 1000)})
    return {
        "language": normalise_language(raw.get("language")),
        "region": normalise_region(raw.get("region")),
        "severity": sev if sev in SEVERITIES else "medium",
        "summary": clip(raw.get("summary"), 200),
        "transcript": transcript,
        "redFlags": [clip(x, 300) for x in _list(raw.get("redFlags"))[:10] if clip(x, 300)],
        "conditions": conditions,
        "actions": actions,
        "sources": [clip(x, 120) for x in _list(raw.get("sources"))[:10] if clip(x, 120)],
    }


def assessment_payload(turn: dict, history, language, region, sources) -> dict:
    """Builds the record for a finished assessment from the model's turn and
    the conversation. `turn` is the dict from gemini_client."""
    transcript = build_transcript(history)
    first_user = next((m["text"] for m in transcript if m["from"] == "user"), "")
    return normalise_assessment(
        {
            "language": language,
            "region": region,
            "severity": turn.get("severity"),
            "summary": _AREA_RE.sub("", first_user),
            "transcript": transcript,
            "redFlags": turn.get("redFlags"),
            "conditions": turn.get("conditions"),
            "actions": turn.get("actions"),
            "sources": sources,
        }
    )


# ── Claim tokens: let a guest keep a result after signing in ──
# The server signs the finished assessment and hands the token to the guest's
# browser. After login the browser returns it and the server saves it. The
# browser cannot alter the token, so it cannot invent or change a result.
def _serializer(secret_key) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="meditech-claim")


def make_claim_token(secret_key, payload: dict):
    body = dict(payload)
    body["nonce"] = secrets.token_hex(8)
    token = _serializer(secret_key).dumps(body)
    return token if len(token) <= CLAIM_MAX_CHARS else None


def read_claim_token(secret_key, token, max_age: int = CLAIM_MAX_AGE_S):
    """Returns (normalised payload, nonce) or (None, None)."""
    if not isinstance(token, str) or not token:
        return None, None
    try:
        body = _serializer(secret_key).loads(token, max_age=max_age)
    except BadSignature:  # also covers SignatureExpired
        return None, None
    if not isinstance(body, dict) or not isinstance(body.get("nonce"), str):
        return None, None
    return normalise_assessment(body), body["nonce"]


# ── Trend ──
def trend_info(count: int, days: int = TREND_DAYS, threshold: int = TREND_THRESHOLD) -> dict:
    """Plain counting of medium/high assessments. Deliberately not model
    judgement: it must behave the same in English and Kiswahili."""
    return {"count": count, "days": days, "notice": count >= threshold}


# ── JSON for the browser ──
def _loads(text, default):
    try:
        value = json.loads(text)
        return value if isinstance(value, type(default)) else default
    except (TypeError, ValueError):
        return default


def serialize_summary(row) -> dict:
    conditions = _loads(row["conditions"], [])
    out = {
        "id": row["id"],
        "createdAt": row["created_at"],
        "severity": row["severity"],
        "summary": row["summary"],
        "language": row["language"],
        "shared": bool(row["shared"]),
        "reviewStatus": row["review_status"],
        "hasClinicianNote": bool(row["clinician_note"]),
        "topConditions": [c.get("name", "") for c in conditions[:2] if isinstance(c, dict)],
    }
    if "patient_name" in row.keys():
        out["patientName"] = row["patient_name"]
    return out


def serialize_detail(row) -> dict:
    out = serialize_summary(row)
    out.update(
        {
            "region": row["region"],
            "transcript": _loads(row["transcript"], []),
            "redFlags": _loads(row["red_flags"], []),
            "conditions": _loads(row["conditions"], []),
            "actions": _loads(row["actions"], []),
            "sources": _loads(row["sources"], []),
            "clinicianNote": row["clinician_note"],
            "reviewedAt": row["reviewed_at"],
        }
    )
    return out
