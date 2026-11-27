"""Accounts for MediTECH AI: the database, saved assessments, passwords and sessions,
and the API routes for sign-in, history and the clinician queue.
Read it top to bottom: 1 database, 2 records, 3 security, 4 routes."""

from datetime import datetime, timedelta, timezone
import json
import os
import re
import secrets
import sqlite3
import threading
import time

from flask import Blueprint, current_app, g, jsonify, request, session
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from ai import normalise_language, normalise_region

# ==========================================================================
# 1. DATABASE  (was db.py)
# ==========================================================================
# SQLite storage for accounts and saved assessments (Phase 4).
#
# Design notes
# - Plain sqlite3 from the standard library; no ORM, no new dependency.
# - Every query is parameterised. Nothing is ever built by string formatting
#   from user input.
# - Photos are never stored. Only the conversation text and the structured
#   result are kept.
# - Deleting a user cascades to their assessments (foreign keys are ON).
# - audit_log records who did what to which record (clinician views and
#   reviews, sharing changes, deletions). It is not shown in the UI; it
#   exists so access to health data is accountable.
#
# The database path comes from the MEDITECH_DB environment variable, else
# data/meditech.db. If your project folder is synced by OneDrive, point
# MEDITECH_DB at a folder outside it: sync clients can lock SQLite files.

def default_db_path() -> str:
    """Read at call time (not import time) so a value from .env is seen."""
    return os.environ.get("MEDITECH_DB") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "meditech.db"
    )


class EmailTaken(Exception):
    """Raised when registering an email that already has an account."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'patient' CHECK (role IN ('patient', 'clinician')),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS assessments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    language       TEXT NOT NULL DEFAULT 'en',
    region         TEXT NOT NULL DEFAULT '',
    severity       TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    summary        TEXT NOT NULL DEFAULT '',
    transcript     TEXT NOT NULL DEFAULT '[]',
    red_flags      TEXT NOT NULL DEFAULT '[]',
    conditions     TEXT NOT NULL DEFAULT '[]',
    actions        TEXT NOT NULL DEFAULT '[]',
    sources        TEXT NOT NULL DEFAULT '[]',
    shared         INTEGER NOT NULL DEFAULT 0 CHECK (shared IN (0, 1)),
    shared_at      TEXT,
    review_status  TEXT NOT NULL DEFAULT 'new' CHECK (review_status IN ('new', 'reviewed')),
    clinician_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    clinician_note TEXT NOT NULL DEFAULT '',
    reviewed_at    TEXT,
    claim_nonce    TEXT
);

CREATE INDEX IF NOT EXISTS idx_assessments_user
    ON assessments (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assessments_shared
    ON assessments (shared, review_status, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_assessments_nonce
    ON assessments (claim_nonce) WHERE claim_nonce IS NOT NULL;

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT NOT NULL,
    actor_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action    TEXT NOT NULL,
    target_id INTEGER
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str) -> sqlite3.Connection:
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ── Flask glue: one connection per request ──
def get_conn() -> sqlite3.Connection:
    from flask import current_app, g

    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_conn(_exc=None) -> None:
    from flask import g

    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# ── Users ──
def create_user(conn, email: str, name: str, password_hash: str, role: str = "patient") -> int:
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                (email, name, password_hash, role),
            )
        return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc).upper():
            raise EmailTaken(email) from exc
        raise


def get_user_by_email(conn, email: str):
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_user_by_id(conn, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def set_role(conn, user_id: int, role: str) -> None:
    with conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def delete_user(conn, user_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ── Assessments ──
def save_assessment(conn, user_id: int, a: dict, claim_nonce=None, created_at=None) -> int:
    """`a` must already be normalised (records.normalise_assessment)."""
    with conn:
        cur = conn.execute(
            """INSERT INTO assessments
               (user_id, created_at, language, region, severity, summary,
                transcript, red_flags, conditions, actions, sources, claim_nonce)
               VALUES (?, COALESCE(?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                created_at,
                a["language"],
                a["region"],
                a["severity"],
                a["summary"],
                json.dumps(a["transcript"], ensure_ascii=False),
                json.dumps(a["redFlags"], ensure_ascii=False),
                json.dumps(a["conditions"], ensure_ascii=False),
                json.dumps(a["actions"], ensure_ascii=False),
                json.dumps(a["sources"], ensure_ascii=False),
                claim_nonce,
            ),
        )
    return cur.lastrowid


