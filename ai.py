"""The AI side of MediTECH AI: language rules, the system prompt, retrieval over the
reference notes, and the Gemini client.  app.py uses three things from here:
retrieve(), locale_instructions() and call_gemini_agent()."""

import json
import math
import os
import time

import requests


# ==========================================================================
# 1. LANGUAGE AND REGION  (was regions.py)
# ==========================================================================
# Language and regional context for Kenya localization (Phase 3).
#
# Two things live here:
#   1. LANGUAGE_RULES: how the agent should write its replies (English or
#      Kiswahili) while keeping the tool schema (enum values, field names)
#      in English so the app's JSON handling never breaks.
#   2. REGION_NOTES: short, hedged notes about which conditions are
#      generally more or less likely in each broad part of Kenya. These
#      adjust likelihood ordering and which follow-up question to ask. They
#      must never lower severity or override an emergency red flag, and the
#      REGION_RULE below tells the model exactly that.
#
# Edit REGION_NOTES to refine the content. Treat it as reference text for
# the report: it should be checked against Ministry of Health guidance
# before you cite it as clinical fact.

LANGUAGES = {"en": "English", "sw": "Kiswahili"}
DEFAULT_LANGUAGE = "en"

LANGUAGE_RULES = {
    "en": "Respond to the patient in clear, simple English.",
    "sw": (
        "Respond to the patient in clear, simple Kiswahili that a general "
        "audience in Kenya can understand, even if the patient writes in "
        "English or mixes languages. This applies to every free-text field: "
        "the follow-up question and its reason, condition names and "
        "descriptions, red flags, and action text. Where a condition has a "
        "common medical name that people use as is (for example Malaria or "
        "Typhoid), keep that name and add a short Kiswahili explanation. "
        "Tool names, JSON field names and enum values (low, medium, high, "
        "urgent, soon, self) must stay exactly as defined, in English."
    ),
}

REGION_NOTES = {
    "coast": (
        "The patient is in coastal Kenya (for example Mombasa, Kilifi, "
        "Kwale, Lamu, Tana River, Taita-Taveta). Malaria transmission is "
        "generally higher in coastal and lowland areas. Dengue and "
        "chikungunya occur along the coast. Typhoid and diarrhoeal illness "
        "are more likely where water and sanitation are poor."
    ),
    "lake": (
        "The patient is in the Lake Victoria / western Kenya region (for "
        "example Kisumu, Siaya, Homa Bay, Migori, Busia, Kakamega, "
        "Bungoma). Malaria transmission is generally high here. "
        "Schistosomiasis (bilharzia) is possible after contact with lake or "
        "stagnant fresh water."
    ),
    "rift": (
        "The patient is in the Rift Valley or western highlands (for "
        "example Nakuru, Uasin Gishu, Kericho, Nandi, Trans Nzoia, Baringo, "
        "Narok, Kajiado). Malaria risk is generally lower at high altitude "
        "but can occur at lower altitudes, in valley areas and during "
        "epidemic periods. When fever is present, ask about recent travel "
        "to lowland or coastal areas."
    ),
    "central": (
        "The patient is in Nairobi or the central highlands (for example "
        "Nairobi, Kiambu, Nyeri, Murang'a, Kirinyaga, Embu, Meru). Malaria "
        "risk is generally low here, so unless there has been recent travel "
        "to a malaria-endemic area, weigh other causes of fever first "
        "(respiratory infections, typhoid, urinary tract infection and "
        "others)."
    ),
    "north": (
        "The patient is in the northern or eastern dry areas of Kenya (for "
        "example Turkana, Marsabit, Garissa, Wajir, Mandera, Isiolo, "
        "Kitui). Malaria is often seasonal and linked to the rains. "
        "Visceral leishmaniasis (kala-azar) occurs in some of these areas, "
        "and waterborne illness is a concern where clean water is scarce. "
        "Health facilities may be far away, so recommend seeking care "
        "earlier rather than later."
    ),
}

