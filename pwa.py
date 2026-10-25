"""Progressive Web App support (Phase 5): the web app manifest and the service worker.

The service worker must be served from the site root (/sw.js) so it controls
the whole app, which is why it is a route here and not a file in static/.

Versioning: the worker's cache name contains a hash of every file it
precaches (plus the worker's own code). Change any of those files and /sw.js
changes, so browsers install the new version and the page offers an update.
Nobody gets stuck on stale code, and nothing needs a manual version bump.

What the worker caches: the app shell only (page, scripts, styles, fonts,
icons). It never touches /api/: assessments, sign-in and saved history are
never stored by the service worker. See templates/sw.js."""

import hashlib
import json
import logging
from pathlib import Path

from flask import Blueprint, Response

log = logging.getLogger(__name__)
bp = Blueprint("pwa", __name__)

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


@bp.get("/sw.js")
def service_worker():
    source = SW_TEMPLATE.read_text(encoding="utf-8")
    source = source.replace("__VERSION__", cache_version()).replace("__PRECACHE__", json.dumps(precache_urls()))
    resp = Response(source, mimetype="application/javascript")
    # Browsers must re-check the worker file every time, or updates never arrive.
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@bp.get("/manifest.webmanifest")
def manifest():
    resp = Response(manifest_bytes(), mimetype="application/manifest+json")
    resp.headers["Cache-Control"] = "no-cache"
    return resp
