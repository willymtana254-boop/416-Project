"""Accounts, saved history and the clinician queue (Phase 4).

Access rules, enforced here and covered by tests:
  - A patient can only read, share or delete their own assessments.
  - A clinician can only see assessments a patient has chosen to share, and
    sees the patient's name and that assessment, never the email address.
  - Anything the caller may not see is answered with 404, not 403, so the
    API does not confirm that a record exists.
  - Every clinician view/review, sharing change, deletion and claim is
    written to the audit log."""

from flask import Blueprint, jsonify, request

import auth
import db
import records
from auth import fail

bp = Blueprint("account", __name__, url_prefix="/api")


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
    return records.trend_info(db.count_recent_concerning(conn, user_id, records.TREND_DAYS))


# ───────────── Authentication ─────────────
@bp.post("/auth/register")
def register():
    ip = _ip()
    if auth.REGISTER_LIMITER.blocked(ip):
        return _rate_limited((auth.REGISTER_LIMITER, ip))
    auth.REGISTER_LIMITER.hit(ip)

    data = _body()
    if data is None:
        return _bad_request()
    email = auth.clean_email(data.get("email"))
    if not email:
        return fail("invalid_email", "Please enter a valid email address.", 400)
    name = auth.clean_name(data.get("name"))
    if not name:
        return fail("name_required", "Please enter your name.", 400)
    password = data.get("password")
    if auth.check_password(password, email):
        return fail("weak_password", "Choose a stronger password (at least 8 characters).", 400)

    conn = db.get_conn()
    try:
        uid = db.create_user(conn, email, name, auth.hash_password(password))
    except db.EmailTaken:
        return fail("email_taken", "An account with this email already exists.", 409)
    user = db.get_user_by_id(conn, uid)
    auth.login_user(user)
    return jsonify({"user": auth.public_user(user)}), 201


@bp.post("/auth/login")
def login():
    data = _body()
    if data is None:
        return _bad_request()
    ip = _ip()
    email = auth.clean_email(data.get("email")) or ""
    acct_key = f"{ip}|{email}"
    if auth.LOGIN_ACCOUNT_LIMITER.blocked(acct_key) or auth.LOGIN_IP_LIMITER.blocked(ip):
        return _rate_limited((auth.LOGIN_ACCOUNT_LIMITER, acct_key), (auth.LOGIN_IP_LIMITER, ip))

    conn = db.get_conn()
    user = db.get_user_by_email(conn, email) if email else None
    # Always run one hash check, so unknown emails take as long as wrong passwords.
    hash_ok = auth.verify_password(user["password_hash"] if user else auth.DUMMY_HASH, data.get("password"))
    if user is None or not hash_ok:
        auth.LOGIN_ACCOUNT_LIMITER.hit(acct_key)
        auth.LOGIN_IP_LIMITER.hit(ip)
        return fail("bad_credentials", "Incorrect email or password.", 401)

    auth.LOGIN_ACCOUNT_LIMITER.reset(acct_key)
    auth.login_user(user)
    return jsonify({"user": auth.public_user(user)})


@bp.post("/auth/logout")
def logout():
    auth.logout_user()
    return jsonify({"ok": True})


@bp.get("/auth/me")
def me():
    user = auth.current_user()
    return jsonify({"user": auth.public_user(user) if user else None})


@bp.post("/account/delete")
@auth.login_required
def delete_account():
    data = _body()
    if data is None:
        return _bad_request()
    user = auth.current_user()
    ip = _ip()
    key = f"{ip}|{user['email']}"
    if auth.LOGIN_ACCOUNT_LIMITER.blocked(key):
        return _rate_limited((auth.LOGIN_ACCOUNT_LIMITER, key))
    if not auth.verify_password(user["password_hash"], data.get("password")):
        auth.LOGIN_ACCOUNT_LIMITER.hit(key)
        return fail("bad_credentials", "Incorrect password.", 401)

    conn = db.get_conn()
    db.audit(conn, user["id"], "account_delete", user["id"])
    db.delete_user(conn, user["id"])  # cascades to every saved assessment
    auth.logout_user()
    return jsonify({"ok": True})


# ───────────── Patient history ─────────────
def _own(assessment_id: int):
    user = auth.current_user()
    row = db.get_assessment(db.get_conn(), assessment_id)
    return row if row is not None and row["user_id"] == user["id"] else None


