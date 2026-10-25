"""A scripted patient. It answers the assistant's follow-up questions from
the case's own rules, so every run of a case sees the same answers and no
extra model calls are needed.

Order of answers: the case's `replies` (first regex match wins) -> generic
answers (duration, temperature, age, pregnancy) -> the case's default reply
("No, I don't think so." unless the case sets `default_reply`).

`revealed` is True when the answer given disclosed a hidden red flag, which
lets the report measure whether the assistant asked the right question."""

import re

GENERIC = {
    "en": [
        (r"how long|since when|when did|when was|for how many|how many (days|hours|weeks)", "duration", "About two days."),
        (r"temperature|how high|degrees|thermometer|measured", None, "I have not measured it, but it feels high."),
        (r"how old|your age|what age", "age", "I am 28 years old."),
        (r"pregnan", None, "No, I am not pregnant."),
    ],
    "sw": [
        (r"muda gani|tangu lini|siku ngapi|lini ilianza|ilianza lini", "duration", "Takriban siku mbili."),
        (r"joto|kipimo|nyuzi", None, "Sijapima, lakini ninahisi joto kali."),
        (r"umri|miaka mingapi", "age", "Nina umri wa miaka 28."),
        (r"mjamzito|mimba", None, "Hapana, si mjamzito."),
    ],
}
DEFAULT_REPLY = {"en": "No, I don't think so.", "sw": "Hapana, sidhani."}


class Patient:
    def __init__(self, case: dict):
        self.case = case
        self.lang = case.get("language", "en")
        self.fired = []          # indexes of case rules that matched
        self.revealed = False    # did any answer disclose a hidden red flag?

    def reply(self, question: str) -> str:
        q = (question or "").lower()
        for i, rule in enumerate(self.case.get("replies", [])):
            if re.search(rule["when"], q, re.I):
                self.fired.append(i)
                if rule.get("reveal"):
                    self.revealed = True
                return rule["say"]
        for pattern, field, text in GENERIC[self.lang]:
            if re.search(pattern, q, re.I):
                return self.case.get(field, text) if field else text
        return self.case.get("default_reply") or DEFAULT_REPLY[self.lang]
