"""Reference material for RAG grounding. Each entry is a short, original
summary of a condition's typical presentation, written for MediTECH AI —
not copied from any single source. The point is to give the model
something concrete to ground its condition descriptions and likelihoods
in, rather than relying purely on its own recall, and to give you control
over exactly what reference content the assessments are grounded against.

Phase 3 can extend or replace this with Kenya MOH / WHO-aligned guidance
documents; this gives Phase 2 a working, swappable knowledge base.

Emergency conditions (meningitis, sepsis, stroke, heart attack) are included
so the highest-stakes red-flag cases have reference text to ground on.

Run build_index.py after editing this file to rebuild the embeddings."""

KNOWLEDGE_BASE = [
    {
        "id": "malaria",
        "title": "Malaria",
        "text": (
            "Malaria typically presents with cyclical fever, chills, sweating, "
            "headache, and muscle aches, often with nausea and fatigue. Fever "
            "patterns may spike every 48-72 hours depending on species. Common "
            "and often underdiagnosed in coastal and western Kenya. Confirmed "
            "diagnosis requires a blood test (RDT or microscopy) - any fever of "
            "unknown origin in a malaria-endemic area should be tested promptly, "
            "and untreated malaria can progress to severe illness within days, "
            "especially in children and pregnant women."
        ),
    },
    {
        "id": "typhoid",
        "title": "Typhoid fever",
        "text": (
            "Typhoid fever develops gradually over several days with a "
            "step-wise rising fever, headache, abdominal pain, and general "
            "malaise; constipation or diarrhoea may both occur, and a rash of "
            "flat pink spots is sometimes seen. Spread via contaminated food "
            "or water, common where sanitation is poor. Needs medical "
            "treatment guided by a blood culture - untreated cases risk "
            "intestinal bleeding or perforation."
        ),
    },
    {
        "id": "common-cold",
        "title": "Common cold / upper respiratory infection",
        "text": (
            "Gradual onset of runny or blocked nose, sneezing, mild sore "
            "throat, and cough, usually without high fever. Self-limiting, "
            "typically resolving within 7-10 days with rest and fluids. "
            "Should not cause breathing difficulty or high fever - if either "
            "appears, consider a different or secondary diagnosis."
        ),
    },
    {
        "id": "influenza",
        "title": "Influenza (flu)",
        "text": (
            "Sudden onset of high fever, chills, body aches, headache, "
            "fatigue, and dry cough, often more severe than a common cold. "
            "Usually resolves in 5-7 days with rest and fluids. Those with "
            "chronic conditions, young children, the elderly, or pregnant "
            "women are at higher risk of complications such as pneumonia."
        ),
    },
    {
        "id": "migraine",
        "title": "Migraine",
        "text": (
            "Typically a throbbing, one-sided headache, often with nausea and "
            "sensitivity to light or sound, sometimes preceded by visual "
            "disturbances (aura). Episodes can last hours to days. A headache "
            "described as 'the worst of my life' with sudden onset, or with "
            "neurological symptoms like weakness or confusion, is NOT typical "
            "migraine and should be treated as a possible emergency instead."
        ),
    },
    {
        "id": "tension-headache",
        "title": "Tension-type headache",
        "text": (
            "A dull, pressing, band-like pain around the head, often linked "
            "to stress, poor sleep, or prolonged screen use. Usually mild to "
            "moderate and responds to rest, hydration, and over-the-counter "
            "pain relief. Not typically accompanied by nausea, visual "
            "disturbance, or neurological symptoms."
        ),
    },
    {
        "id": "gastroenteritis",
        "title": "Gastroenteritis (stomach flu / food poisoning)",
        "text": (
            "Nausea, vomiting, watery diarrhoea, and abdominal cramps, "
            "usually starting within hours to a couple of days of eating "
            "contaminated food or water. Most cases resolve within a few days "
            "with fluids and rest. Risk of dehydration is the main concern, "
            "especially in children - persistent vomiting, inability to keep "
            "fluids down, or blood in stool warrants urgent review."
        ),
    },
    {
        "id": "uti",
        "title": "Urinary tract infection",
        "text": (
            "Burning on urination, frequent urge to urinate, cloudy or "
            "strong-smelling urine, and lower abdominal discomfort. If fever, "
            "chills, or flank/back pain develop, the infection may have "
            "spread to the kidneys and needs urgent medical attention rather "
            "than routine care."
        ),
    },
    {
        "id": "pneumonia",
        "title": "Pneumonia",
        "text": (
            "Cough (often productive), fever, chills, and chest pain that "
            "worsens with breathing or coughing, sometimes with shortness of "
            "breath. More serious than a simple chest cold - breathing "
            "difficulty, bluish lips, confusion, or high fever that doesn't "
            "improve are signs of a severe case needing urgent care, "
            "particularly in young children and older adults."
        ),
    },
    {
        "id": "asthma-exacerbation",
        "title": "Asthma exacerbation",
        "text": (
            "Wheezing, chest tightness, shortness of breath, and cough, "
            "often triggered by allergens, exercise, cold air, or infection. "
            "Mild episodes can often be managed with a reliever inhaler if "
            "the person has one; inability to speak in full sentences, "
            "bluish lips, or no improvement with a reliever inhaler is an "
            "emergency."
        ),
    },
    {
        "id": "appendicitis",
        "title": "Appendicitis",
        "text": (
            "Pain often starting around the navel and migrating to the lower "
            "right abdomen, worsening over hours, with nausea, loss of "
            "appetite, and low-grade fever. Pain that worsens with movement "
            "or coughing, or a rigid/very tender abdomen, is a surgical "
            "emergency - delay risks rupture."
        ),
    },
    {
        "id": "allergic-reaction",
        "title": "Allergic reaction",
        "text": (
            "Mild reactions cause localized itching, hives, or rash. "
            "Reactions involving swelling of the face, lips or throat, "
            "difficulty breathing, or dizziness after exposure to a known "
            "trigger (food, insect sting, medication) suggest anaphylaxis - "
            "an emergency requiring immediate care."
        ),
    },
    {
        "id": "dehydration",
        "title": "Dehydration",
        "text": (
            "Thirst, dry mouth, dark urine, fatigue, and dizziness, "
            "especially on standing. Can result from inadequate fluid "
            "intake, heat, vomiting, or diarrhoea. Severe dehydration "
            "(confusion, very little or no urination, rapid heartbeat, "
            "sunken eyes in children) needs urgent rehydration, sometimes "
            "intravenously."
        ),
    },
    {
        "id": "chickenpox",
        "title": "Chickenpox",
        "text": (
            "An itchy rash that progresses from red spots to fluid-filled "
            "blisters to crusted scabs over several days, often with mild "
            "fever. Highly contagious. Usually mild in children; adults and "
            "immunocompromised individuals are at higher risk of "
            "complications and should seek medical advice."
        ),
    },
    {
        "id": "measles",
        "title": "Measles",
        "text": (
            "Starts with fever, cough, runny nose, and red eyes, followed by "
            "a red blotchy rash spreading from the face downward a few days "
            "later. Highly contagious, especially dangerous in unvaccinated "
            "children. Watch for difficulty breathing, persistent high "
            "fever, or signs of ear/lung complications."
        ),
    },
    {
        "id": "dengue",
        "title": "Dengue fever",
        "text": (
            "High fever with severe headache, pain behind the eyes, joint "
            "and muscle pain, and sometimes a rash, transmitted by mosquito "
            "bite. Most cases resolve with rest and fluids, but warning signs "
            "- severe abdominal pain, persistent vomiting, bleeding gums, or "
            "lethargy - signal possible severe dengue and need urgent care."
        ),
    },
    {
        "id": "heat-exhaustion",
        "title": "Heat exhaustion",
        "text": (
            "Heavy sweating, weakness, dizziness, nausea, and headache after "
            "exposure to heat or exertion. Responds to moving to a cool "
            "place, rest, and fluids. If sweating stops, confusion develops, "
            "or body temperature feels very high, this may be heat stroke - "
            "an emergency."
        ),
    },
    {
        "id": "anxiety-chest-tightness",
        "title": "Anxiety-related chest tightness",
        "text": (
            "Chest tightness, rapid heartbeat, shortness of breath, and "
            "tingling can occur with acute anxiety or panic. However, chest "
            "pain should never be assumed to be 'just anxiety' on first "
            "presentation, especially with risk factors for heart disease - "
            "cardiac causes should be ruled out first, particularly if pain "
            "radiates to the arm/jaw or is accompanied by sweating."
        ),
    },
    {
        "id": "meningitis",
        "title": "Meningitis",
        "text": (
            "Fever with severe headache, stiff neck, sensitivity to bright "
            "light, nausea or vomiting, and often confusion or unusual "
            "drowsiness. A rash that does not fade when a clear glass is "
            "pressed against it suggests meningococcal disease. In babies, "
            "look for poor feeding, constant crying or irritability, a "
            "bulging soft spot, or floppiness. It can worsen within hours, "
            "so any suspected case needs emergency hospital care "
            "immediately rather than watchful waiting."
        ),
    },
    {
        "id": "sepsis",
        "title": "Sepsis",
        "text": (
            "A dangerous whole-body reaction to infection. Warning signs "
            "include fever or a very low body temperature, fast heartbeat, "
            "fast breathing, confusion or unusual drowsiness, very little "
            "urine, cold, clammy or blotchy skin, and feeling far sicker "
            "than the apparent illness would explain. It can follow a "
            "chest, urinary, abdominal, skin or wound infection, or "
            "severe malaria. Babies, older adults, pregnant or recently "
            "delivered women, and people with HIV or diabetes are at "
            "higher risk. It is an emergency needing immediate hospital "
            "care."
        ),
    },
    {
        "id": "stroke",
        "title": "Stroke",
        "text": (
            "Sudden drooping of one side of the face, weakness or numbness "
            "in one arm or leg, slurred or confused speech, sudden loss of "
            "vision, loss of balance, or a sudden severe headache. The "
            "FAST check covers Face, Arms, Speech and Time. Treatment is "
            "time-limited, so note when symptoms began and go to hospital "
            "at once. Symptoms that settle within minutes (a mini-stroke) "
            "still need same-day emergency assessment. High blood pressure "
            "is the biggest risk factor."
        ),
    },
    {
        "id": "heart-attack",
        "title": "Heart attack",
        "text": (
            "Pressure, tightness, heaviness or squeezing pain in the "
            "centre of the chest lasting more than a few minutes or "
            "coming and going, which may spread to the arm, shoulder, "
            "neck, jaw or back. Often with shortness of breath, cold "
            "sweat, nausea, light-headedness or unusual tiredness. Women, "
            "older adults and people with diabetes may have milder or "
            "atypical symptoms such as breathlessness or upper abdominal "
            "discomfort. Treat as an emergency: call for emergency help "
            "and do not drive yourself."
        ),
    },
]