def get_assessment(conn, assessment_id: int):
    return conn.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,)).fetchone()


def find_by_nonce(conn, nonce: str):
    return conn.execute("SELECT * FROM assessments WHERE claim_nonce = ?", (nonce,)).fetchone()


def list_assessments(conn, user_id: int, limit: int = 20, offset: int = 0):
    return conn.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ).fetchall()


def count_assessments(conn, user_id: int) -> int:
    return conn.execute("SELECT COUNT(*) FROM assessments WHERE user_id = ?", (user_id,)).fetchone()[0]


def count_recent_concerning(conn, user_id: int, days: int = 30) -> int:
    """Assessments rated medium or high in the last `days` days."""
    return conn.execute(
        """SELECT COUNT(*) FROM assessments
           WHERE user_id = ? AND severity IN ('medium', 'high') AND created_at >= ?""",
        (user_id, utc_days_ago(days)),
    ).fetchone()[0]


def delete_assessment(conn, assessment_id: int, user_id: int) -> bool:
    with conn:
        cur = conn.execute(
            "DELETE FROM assessments WHERE id = ? AND user_id = ?", (assessment_id, user_id)
        )
    return cur.rowcount > 0


def set_shared(conn, assessment_id: int, user_id: int, shared: bool) -> bool:
    with conn:
        cur = conn.execute(
            "UPDATE assessments SET shared = ?, shared_at = ? WHERE id = ? AND user_id = ?",
            (1 if shared else 0, utc_now() if shared else None, assessment_id, user_id),
        )
    return cur.rowcount > 0


# ── Clinician queue (only assessments the patient chose to share) ──
_QUEUE_ORDER = """ORDER BY (a.review_status = 'reviewed'),
                  CASE a.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                  a.created_at DESC, a.id DESC"""


def _queue_filter(status, severity):
    where, params = ["a.shared = 1"], []
    if status in ("new", "reviewed"):
        where.append("a.review_status = ?")
        params.append(status)
    if severity in ("low", "medium", "high"):
        where.append("a.severity = ?")
        params.append(severity)
    return " AND ".join(where), params


def queue_rows(conn, status="new", severity=None, limit=30, offset=0):
    where, params = _queue_filter(status, severity)
    rows = conn.execute(
        f"""SELECT a.*, u.name AS patient_name FROM assessments a
            JOIN users u ON u.id = a.user_id
            WHERE {where} {_QUEUE_ORDER} LIMIT ? OFFSET ?""",
        (*params, limit, offset),
    ).fetchall()
    total = conn.execute(f"SELECT COUNT(*) FROM assessments a WHERE {where}", params).fetchone()[0]
    return rows, total


def get_shared_assessment(conn, assessment_id: int):
    return conn.execute(
        """SELECT a.*, u.name AS patient_name FROM assessments a
           JOIN users u ON u.id = a.user_id
           WHERE a.id = ? AND a.shared = 1""",
        (assessment_id,),
    ).fetchone()


def review_assessment(conn, assessment_id: int, clinician_id: int, note: str):
    """Marks a shared assessment reviewed. Returns the review time, or None
    if the assessment does not exist or is not shared."""
    when = utc_now()
    with conn:
        cur = conn.execute(
            """UPDATE assessments
               SET review_status = 'reviewed', clinician_id = ?, clinician_note = ?, reviewed_at = ?
               WHERE id = ? AND shared = 1""",
            (clinician_id, note, when, assessment_id),
        )
    return when if cur.rowcount > 0 else None


