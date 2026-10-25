"""Server-only Gemini client. This module is imported only by app.py and
reads the API key from the environment — the key never travels to the
browser, which is the core Phase 1 fix vs the original client-side-key
version."""

import os

import requests

from prompts import build_system_instruction

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