@bp.get("/history")
@auth.login_required
def history():
    user = auth.current_user()
    conn = db.get_conn()
    limit = _int_arg("limit", 20, 1, 50)
    offset = _int_arg("offset", 0, 0, 1_000_000)
    rows = db.list_assessments(conn, user["id"], limit, offset)
    return jsonify(
        {
            "items": [records.serialize_summary(r) for r in rows],
            "total": db.count_assessments(conn, user["id"]),
            "trend": _trend_for(conn, user["id"]),
        }
    )


@bp.get("/history/<int:assessment_id>")
@auth.login_required
def history_detail(assessment_id):
    row = _own(assessment_id)
    if row is None:
        return fail("not_found", "That record was not found.", 404)
    return jsonify(records.serialize_detail(row))


@bp.delete("/history/<int:assessment_id>")
@auth.login_required
def history_delete(assessment_id):
    user = auth.current_user()
    conn = db.get_conn()
    if not db.delete_assessment(conn, assessment_id, user["id"]):
        return fail("not_found", "That record was not found.", 404)
    db.audit(conn, user["id"], "assessment_delete", assessment_id)
    return jsonify({"ok": True})


@bp.post("/history/<int:assessment_id>/share")
@auth.login_required
def history_share(assessment_id):
    data = _body()
    if data is None or not isinstance(data.get("shared"), bool):
        return fail("bad_request", "Send {\"shared\": true or false}.", 400)
    user = auth.current_user()
    conn = db.get_conn()
    if not db.set_shared(conn, assessment_id, user["id"], data["shared"]):
        return fail("not_found", "That record was not found.", 404)
    db.audit(conn, user["id"], "share_on" if data["shared"] else "share_off", assessment_id)
    return jsonify({"shared": data["shared"]})


@bp.post("/history/claim")
@auth.login_required
def history_claim():
    """Saves the assessment a guest finished just before signing in."""
    data = _body()
    if data is None:
        return _bad_request()
    from flask import current_app

    payload, nonce = records.read_claim_token(current_app.secret_key, data.get("token"))
    if payload is None:
        return fail("claim_invalid", "This result can no longer be saved.", 400)

    user = auth.current_user()
    conn = db.get_conn()
    existing = db.find_by_nonce(conn, nonce)
    if existing is not None:
        if existing["user_id"] != user["id"]:
            return fail("claim_invalid", "This result can no longer be saved.", 409)
        assessment_id = existing["id"]  # same user claiming twice: no duplicate
    else:
        assessment_id = db.save_assessment(conn, user["id"], payload, claim_nonce=nonce)
        db.audit(conn, user["id"], "claim", assessment_id)
    return jsonify({"assessmentId": assessment_id, "trend": _trend_for(conn, user["id"])})


# ───────────── Clinician ─────────────
@bp.get("/clinician/queue")
@auth.role_required("clinician")
def clinician_queue():
    status = request.args.get("status", "new")
    severity = request.args.get("severity")
    rows, total = db.clinician_queue(
        db.get_conn(),
        status=status,
        severity=severity,
        limit=_int_arg("limit", 30, 1, 100),
        offset=_int_arg("offset", 0, 0, 1_000_000),
    )
    return jsonify({"items": [records.serialize_summary(r) for r in rows], "total": total})


@bp.get("/clinician/assessments/<int:assessment_id>")
@auth.role_required("clinician")
def clinician_detail(assessment_id):
    conn = db.get_conn()
    row = db.get_shared_assessment(conn, assessment_id)
    if row is None:
        return fail("not_found", "That record was not found.", 404)
    db.audit(conn, auth.current_user()["id"], "clinician_view", assessment_id)
    return jsonify(records.serialize_detail(row))


@bp.post("/clinician/assessments/<int:assessment_id>/review")
@auth.role_required("clinician")
def clinician_review(assessment_id):
    data = _body()
    if data is None:
        return _bad_request()
    note = data.get("note", "")
    if not isinstance(note, str):
        return fail("bad_request", "The note must be text.", 400)
    conn = db.get_conn()
    clinician = auth.current_user()
    reviewed_at = db.review_assessment(conn, assessment_id, clinician["id"], records.clip(note, 1000))
    if reviewed_at is None:
        return fail("not_found", "That record was not found.", 404)
    db.audit(conn, clinician["id"], "clinician_review", assessment_id)
    return jsonify({"ok": True, "reviewedAt": reviewed_at})
