"""One-off jobs for MediTECH AI.  Run from the project folder:

    python manage.py index        build the reference-note index (needs GEMINI_API_KEY in .env)
    python manage.py clinician    create a clinician account, or promote an existing one
    python manage.py check        check the project folder is complete and ready

index     Embeds the notes in knowledge_base.py into data/kb_embeddings.json. Run it
          whenever the notes change. It is safe to re-run: embeddings already computed
          for unchanged notes are reused, and progress is saved after every note, so a
          dropped connection continues where it stopped. The live index is replaced
          only once every note is done.
clinician Clinician accounts cannot be created from the website, so nobody can give
          themselves access to other people's shared assessments. You run this yourself.
check     Only reads files. It never starts the app, creates a database or calls an API.
"""

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from accounts import (
    check_password,
    clean_email,
    clean_name,
    connect,
    create_user,
    default_db_path,
    get_user_by_email,
    hash_password,
    init_db,
    set_role,
)
from ai import INDEX_PATH, RetrievalError, embed_text
from knowledge_base import KNOWLEDGE_BASE

ROOT = Path(__file__).resolve().parent


# ==========================================================================
# index: build the reference-note embeddings  (was build_index.py)
# ==========================================================================
CACHE_PATH = os.path.join(os.path.dirname(INDEX_PATH), "kb_cache.json")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json_atomic(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _load_cache() -> dict:
    """id -> {"hash": ..., "embedding": [...]}, seeded from the cache file
    and from the previous index so unchanged entries are never re-embedded."""
    cache = {}
    previous = _read_json(INDEX_PATH)
    if isinstance(previous, list):
        for e in previous:
            if isinstance(e, dict) and {"id", "text", "embedding"} <= set(e):
                cache[e["id"]] = {"hash": _hash(e["text"]), "embedding": e["embedding"]}
    saved = _read_json(CACHE_PATH)
    if isinstance(saved, dict):
        for k, v in saved.items():
            if isinstance(v, dict) and {"hash", "embedding"} <= set(v):
                cache[k] = v
    return cache


def build_index():
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set. Add it to .env first.")

    cache = _load_cache()
    indexed = []
    new_count = reused_count = 0

    for entry in KNOWLEDGE_BASE:
        h = _hash(entry["text"])
        hit = cache.get(entry["id"])
        if hit and hit["hash"] == h:
            print(f"Reusing:   {entry['title']}")
            embedding = hit["embedding"]
            reused_count += 1
        else:
            print(f"Embedding: {entry['title']}...")
            try:
                embedding = embed_text(entry["text"], task_type="RETRIEVAL_DOCUMENT", timeout=40, retries=4)
            except RetrievalError as exc:
                print(f"\nStopped on '{entry['title']}': {exc}")
                print("Progress is saved. Run `python manage.py index` again to continue.")
                raise SystemExit(1)
            cache[entry["id"]] = {"hash": h, "embedding": embedding}
            _write_json_atomic(CACHE_PATH, cache)
            new_count += 1
        indexed.append({**entry, "embedding": embedding})

    # Drop cache rows for entries that no longer exist, then publish the index.
    live_ids = {e["id"] for e in KNOWLEDGE_BASE}
    _write_json_atomic(CACHE_PATH, {k: v for k, v in cache.items() if k in live_ids})
    _write_json_atomic(INDEX_PATH, indexed)

    print(f"\nWrote {len(indexed)} entries to {INDEX_PATH} ({new_count} new, {reused_count} reused)")


# ==========================================================================
# clinician: create or promote a clinician account  (was create_clinician.py)
# ==========================================================================
def create_or_promote(conn, email: str, name: str, password: str):
    """Returns ("created" | "promoted" | "already", user_id)."""
    existing = get_user_by_email(conn, email)
    if existing is not None:
        if existing["role"] == "clinician":
            return "already", existing["id"]
        set_role(conn, existing["id"], "clinician")
        return "promoted", existing["id"]
    uid = create_user(conn, email, name, hash_password(password), role="clinician")
    return "created", uid


def clinician(args):
    email = clean_email(args.email or input("Email: "))
    if not email:
        sys.exit("That is not a valid email address.")

    path = default_db_path()
    init_db(path)
    conn = connect(path)
    try:
        existing = get_user_by_email(conn, email)
        if existing is not None:
            result, uid = create_or_promote(conn, email, existing["name"], "")
        else:
            name = clean_name(args.name or input("Name: "))
            if not name:
                sys.exit("Please enter a name (1-80 characters).")
            password = getpass.getpass("Password (not shown): ")
            if getpass.getpass("Repeat password: ") != password:
                sys.exit("The passwords do not match.")
            if check_password(password, email):
                sys.exit("Choose a stronger password (at least 8 characters, not a common one).")
            result, uid = create_or_promote(conn, email, name, password)
    finally:
        conn.close()

    messages = {
        "created": "Created clinician account",
        "promoted": "Promoted existing account to clinician",
        "already": "That account is already a clinician",
    }
    print(f"{messages[result]}: {email} (id {uid}) in {path}")


# ==========================================================================
# check: is the project folder complete?  (replaces check_project.py)
# ==========================================================================
REQUIRED = [
    "app.py", "ai.py", "accounts.py", "knowledge_base.py", "manage.py",
    "requirements.txt", ".env.example",
    "templates/index.html", "templates/sw.js",
    "static/css/styles.css", "static/js/app.js",
    "evaluation/cases.py", "evaluation/scoring.py", "evaluation/report.py",
    "evaluation/run_eval.py", "evaluation/selftest.py",
]
# files from the older, many-file layout; harmless, but they only confuse readers
OLD_FILES = [
    "auth.py", "db.py", "records.py", "account_routes.py", "regions.py", "prompts.py", "retrieval.py",
    "gemini_client.py", "pwa.py", "build_index.py", "create_clinician.py", "check_project.py", "facilities.py",
    "static/js/account.js", "static/js/pwa.js",
    "evaluation/patient.py", "evaluation/mock_model.py",
]


def check(_args):
    problems, notes = [], []

    def line(tag, text):
        print(f"  [{tag:<7}] {text}")

    print(f"MediTECH AI project check\nFolder: {ROOT}\nPython: {sys.version.split()[0]}\n\nFiles")
    for rel in REQUIRED:
        f = ROOT / rel
        if not f.exists():
            line("MISSING", rel)
            problems.append(f"missing {rel}")
        elif f.suffix == ".py":
            try:
                compile(f.read_text(encoding="utf-8"), rel, "exec")
            except SyntaxError as exc:
                line("PROBLEM", f"{rel}: syntax error at line {exc.lineno} (file damaged or cut off?)")
                problems.append(f"syntax error in {rel}")
    if not problems:
        line("ok", f"all {len(REQUIRED)} required files are present and the Python files compile")

    print("\nOld files from the previous layout")
    old = [rel for rel in OLD_FILES if (ROOT / rel).exists()]
    for rel in old:
        line("OLD", f"{rel}  (no longer used; delete it)")
        notes.append(rel)
    if not old:
        line("ok", "none found")

    print("\nSettings")
    env = ROOT / ".env"
    if not env.exists():
        line("MISSING", ".env  (copy .env.example to .env and add your Gemini key)")
        problems.append("missing .env")
    else:
        m = re.search(r"^\s*GEMINI_API_KEY\s*=\s*(.*)$", env.read_text(encoding="utf-8", errors="replace"), re.M)
        value = m.group(1).strip().strip("\"'") if m else ""
        if not value or "your_gemini_api_key" in value:
            line("PROBLEM", ".env has no real GEMINI_API_KEY yet")
            problems.append("no API key")
        else:
            line("ok", f".env has a GEMINI_API_KEY ({len(value)} characters; not shown)")

    print("\nReference-note index")
    index = Path(INDEX_PATH)
    wanted = len(KNOWLEDGE_BASE)
    if not index.exists():
        line("MISSING", "data/kb_embeddings.json  (run: python manage.py index)")
        problems.append("no index")
    else:
        try:
            entries = json.loads(index.read_text(encoding="utf-8"))
            have = len(entries)
            bad = [e.get("id") for e in entries if not isinstance(e.get("embedding"), list) or len(e["embedding"]) < 100]
        except (OSError, ValueError, AttributeError):
            have, bad = -1, ["unreadable"]
        if have != wanted or bad:
            line("OLD?", f"the index has {have} entries but knowledge_base.py has {wanted}. Run: python manage.py index")
            problems.append("index out of date")
        else:
            line("ok", f"{have} entries, matches knowledge_base.py")

    print()
    if problems:
        print(f"{len(problems)} thing(s) to fix:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Everything is in place." + (" (Old files are listed above; you can delete them.)" if notes else ""))


# ==========================================================================
def main(argv=None):
    parser = argparse.ArgumentParser(description="One-off jobs for MediTECH AI.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index", help="build the reference-note index").set_defaults(run=lambda a: build_index())
    c = sub.add_parser("clinician", help="create or promote a clinician account")
    c.add_argument("--email", help="clinician email address")
    c.add_argument("--name", help="clinician display name")
    c.set_defaults(run=clinician)
    sub.add_parser("check", help="check the project folder").set_defaults(run=check)
    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
