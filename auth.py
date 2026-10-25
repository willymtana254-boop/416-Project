"""Authentication and request-security helpers (Phase 4).

- Passwords are hashed with PBKDF2-SHA256 (werkzeug). Plain passwords are
  never stored or logged.
- Login failures are rate limited per account+IP and per IP. Unknown emails
  and wrong passwords give the same answer in the same time, so the login
  form does not reveal which emails have accounts.
- Sessions are signed cookies: HttpOnly, SameSite=Lax. Set
  SESSION_COOKIE_SECURE=1 when serving over https.
- State-changing endpoints only accept a JSON body. Browsers cannot send
  cross-site JSON without a CORS preflight (which this app never allows),
  and SameSite=Lax keeps the cookie off cross-site POSTs, so a hostile page
  cannot act as a signed-in user.
- Clinician accounts cannot be created through the website (see
  create_clinician.py), so nobody can promote themselves."""

import os
import re
import secrets
import threading
import time
from datetime import timedelta

from flask import current_app, g, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash

import db

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
        row = db.get_user_by_id(db.get_conn(), uid)
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
    path = db_path or db.default_db_path()
    app.config.update(
        DATABASE=path,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # photos arrive as base64 in JSON
    )
    app.secret_key = load_secret_key(os.path.dirname(os.path.abspath(path)))
    app.teardown_appcontext(db.close_conn)
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