# ── Audit trail ──
def audit(conn, actor_id, action: str, target_id=None) -> None:
    with conn:
        conn.execute(
            "INSERT INTO audit_log (at, actor_id, action, target_id) VALUES (?, ?, ?, ?)",
            (utc_now(), actor_id, action, target_id),
        )


# ==========================================================================
# 2. RECORDS: a finished chat becomes a stored result  (was records.py)
# ==========================================================================
# Turning a finished conversation into a stored record, and back into JSON
# for the browser (Phase 4). Nothing here touches Flask or the database, so
# it is easy to test.
#
# Everything stored is normalised first: unknown keys are dropped, strings are
# clipped and enums are coerced. The model's output and the browser's
# conversation history are both treated as untrusted data.

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


# ==========================================================================
# 3. PASSWORDS, SESSIONS AND SECURITY HEADERS  (was auth.py)
# ==========================================================================
# Authentication and request-security helpers (Phase 4).
#
# - Passwords are hashed with PBKDF2-SHA256 (werkzeug). Plain passwords are
#   never stored or logged.
# - Login failures are rate limited per account+IP and per IP. Unknown emails
#   and wrong passwords give the same answer in the same time, so the login
#   form does not reveal which emails have accounts.
# - Sessions are signed cookies: HttpOnly, SameSite=Lax. Set
#   SESSION_COOKIE_SECURE=1 when serving over https.
# - State-changing endpoints only accept a JSON body. Browsers cannot send
#   cross-site JSON without a CORS preflight (which this app never allows),
#   and SameSite=Lax keeps the cookie off cross-site POSTs, so a hostile page
#   cannot act as a signed-in user.
# - Clinician accounts cannot be created through the website (see
#   create_clinician.py), so nobody can promote themselves.

PASSWORD_METHOD = "pbkdf2:sha256"
# Checked when the email is unknown, so the response time is the same.
DUMMY_HASH = generate_password_hash("not-a-real-password", method=PASSWORD_METHOD)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COMMON_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "1234567890", "qwertyui",
    "qwerty123", "11111111", "00000000", "iloveyou", "abcd1234", "letmein123",
}


# ── Validation (return the cleaned value, or None / an error code) ──
def clean_email(value):
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    return email if len(email) <= 254 and EMAIL_RE.match(email) else None


def clean_name(value):
    if not isinstance(value, str):
        return None
    name = re.sub(r"[\x00-\x1f\x7f]", "", value)
    name = re.sub(r"\s+", " ", name).strip()
    return name if 1 <= len(name) <= 80 else None


def check_password(password, email: str = ""):
    """Returns an error code, or None if the password is acceptable."""
    if not isinstance(password, str) or not (8 <= len(password) <= 128):
        return "weak_password"
    if password.lower() in COMMON_PASSWORDS or len(set(password)) < 3:
        return "weak_password"
    if email and password.lower() == email.lower():
        return "weak_password"
    return None


def hash_password(password: str) -> str:
    return generate_password_hash(password, method=PASSWORD_METHOD)


def verify_password(stored_hash: str, password) -> bool:
    return check_password_hash(stored_hash, password if isinstance(password, str) else "")