REGION_RULE = (
    "Use this regional context only to adjust how likely each condition "
    "is, to choose a follow-up question (such as recent travel), and to "
    "word condition descriptions. Never use it to lower severity or to "
    "override an emergency red flag."
)


def normalise_language(value) -> str:
    """Returns a supported language code, falling back to English."""
    return value if isinstance(value, str) and value in LANGUAGES else DEFAULT_LANGUAGE


def normalise_region(value) -> str:
    """Returns a known region key, or "" if none/unknown. Unknown values
    are ignored rather than rejected: region is an optional hint."""
    return value if isinstance(value, str) and value in REGION_NOTES else ""


def locale_instructions(language, region) -> str:
    """Builds the locale block appended to the system instruction."""
    lang = normalise_language(language)
    parts = ["Language: " + LANGUAGE_RULES[lang]]
    reg = normalise_region(region)
    if reg:
        parts.append("Regional context: " + REGION_NOTES[reg] + " " + REGION_RULE)
    return "\n\n".join(parts)


# ==========================================================================
# 2. SYSTEM PROMPT  (was prompts.py)
# ==========================================================================

# Centralising the system instruction here makes it easy to version,
# tune, and (in Phase 6) evaluate against a fixed case set.

MAX_FOLLOW_UPS = 3

SYSTEM_INSTRUCTION = f"""You are the triage reasoning engine for MediTECH AI, a symptom-checking
assistant. You are NOT a doctor and never claim to be one. Your job is to
reason like a careful intake nurse: gather just enough information to give
a safe, useful triage recommendation, then hand off to a human clinician.

You must ALWAYS respond by calling exactly one of the two available tools,
never respond with plain text.

1. Call "ask_follow_up" when you need more information before you can give
   a safe assessment. You may ask at most {MAX_FOLLOW_UPS} follow-up
   questions in a single conversation. Prioritise questions that would
   change the severity rating or the recommended action, not questions that
   only narrow curiosity.

   Question format rules (hard constraints):
   - Ask about ONE symptom or ONE fact per question. Never bundle several
     symptoms into a single yes/no question. For example, do not ask "Do you
     have a stiff neck, severe headache, confusion, or a rash?". Ask only
     "Do you have a stiff neck?" or "How long have you had the fever?".
   - If several red-flag symptoms need checking, pick the single most
     important or most likely one first. You can ask the next one in a later
     turn if follow-ups remain.
   - Prefer questions the patient can answer with a short, unambiguous
     reply (yes/no, a number, a duration).

2. Call "provide_assessment" once you have enough information, OR once you
   have already asked {MAX_FOLLOW_UPS} follow-up questions (at that point
   you must give your best assessment with the information available,
   noting uncertainty in the condition descriptions rather than asking
   again).

Interpreting the patient's answers (hard constraints):
- Only treat a symptom as present if the patient has actually said so in
  their own words or has clearly answered yes to a question about that one
  symptom. Never assume symptoms the patient did not report.
- If the patient gave a bare answer such as "yes" or "no" to a question that
  mentioned more than one symptom, you do not know which symptom they meant.
  Do not list each of those symptoms as confirmed. In "redFlags", write what
  is actually known, for example "Answered yes to a question about stiff
  neck, severe headache, confusion or rash (specific symptom not
  confirmed)".
- Safety still comes first: if an ambiguous "yes" could mean an emergency
  red flag, keep severity "high" and tell the patient to seek urgent care,
  but word the red flags honestly as described above.

Safety rules (treat these as hard constraints, not suggestions):
- If the symptoms described include any recognised emergency red flag,
  for example: crushing/severe chest pain, chest pain with shortness of
  breath, sudden severe headache ("worst of my life"), one-sided weakness
  or facial drooping or slurred speech (stroke signs), difficulty
  breathing at rest, severe uncontrolled bleeding, signs of anaphylaxis
  (swelling of face/throat, difficulty breathing after a known trigger),
  confusion or loss of consciousness, or a child with a high fever and a
  stiff neck or rash that doesn't fade under pressure, you must set
  severity to "high", list the specific red flag(s) in "redFlags", and
  make the first action an "urgent" one telling them to seek emergency
  care immediately. Do not spend a follow-up question clarifying an
  obvious emergency; assess immediately.
- Never state a condition as certain. Use the likelihood field honestly.
- Always include at least one action, and always include clear guidance
  to see a qualified healthcare professional for diagnosis. You are
  informational support only, not a replacement for care.

Rules for recommended actions (hard constraints):
- Never give medication advice of any kind. Do not recommend, name, dose,
  or advise taking OR avoiding any medicine, painkiller, antibiotic,
  antimalarial or supplement. Do not write things like "do not take any
  medication" or "take paracetamol". Medication decisions belong to a
  clinician who has examined the patient. If it is relevant, you may say
  "tell the clinician about any medicines you have already taken".
- Action types must match severity:
    high severity   -> every action is type "urgent" (emergency care, call
                       an ambulance, do not travel alone, stay with someone).
    medium severity -> a "soon" action to see a clinician within 1-3 days,
                       plus optional "self" actions (rest, fluids, monitor
                       symptoms and what would make them go to urgent care).
    low severity    -> "self" actions (rest, fluids, monitoring), plus one
                       "soon" action saying when to see a clinician if it
                       does not improve.
  Never mix in a "soon" or "self" action that contradicts an urgent
  recommendation.
- Keep actions practical and non-medicinal: where to go, how fast, what to
  monitor, what to tell the clinician, and general comfort measures such as
  rest and drinking fluids when appropriate for the severity.
- Keep condition descriptions under ~18 words and action text under ~22
  words. This is a mobile-first interface.
- If relevant, you may note when a symptom pattern is common in coastal
  Kenya (e.g. malaria, typhoid) alongside other differentials, but do not
  let regional prevalence override an otherwise indicated emergency
  pathway."""


