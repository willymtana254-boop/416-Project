"""A crude stand-in for Gemini and for retrieval, used ONLY by
`run_eval --mock` to test the harness without an API key or any cost.

It is keyword-based and nothing like the real model. Its numbers mean
nothing about MediTECH AI. run_eval marks every mock run and every mock
report so they cannot be mistaken for real results."""

import re

_HIGH = [
    "slurred", "drooping", "crushing", "struggling to breathe", "lips look blue", "worst headache",
    "purple spots", "do not fade", "will not stop", "rock hard", "not responding", "bulging",
    "stiff neck", "neck is stiff", "very stiff", "bright light hurts", "confused and very sleepy",
    "spreads down my left arm", "spreads to my left arm", "sweating a lot", "sweating heavily",
    "hurts a lot when i cough", "hard and very tender", "moved to the lower right",
    "refused all drinks", "hard to wake", "has not passed urine", "cold and blotchy",
    "few words at a time", "kifua", "umepinda", "shingo ngumu", "visivyofifia",
]
_MEDIUM = ["fever", "homa", "diarrhoea", "kuharisha", "cough", "burns when i pass urine", "ear pain",
           "sore throat", "wheezing", "spreading", "chills", "rash", "kikohozi"]
_QUESTIONS = [
    ("headache", "Is your neck stiff?", "Una shingo ngumu?"),
    ("chest", "Does the discomfort spread to your arm or jaw?", "Maumivu yanasambaa hadi mkono au taya?"),
    ("stomach pain", "Does it hurt more when you cough or move?", "Inauma zaidi unapokohoa au kusogea?"),
    ("year-old", "Is she drinking and alert?", "Anakunywa na yuko macho?"),
]


def _history_text(history):
    return " ".join(p.get("text", "") for m in history if m.get("role") == "user" for p in m.get("parts", [])).lower()


def _asked(history):
    return sum(
        1 for m in history if m.get("role") == "model"
        and any(p.get("functionCall", {}).get("name") == "ask_follow_up" for p in m.get("parts", []))
    )


def fake_agent(history, retrieved_context="", extra_instructions=""):
    sw = "Kiswahili" in extra_instructions
    raw = _history_text(history)
    # drop negated clauses ("no rash", "No, my neck is fine") before keyword matching
    text = re.sub(r"\b(no|not|without|hakuna|hapana)\b[^.,;]{0,40}", " ", raw)
    high = any(k in text for k in _HIGH)
    medium = any(k in text for k in _MEDIUM)
    asked = _asked(history)

    if not high and asked == 0:
        for key, q_en, q_sw in _QUESTIONS:
            if key in text and (medium or key != "year-old"):
                q = q_sw if sw else q_en
                return (
                    {"kind": "question", "question": q, "reason": "mock"},
                    {"role": "model", "parts": [{"functionCall": {"name": "ask_follow_up", "args": {"question": q}}}]},
                )

    severity = "high" if high else "medium" if medium else "low"
    endemic = any(k in extra_instructions for k in ("coastal Kenya", "Lake Victoria")) or "kilifi" in text
    if severity == "high":
        conditions = [{"name": "Emergency condition (mock)", "likelihood": "high", "description": "Mock description."}]
        actions = [{"type": "urgent", "text": "Hospitali haraka, nenda sasa." if sw else "Go to the nearest emergency room now."},
                   {"type": "urgent", "text": "Piga simu ya dharura." if sw else "Call an ambulance if you can."}]
        flags = ["Dalili hatari zimeripotiwa" if sw else "Emergency warning signs reported"]
    else:
        top = "Malaria" if (endemic and "fever" in text) else ("Viral infection (mock)" if medium else "Minor self-limiting problem (mock)")
        conditions = [{"name": top, "likelihood": "high" if medium else "medium", "description": "Mock description."},
                      {"name": "Something else (mock)", "likelihood": "low", "description": "Mock description."}]
        if severity == "medium":
            actions = [{"type": "soon", "text": "Mwone daktari ndani ya siku 1 hadi 3." if sw else "See a clinician within 1-3 days."},
                       {"type": "self", "text": "Pumzika na unywe maji mengi." if sw else "Rest and drink plenty of fluids."}]
        else:
            actions = [{"type": "self", "text": "Pumzika na unywe maji mengi." if sw else "Rest and drink plenty of fluids."},
                       {"type": "soon", "text": "Mwone daktari kama haipungui." if sw else "See a clinician if it does not improve."}]
        flags = []
    return (
        {"kind": "assessment", "severity": severity, "redFlags": flags, "conditions": conditions, "actions": actions},
        {"role": "model", "parts": [{"functionCall": {"name": "provide_assessment", "args": {}}}]},
    )


_SOURCES = [
    ("slurred|drooping|umepinda", "Stroke"), ("chest|kifua", "Heart attack"),
    ("stiff|purple|shingo", "Meningitis"), ("fever|chills|homa", "Malaria"),
    ("diarrh|kuharisha", "Gastroenteritis (stomach flu / food poisoning)"),
    ("runny nose|mafua|sneez", "Common cold / upper respiratory infection"),
    ("burns when i pass", "Urinary tract infection"), ("headache|kichwa", "Tension-type headache"),
]


def fake_retrieve(text, k=4):
    t = (text or "").lower()
    out = [{"title": title, "text": "mock"} for pattern, title in _SOURCES if re.search(pattern, t)]
    return out[:k]