# ── Rate limiting (in memory: resets when the server restarts) ──
class RateLimiter:
    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self._hits: dict = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        hits = [t for t in self._hits.get(key, []) if now - t < self.window]
        if hits:
            self._hits[key] = hits
        else:
            self._hits.pop(key, None)
        return hits

    def blocked(self, key, now=None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            return len(self._recent(key, now)) >= self.limit

    def retry_after(self, key, now=None) -> int:
        now = time.time() if now is None else now
        with self._lock:
            hits = self._recent(key, now)
            return max(1, int(hits[0] + self.window - now)) if hits else 0

    def hit(self, key, now=None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            if len(self._hits) > 10000:  # keep memory bounded
                for k in list(self._hits):
                    self._recent(k, now)
            self._hits.setdefault(key, []).append(now)

    def reset(self, key) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


LOGIN_ACCOUNT_LIMITER = RateLimiter(5, 15 * 60)    # 5 failures per account+IP
LOGIN_IP_LIMITER = RateLimiter(30, 15 * 60)        # 30 failures per IP
REGISTER_LIMITER = RateLimiter(10, 60 * 60)        # 10 sign-ups per IP per hour


# ── Sessions ──
def public_user(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}


def login_user(row) -> None:
    session.clear()  # fresh session on login (prevents session fixation)
    session["uid"] = row["id"]
    session.permanent = True
    g.user = row


def logout_user() -> None:
    session.clear()
    g.user = None


def current_user():
    """The signed-in user's row, or None. Looked up on every request so a
    deleted account or changed role takes effect immediately."""
    if "user" in g:
        return g.user
    g.user = None
    uid = session.get("uid")
    if uid is not None:
        row = get_user_by_id(get_conn(), uid)
        if row is not None:
            g.user = row
        else:
            session.pop("uid", None)
    return g.user


def fail(code: str, message: str, status: int):
    return jsonify({"error": message, "code": code}), status


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return fail("not_logged_in", "Please sign in first.", 401)
        return fn(*args, **kwargs)

    return wrapper


def role_required(role: str):
    def decorator(fn):
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return fail("not_logged_in", "Please sign in first.", 401)
            if user["role"] != role:
                return fail("forbidden", "You do not have access to this.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ── App configuration ──
def load_secret_key(data_dir: str) -> str:
    """SECRET_KEY from the environment, else a random key kept in
    data/.secret_key so logins survive a server restart."""
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    path = os.path.join(data_dir, ".secret_key")
    try:
        with open(path, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if len(key) >= 32:
                return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def configure(app, db_path=None) -> None:
    path = db_path or default_db_path()
    app.config.update(
        DATABASE=path,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # photos arrive as base64 in JSON
    )
    app.secret_key = load_secret_key(os.path.dirname(os.path.abspath(path)))
    app.teardown_appcontext(close_conn)
    app.after_request(add_security_headers)

    @app.errorhandler(413)
    def too_large(_e):
        return fail("too_large", "That request is too large. Please use a smaller photo.", 413)


# Everything the app needs is served from this site (fonts included), so no other
# origin is allowed. 'unsafe-inline' is for the style="display:none" attributes in the
# page; scripts get no such exception.
CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "worker-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    from flask import request

    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"  # health data must not be cached
    # The Werkzeug debugger page uses inline scripts, so the CSP is only
    # sent when the app is not in debug mode.
    if not current_app.debug:
        response.headers.setdefault("Content-Security-Policy", CSP)
    return response


# ==========================================================================
# 4. ACCOUNT ROUTES  (was account_routes.py)
# ==========================================================================
# Accounts, saved history and the clinician queue (Phase 4).
#
# Access rules, enforced here and covered by tests:
#   - A patient can only read, share or delete their own assessments.
#   - A clinician can only see assessments a patient has chosen to share, and
#     sees the patient's name and that assessment, never the email address.
#   - Anything the caller may not see is answered with 404, not 403, so the
#     API does not confirm that a record exists.
#   - Every clinician view/review, sharing change, deletion and claim is
#     written to the audit log.

account_bp = Blueprint("account", __name__, url_prefix="/api")


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _bad_request():
    return fail("bad_request", "Invalid JSON body.", 400)


def _ip() -> str:
    return request.remote_addr or "unknown"


def _rate_limited(*pairs):
    seconds = max(limiter.retry_after(key) for limiter, key in pairs)
    resp, status = fail("rate_limited", "Too many attempts. Please wait a few minutes.", 429)
    resp.headers["Retry-After"] = str(seconds)
    return resp, status


def _int_arg(name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _trend_for(conn, user_id: int) -> dict:
    return trend_info(count_recent_concerning(conn, user_id, TREND_DAYS))


# ───────────── Authentication ─────────────
@account_bp.post("/auth/register")
def register():
    ip = _ip()
    if REGISTER_LIMITER.blocked(ip):
        return _rate_limited((REGISTER_LIMITER, ip))
    REGISTER_LIMITER.hit(ip)

    data = _body()
    if data is None:
        return _bad_request()
    email = clean_email(data.get("email"))
    if not email:
        return fail("invalid_email", "Please enter a valid email address.", 400)
    name = clean_name(data.get("name"))
    if not name:
        return fail("name_required", "Please enter your name.", 400)
    password = data.get("password")
    if check_password(password, email):
        return fail("weak_password", "Choose a stronger password (at least 8 characters).", 400)

    conn = get_conn()
    try:
        uid = create_user(conn, email, name, hash_password(password))
    except EmailTaken:
        return fail("email_taken", "An account with this email already exists.", 409)
    user = get_user_by_id(conn, uid)
    login_user(user)
    return jsonify({"user": public_user(user)}), 201


@account_bp.post("/auth/login")
def login():
    data = _body()
    if data is None:
        return _bad_request()
    ip = _ip()
    email = clean_email(data.get("email")) or ""
    acct_key = f"{ip}|{email}"
    if LOGIN_ACCOUNT_LIMITER.blocked(acct_key) or LOGIN_IP_LIMITER.blocked(ip):
        return _rate_limited((LOGIN_ACCOUNT_LIMITER, acct_key), (LOGIN_IP_LIMITER, ip))

    conn = get_conn()
    user = get_user_by_email(conn, email) if email else None
    # Always run one hash check, so unknown emails take as long as wrong passwords.
    hash_ok = verify_password(user["password_hash"] if user else DUMMY_HASH, data.get("password"))
    if user is None or not hash_ok:
        LOGIN_ACCOUNT_LIMITER.hit(acct_key)
        LOGIN_IP_LIMITER.hit(ip)
        return fail("bad_credentials", "Incorrect email or password.", 401)

    LOGIN_ACCOUNT_LIMITER.reset(acct_key)
    login_user(user)
    return jsonify({"user": public_user(user)})


@account_bp.post("/auth/logout")
def logout():
    logout_user()
    return jsonify({"ok": True})


@account_bp.get("/auth/me")
def me():
    user = current_user()
    return jsonify({"user": public_user(user) if user else None})


@account_bp.post("/account/delete")
@login_required
def delete_account():
    data = _body()
    if data is None:
        return _bad_request()
    user = current_user()
    ip = _ip()
    key = f"{ip}|{user['email']}"
    if LOGIN_ACCOUNT_LIMITER.blocked(key):
        return _rate_limited((LOGIN_ACCOUNT_LIMITER, key))
    if not verify_password(user["password_hash"], data.get("password")):
        LOGIN_ACCOUNT_LIMITER.hit(key)
        return fail("bad_credentials", "Incorrect password.", 401)

    conn = get_conn()
    audit(conn, user["id"], "account_delete", user["id"])
    delete_user(conn, user["id"])  # cascades to every saved assessment
    logout_user()
    return jsonify({"ok": True})


# ───────────── Patient history ─────────────
def _own(assessment_id: int):
    user = current_user()
    row = get_assessment(get_conn(), assessment_id)
    return row if row is not None and row["user_id"] == user["id"] else None


@account_bp.get("/history")
@login_required
def history():
    user = current_user()
    conn = get_conn()
    limit = _int_arg("limit", 20, 1, 50)
    offset = _int_arg("offset", 0, 0, 1_000_000)
    rows = list_assessments(conn, user["id"], limit, offset)
    return jsonify(
        {
            "items": [serialize_summary(r) for r in rows],
            "total": count_assessments(conn, user["id"]),
            "trend": _trend_for(conn, user["id"]),
        }
    )


@account_bp.get("/history/<int:assessment_id>")
@login_required
def history_detail(assessment_id):
    row = _own(assessment_id)
    if row is None:
        return fail("not_found", "That record was not found.", 404)
    return jsonify(serialize_detail(row))


@account_bp.delete("/history/<int:assessment_id>")
@login_required
def history_delete(assessment_id):
    user = current_user()
    conn = get_conn()
    if not delete_assessment(conn, assessment_id, user["id"]):
        return fail("not_found", "That record was not found.", 404)
    audit(conn, user["id"], "assessment_delete", assessment_id)
    return jsonify({"ok": True})


@account_bp.post("/history/<int:assessment_id>/share")
@login_required
def history_share(assessment_id):
    data = _body()
    if data is None or not isinstance(data.get("shared"), bool):
        return fail("bad_request", "Send {\"shared\": true or false}.", 400)
    user = current_user()
    conn = get_conn()
    if not set_shared(conn, assessment_id, user["id"], data["shared"]):
        return fail("not_found", "That record was not found.", 404)
    audit(conn, user["id"], "share_on" if data["shared"] else "share_off", assessment_id)
    return jsonify({"shared": data["shared"]})


@account_bp.post("/history/claim")
@login_required
def history_claim():
    """Saves the assessment a guest finished just before signing in."""
    data = _body()
    if data is None:
        return _bad_request()
    from flask import current_app

    payload, nonce = read_claim_token(current_app.secret_key, data.get("token"))
    if payload is None:
        return fail("claim_invalid", "This result can no longer be saved.", 400)

    user = current_user()
    conn = get_conn()
    existing = find_by_nonce(conn, nonce)
    if existing is not None:
        if existing["user_id"] != user["id"]:
            return fail("claim_invalid", "This result can no longer be saved.", 409)
        assessment_id = existing["id"]  # same user claiming twice: no duplicate
    else:
        assessment_id = save_assessment(conn, user["id"], payload, claim_nonce=nonce)
        audit(conn, user["id"], "claim", assessment_id)
    return jsonify({"assessmentId": assessment_id, "trend": _trend_for(conn, user["id"])})


# ───────────── Clinician ─────────────
@account_bp.get("/clinician/queue")
@role_required("clinician")
def clinician_queue():
    status = request.args.get("status", "new")
    severity = request.args.get("severity")
    rows, total = queue_rows(
        get_conn(),
        status=status,
        severity=severity,
        limit=_int_arg("limit", 30, 1, 100),
        offset=_int_arg("offset", 0, 0, 1_000_000),
    )
    return jsonify({"items": [serialize_summary(r) for r in rows], "total": total})


@account_bp.get("/clinician/assessments/<int:assessment_id>")
@role_required("clinician")
def clinician_detail(assessment_id):
    conn = get_conn()
    row = get_shared_assessment(conn, assessment_id)
    if row is None:
        return fail("not_found", "That record was not found.", 404)
    audit(conn, current_user()["id"], "clinician_view", assessment_id)
    return jsonify(serialize_detail(row))


@account_bp.post("/clinician/assessments/<int:assessment_id>/review")
@role_required("clinician")
def clinician_review(assessment_id):
    data = _body()
    if data is None:
        return _bad_request()
    note = data.get("note", "")
    if not isinstance(note, str):
        return fail("bad_request", "The note must be text.", 400)
    conn = get_conn()
    clinician = current_user()
    reviewed_at = review_assessment(conn, assessment_id, clinician["id"], clip(note, 1000))
    if reviewed_at is None:
        return fail("not_found", "That record was not found.", 404)
    audit(conn, clinician["id"], "clinician_review", assessment_id)
    return jsonify({"ok": True, "reviewedAt": reviewed_at})