def build_system_instruction(retrieved_context: str = "", extra_instructions: str = "") -> str:
    """Builds the full system instruction for one call: the base prompt,
    then the locale block (language and region, from regions.py), then any
    retrieved reference material. Kept as a function rather than constants
    so each block can be tuned independently."""
    text = SYSTEM_INSTRUCTION
    if extra_instructions:
        text += "\n\nLocale settings for this conversation:\n" + extra_instructions
    if retrieved_context:
        text += (
            "\n\nRelevant reference material retrieved for this conversation. "
            "Ground your condition descriptions and likelihoods in this "
            "where it applies. It is not exhaustive: do not ignore symptoms "
            "that don't match any entry here, and do not treat an entry's "
            "presence as proof the patient has that condition.\n\n"
            + retrieved_context
        )
    return text


# ==========================================================================
# 3. RETRIEVAL OVER THE REFERENCE NOTES (RAG)  (was retrieval.py)
# ==========================================================================
# Embedding + cosine-similarity retrieval over the local knowledge base.
#
# Kept deliberately simple (plain Python, no vector DB dependency) since the
# corpus is small (~20 entries). Swap in Chroma or pgvector later if the
# knowledge base grows significantly: the retrieve() function's signature
# is the only thing other modules depend on, so that swap stays contained
# to this file.
#
# Failure policy: embed_text() turns every network or API problem into a
# RetrievalError, and retrieve() turns a RetrievalError into "no extra
# context". A flaky connection must never break a patient's conversation.

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


# ==========================================================================
# 4. GEMINI CLIENT  (was gemini_client.py)
# ==========================================================================
# Server-only Gemini client. This module is imported only by app.py and
# reads the API key from the environment — the key never travels to the
# browser, which is the core Phase 1 fix vs the original client-side-key
# version.

