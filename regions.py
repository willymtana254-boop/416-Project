"""Language and regional context for Kenya localization (Phase 3).

Two things live here:
  1. LANGUAGE_RULES: how the agent should write its replies (English or
     Kiswahili) while keeping the tool schema (enum values, field names)
     in English so the app's JSON handling never breaks.
  2. REGION_NOTES: short, hedged notes about which conditions are
     generally more or less likely in each broad part of Kenya. These
     adjust likelihood ordering and which follow-up question to ask. They
     must never lower severity or override an emergency red flag, and the
     REGION_RULE below tells the model exactly that.

Edit REGION_NOTES to refine the content. Treat it as reference text for
the report: it should be checked against Ministry of Health guidance
before you cite it as clinical fact."""

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
