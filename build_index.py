"""Builds the embeddings index used for retrieval. Run it whenever
knowledge_base.py changes:

    python build_index.py

Requires GEMINI_API_KEY in .env (uses the same key as the main app).

It is safe to re-run. Embeddings already computed for unchanged entries
are reused, from data/kb_cache.json and from the previous index, and
progress is saved after every entry. If the network drops half way, run
it again and it continues where it stopped instead of starting over. The
live index (data/kb_embeddings.json) is only replaced once every entry is
done, so the running app never sees a half-built index."""

import hashlib
import json
import os

from dotenv import load_dotenv

from knowledge_base import KNOWLEDGE_BASE
from retrieval import INDEX_PATH, RetrievalError, embed_text

load_dotenv()

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


def main():
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
                embedding = embed_text(
                    entry["text"], task_type="RETRIEVAL_DOCUMENT", timeout=40, retries=4
                )
            except RetrievalError as exc:
                print(f"\nStopped on '{entry['title']}': {exc}")
                print("Progress is saved. Run `python build_index.py` again to continue.")
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


if __name__ == "__main__":
    main()