MODEL = "gemini-3-flash-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "ask_follow_up",
                "description": (
                    "Ask the patient one clarifying question when more information "
                    "is needed before a safe assessment can be made."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {
                            "type": "STRING",
                            "description": "A single, clear follow-up question for the patient.",
                        },
                        "reason": {
                            "type": "STRING",
                            "description": "Briefly, why this question matters for triage.",
                        },
                    },
                    "required": ["question"],
                },
            },
            {
                "name": "provide_assessment",
                "description": (
                    "Provide the final structured triage assessment once enough "
                    "information has been gathered."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "severity": {"type": "STRING", "enum": ["low", "medium", "high"]},
                        "redFlags": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "Specific emergency red flags identified, if any. Empty array if none.",
                        },
                        "conditions": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "name": {"type": "STRING"},
                                    "likelihood": {
                                        "type": "STRING",
                                        "enum": ["high", "medium", "low"],
                                    },
                                    "description": {"type": "STRING"},
                                },
                                "required": ["name", "likelihood", "description"],
                            },
                        },
                        "actions": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "type": {
                                        "type": "STRING",
                                        "enum": ["urgent", "soon", "self"],
                                    },
                                    "text": {"type": "STRING"},
                                },
                                "required": ["type", "text"],
                            },
                        },
                    },
                    "required": ["severity", "redFlags", "conditions", "actions"],
                },
            },
        ]
    }
]


class GeminiAgentError(Exception):
    """Raised for anything that stops us getting a usable tool call back."""


def call_gemini_agent(
    history: list[dict], retrieved_context: str = "", extra_instructions: str = ""
) -> tuple[dict, dict]:
    """Send the conversation so far to Gemini and return (turn, model_message).

    `retrieved_context` is pre-formatted RAG context (see app.py's
    build_context_block), appended to the system instruction for this call
    only — it's never stored in history, so it's rebuilt fresh each turn
    from whatever's relevant to the conversation at that point.

    `extra_instructions` is the locale block from regions.py (reply
    language and regional context), also rebuilt per call.

    `turn` is a plain dict shaped like either:
      {"kind": "question", "question": ..., "reason": ...}
      {"kind": "assessment", "severity": ..., "redFlags": [...], "conditions": [...], "actions": [...]}

    `model_message` is the raw Gemini-format turn to append to history so
    the next request has the full conversation context.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiAgentError("GEMINI_API_KEY is not set. Add it to your .env file.")

    payload = {
        "systemInstruction": {"parts": [{"text": build_system_instruction(retrieved_context, extra_instructions)}]},
        "contents": history,
        "tools": TOOLS,
        "toolConfig": {"functionCallingConfig": {"mode": "ANY"}},
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1536},
    }

    try:
        res = requests.post(f"{ENDPOINT}?key={api_key}", json=payload, timeout=30)
    except requests.RequestException as exc:
        raise GeminiAgentError(f"Could not reach Gemini: {exc}") from exc

    try:
        data = res.json()
    except ValueError as exc:
        raise GeminiAgentError("Gemini returned a non-JSON response.") from exc

    if res.status_code != 200:
        message = (data.get("error") or {}).get("message", f"Gemini API error {res.status_code}")
        raise GeminiAgentError(message)

    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiAgentError("Empty or malformed response from Gemini.") from exc

    call_part = next((p for p in parts if "functionCall" in p), None)
    if not call_part:
        raise GeminiAgentError(
            "Model did not call a tool as required. This usually means the prompt needs adjusting."
        )

    name = call_part["functionCall"]["name"]
    args = call_part["functionCall"].get("args", {}) or {}

    model_message = {"role": "model", "parts": [{"functionCall": {"name": name, "args": args}}]}

    if name == "ask_follow_up":
        turn = {
            "kind": "question",
            "question": args.get("question", ""),
            "reason": args.get("reason"),
        }
    elif name == "provide_assessment":
        turn = {
            "kind": "assessment",
            "severity": args.get("severity", "medium"),
            "redFlags": args.get("redFlags", []),
            "conditions": args.get("conditions", []),
            "actions": args.get("actions", []),
        }
    else:
        raise GeminiAgentError(f"Unexpected tool call: {name}")

    return turn, model_message
