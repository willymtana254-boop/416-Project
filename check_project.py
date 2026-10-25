"""Checks that your MediTECH AI project folder is complete and up to date.

    python check_project.py

Run it from the project folder. It looks for:
  * every file the app needs, and that each one is the CURRENT version
    (each file has a marker that older versions do not contain)
  * stray or old copies: "app (1).py", a leftover rag/ folder, style.css...
  * your .env (without ever printing the key), and the reference-note index

It only reads files. It never imports the app, so it does not create a
database or call any API."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# path -> (phase, what it is, markers that must all appear in the file)
FILES = {
    "app.py": (1, "Flask app and /api/chat", ["auth.configure(app)", "_persist_assessment", "pwa_bp"]),
    "prompts.py": (1, "triage rules for the model", ["Never give medication advice", "extra_instructions", "ONE symptom"]),
    "gemini_client.py": (1, "talks to Gemini", ["extra_instructions", "functionDeclarations"]),
    "requirements.txt": (1, "Python packages", ["flask", "requests", "python-dotenv"]),
    "knowledge_base.py": (2, "22 reference notes", ['"id": "meningitis"', '"id": "heart-attack"']),
    "retrieval.py": (2, "finds relevant notes", ["gemini-embedding-001", "QUERY_TIMEOUT_S"]),
    "build_index.py": (2, "builds the search index", ["kb_cache.json"]),
    "regions.py": (3, "language and region context", ["REGION_NOTES", "LANGUAGE_RULES"]),
    "facilities.py": (3, "nearest health facilities", ["TIME_BUDGET_S", "OVERPASS_URLS"]),
    "db.py": (4, "SQLite storage", ["CREATE TABLE IF NOT EXISTS users", "audit_log"]),
    "records.py": (4, "saved-assessment logic", ["make_claim_token", "trend_info"]),
    "auth.py": (4, "login and security", ["RateLimiter", "add_security_headers", "manifest-src"]),
    "pwa.py": ("5a", "installable app: manifest and service worker", ["def cache_version", "SHELL = ["]),
    "account_routes.py": (4, "accounts, history, clinician API", ["clinician_queue", "history_claim"]),
    "create_clinician.py": (4, "makes clinician accounts", ["create_or_promote"]),
    "check_project.py": (4, "this checker", []),
    "templates/index.html": (4, "the page", ["account.js", "authCard", "facCard", "homeView", "manifest.webmanifest", "pwa.js"]),
    "templates/sw.js": ("5a", "the service worker", ["__VERSION__", "__PRECACHE__"]),
    "static/css/styles.css": (4, "styling", ["Phase 4", ".fac-item", "@font-face"]),
    "static/js/app.js": (4, "assessment page logic", ["window.MT", "hooks.afterRender"]),
    "static/js/account.js": (4, "sign-in, history, clinician view", ["MT.addStrings", "clinFilters"]),
    "static/js/pwa.js": ("5a", "install button and app updates", ["registerWorker", "beforeinstallprompt"]),
    "evaluation/__init__.py": (6, "evaluation package", []),
    "evaluation/cases.py": (6, "57 test cases", ["CASES = ["]),
    "evaluation/patient.py": (6, "scripted patient", ["class Patient"]),
    "evaluation/scoring.py": (6, "metrics and safety checks", ["def wilson", "def check_run"]),
    "evaluation/report.py": (6, "report generator", ["def analyse", "def render_markdown"]),
    "evaluation/run_eval.py": (6, "runs the cases", ["def run_case", "--no-rag"]),
    "evaluation/mock_model.py": (6, "dry-run stand-in", ["def fake_agent"]),
    "evaluation/selftest.py": (6, "tests the harness", ["ALL "]),
    "evaluation/README.md": (6, "how to use the evaluation", []),
}
PNG, WOFF2 = b"\x89PNG\r\n\x1a\n", b"wOF2"
BINARY = {
    "static/icons/icon-192.png": ("5a", "app icon", PNG), "static/icons/icon-512.png": ("5a", "app icon", PNG),
    "static/icons/icon-maskable-512.png": ("5a", "app icon (Android shapes)", PNG),
    "static/icons/apple-touch-icon.png": ("5a", "iPhone icon", PNG), "static/icons/favicon-32.png": ("5a", "browser tab icon", PNG),
    "static/fonts/syne-latin-400-normal.woff2": ("5a", "font", WOFF2), "static/fonts/syne-latin-500-normal.woff2": ("5a", "font", WOFF2),
    "static/fonts/syne-latin-600-normal.woff2": ("5a", "font", WOFF2), "static/fonts/fraunces-latin-400-normal.woff2": ("5a", "font", WOFF2),
    "static/fonts/fraunces-latin-600-normal.woff2": ("5a", "font", WOFF2),
}
OPTIONAL = {"README.md", ".env.example", ".gitignore", "data/.gitkeep"}
KNOWN_ROOT_PY = {Path(p).name for p in FILES if "/" not in p}

problems, warnings = [], []


def line(tag, text):
    print(f"  [{tag:<7}] {text}")


def read(path):
    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def check_files():
    print("Files")
    for path, (phase, what, markers) in FILES.items():
        text = read(path)
        if text is None:
            if (ROOT / path).exists():
                line("PROBLEM", f"{path}: cannot be read as text")
            else:
                line("MISSING", f"{path}  (phase {phase}: {what})")
            problems.append(f"missing {path}")
            continue
        absent = [m for m in markers if m not in text]
        if absent:
            line("OLD?", f"{path}  is present but looks like an OLD version (does not contain {absent[0]!r})")
            problems.append(f"old version of {path}")
        else:
            line("ok", f"{path}")
    for path, (phase, what, magic) in BINARY.items():
        f = ROOT / path
        if not f.exists():
            line("MISSING", f"{path}  (phase {phase}: {what})"); problems.append(f"missing {path}")
        elif f.stat().st_size == 0 or not f.read_bytes().startswith(magic):
            line("PROBLEM", f"{path} is damaged (wrong or empty file; download it again)"); problems.append(f"damaged {path}")
        else:
            line("ok", path)
    # Python files must at least be valid Python (compile only: no files written)
    for path in FILES:
        if path.endswith(".py") and read(path):
            try:
                compile(read(path), path, "exec")
            except SyntaxError as exc:
                line("PROBLEM", f"{path}: syntax error at line {exc.lineno}: {exc.msg} (file damaged or cut off?)")
                problems.append(f"syntax error in {path}")


def check_strays():
    print("\nStray or old files")
    found = False
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).as_posix()
        if any(part in (".venv", "venv", "__pycache__", "node_modules", ".git") for part in p.parts):
            continue
        if not p.is_file() and not p.is_dir():
            continue
        name = p.name
        if re.search(r" \(\d+\)", name) or name.lower().startswith("download") or name.endswith((".new", ".bak", ".orig", ".tmp")):
            line("STRAY", f"{rel}   (a leftover download or backup; delete it)")
            problems.append(f"stray {rel}")
            found = True
    for rel, why in [
        ("rag", "old folder from an earlier design; delete it"),
        ("static/css/style.css", "wrong name; the page loads styles.css (plural)"),
        ("evaluation/evaluation", "the zip was extracted one folder too deep; move its contents up"),
        ("data/knowledge_base.json", "old file, not used"),
    ]:
        if (ROOT / rel).exists():
            line("STRAY", f"{rel}   ({why})")
            problems.append(f"stray {rel}")
            found = True
    extra = sorted(p.name for p in ROOT.glob("*.py") if p.name not in KNOWN_ROOT_PY)
    if extra:
        line("note", "Python files here that the project does not use: " + ", ".join(extra))
        found = True
    if not found:
        line("ok", "none found")


def check_env():
    print("\nSettings")
    env = ROOT / ".env"
    if not env.exists():
        line("MISSING", ".env  (copy .env.example to .env and add your Gemini key)")
        problems.append("missing .env")
        return
    text = env.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^\s*GEMINI_API_KEY\s*=\s*(.*)$", text, re.M)
    value = (m.group(1).strip().strip("\"'") if m else "")
    if not value or "your_gemini_api_key" in value:
        line("PROBLEM", ".env has no real GEMINI_API_KEY yet")
        problems.append("no API key")
    else:
        line("ok", f".env has a GEMINI_API_KEY ({len(value)} characters; not shown)")
    gi = read(".gitignore")
    if gi is not None and not all(x in gi for x in ("data/meditech.db", "data/.secret_key")):
        line("warn", ".gitignore does not list data/meditech.db and data/.secret_key (add them before using git)")
        warnings.append(".gitignore")


def check_index():
    print("\nReference-note index")
    kb = read("knowledge_base.py") or ""
    wanted = len(re.findall(r'^\s*"id":', kb, re.M))
    idx = ROOT / "data" / "kb_embeddings.json"
    if not idx.exists():
        line("MISSING", "data/kb_embeddings.json  (run: python build_index.py)")
        problems.append("no index")
        return
    try:
        entries = json.loads(idx.read_text(encoding="utf-8"))
        have = len(entries)
        bad = [e.get("id") for e in entries if not isinstance(e.get("embedding"), list) or len(e["embedding"]) < 100]
    except (OSError, ValueError, AttributeError):
        line("PROBLEM", "data/kb_embeddings.json is unreadable (run: python build_index.py)")
        problems.append("bad index")
        return
    if have != wanted or bad:
        line("OLD?", f"the index has {have} entries but knowledge_base.py has {wanted}. Run: python build_index.py")
        problems.append("index out of date")
    else:
        line("ok", f"{have} entries, matches knowledge_base.py")


def main():
    print(f"MediTECH AI project check\nFolder: {ROOT}\nPython: {sys.version.split()[0]}\n")
    if sys.version_info >= (3, 14):
        warnings.append("python 3.14")
        print("  [warn   ] Python 3.14 is very new and some packages lack builds for it. Use the 3.13 virtual environment.\n")
    check_files()
    check_strays()
    check_env()
    check_index()
    print()
    if problems:
        print(f"{len(problems)} thing(s) to fix:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Everything is in place." + (" (with warnings above)" if warnings else ""))


if __name__ == "__main__":
    main()
