"""SQLite storage for accounts and saved assessments (Phase 4).

Design notes
- Plain sqlite3 from the standard library; no ORM, no new dependency.
- Every query is parameterised. Nothing is ever built by string formatting
  from user input.
- Photos are never stored. Only the conversation text and the structured
  result are kept.
- Deleting a user cascades to their assessments (foreign keys are ON).
- audit_log records who did what to which record (clinician views and
  reviews, sharing changes, deletions). It is not shown in the UI; it
  exists so access to health data is accountable.

The database path comes from the MEDITECH_DB environment variable, else
data/meditech.db. If your project folder is synced by OneDrive, point
MEDITECH_DB at a folder outside it: sync clients can lock SQLite files."""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone


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


def clinician_queue(conn, status="new", severity=None, limit=30, offset=0):
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
