"""Embedding + cosine-similarity retrieval over the local knowledge base.

Kept deliberately simple (plain Python, no vector DB dependency) since the
corpus is small (~20 entries). Swap in Chroma or pgvector later if the
knowledge base grows significantly: the retrieve() function's signature
is the only thing other modules depend on, so that swap stays contained
to this file.

Failure policy: embed_text() turns every network or API problem into a
RetrievalError, and retrieve() turns a RetrievalError into "no extra
context". A flaky connection must never break a patient's conversation."""

import json
import math
import os
import time

import requests

EMBED_MODEL = "gemini-embedding-001"
EMBED_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent"
)
INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "kb_embeddings.json")

# Chat-time lookups fail fast (the conversation continues without notes).
QUERY_TIMEOUT_S = 12

_index_cache = None
_index_mtime = None


class RetrievalError(Exception):
    pass


def embed_text(
    text: str,
    task_type: str = "RETRIEVAL_QUERY",
    timeout: float = QUERY_TIMEOUT_S,
    retries: int = 0,
) -> list[float]:
    """Calls Gemini's embedding model. task_type should be
    RETRIEVAL_DOCUMENT when embedding knowledge base entries (build_index.py)
    and RETRIEVAL_QUERY when embedding a user's conversation (retrieve()).

    Network errors, timeouts, 429 and 5xx responses are retried `retries`
    times with backoff (2s, 4s, 8s). Other errors, such as a bad or leaked
    API key, fail immediately because retrying cannot help. Everything is
    raised as RetrievalError."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RetrievalError("GEMINI_API_KEY is not set.")

    last_problem = "unknown error"
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(2 ** attempt, 8))
        try:
            res = requests.post(
                f"{EMBED_ENDPOINT}?key={api_key}",
                json={
                    "model": f"models/{EMBED_MODEL}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_problem = f"network problem ({exc.__class__.__name__})"
            continue

        try:
            data = res.json()
        except ValueError:
            data = {}

        if res.status_code == 200:
            try:
                return data["embedding"]["values"]
            except (KeyError, TypeError) as exc:
                raise RetrievalError("Malformed embedding response.") from exc

        message = (data.get("error") or {}).get("message") or f"Embedding API error {res.status_code}"
        if res.status_code == 429 or res.status_code >= 500:
            last_problem = message  # busy or temporary: worth retrying
            continue
        raise RetrievalError(message)  # e.g. bad key: retrying won't help

    raise RetrievalError(last_problem)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_index(force_reload: bool = False):
    """Loads data/kb_embeddings.json (built by build_index.py). Returns
    None if it doesn't exist yet or can't be read, so the app degrades
    gracefully (no retrieval) instead of raising. The file's modified time
    is checked on every call, so rebuilding the index takes effect without
    restarting the server."""
    global _index_cache, _index_mtime
    if not os.path.exists(INDEX_PATH):
        return None
    try:
        mtime = os.path.getmtime(INDEX_PATH)
        if _index_cache is None or force_reload or mtime != _index_mtime:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                _index_cache = json.load(f)
            _index_mtime = mtime
    except (OSError, ValueError):
        return None
    return _index_cache


def retrieve(query_text: str, k: int = 4) -> list[dict]:
    """Returns up to k knowledge base entries most relevant to query_text,
    each with a similarity 'score'. Returns [] if the index hasn't been
    built yet, the query is empty, or anything goes wrong: retrieval
    failing should degrade to "no extra context", never break the
    conversation."""
    if not query_text or not query_text.strip():
        return []

    index = load_index()
    if not index:
        return []

    try:
        query_embedding = embed_text(query_text, task_type="RETRIEVAL_QUERY")
    except RetrievalError:
        return []

    try:
        scored = [{**entry, "score": _cosine(query_embedding, entry["embedding"])} for entry in index]
    except (KeyError, TypeError):
        return []  # malformed index file
    scored.sort(key=lambda e: e["score"], reverse=True)
    return scored[:k]