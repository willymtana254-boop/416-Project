import os, sys, tempfile
tmp = tempfile.mkdtemp()
os.environ.update(MEDITECH_DB=os.path.join(tmp, "e2e.db"), SECRET_KEY="e2e-secret-key-e2e-secret-key-0123456789")
sys.path.insert(0, "/home/claude/meditech-ai-py"); os.chdir("/home/claude/meditech-ai-py")
import app as appmod, auth, db, create_clinician
from facilities import FacilitiesError

# The only fakes: the Gemini call, retrieval and the map lookup. Everything else is the real app.
def fake_agent(history, retrieved_context="", extra_instructions=""):
    users = [m for m in history if m.get("role") == "user"]
    last = " ".join(p.get("text", "") for p in users[-1]["parts"]).lower()
    asked = sum(1 for m in history if m.get("role") == "model" and any(p.get("functionCall", {}).get("name") == "ask_follow_up" for p in m.get("parts", [])))
    if "fever" in last and asked == 0:
        q = "How long have you had the fever?"
        return ({"kind": "question", "question": q, "reason": "Duration matters"},
                {"role": "model", "parts": [{"functionCall": {"name": "ask_follow_up", "args": {"question": q}}}]})
    sev = "high" if "chest" in last else "medium"
    return ({"kind": "assessment", "severity": sev, "redFlags": ["Chest pain"] if sev == "high" else [],
             "conditions": [{"name": "Test condition <b>x</b>", "likelihood": "medium", "description": "d"}],
             "actions": [{"type": "urgent" if sev == "high" else "soon", "text": "Act now" if sev == "high" else "See a clinician"}]},
            {"role": "model", "parts": [{"functionCall": {"name": "provide_assessment", "args": {}}}]})
appmod.call_gemini_agent = fake_agent
appmod.retrieve = lambda text, k=4: [{"title": "Malaria", "text": "x"}]
FAC = [
    {"name": "Eldoret Referral Hospital", "kind": "hospital", "distanceKm": 0.6, "lat": 0.5200, "lon": 35.2700, "phone": "+254 53 203 3471", "emergency": True, "openingHours": "24/7", "directionsUrl": "https://www.google.com/maps/dir/?api=1&destination=0.52,35.27"},
    {"name": "Corner Pharmacy", "kind": "pharmacy", "distanceKm": 0.1, "lat": 0.5150, "lon": 35.2690, "phone": "", "emergency": False, "openingHours": "", "directionsUrl": "https://www.google.com/maps/dir/?api=1&destination=0.515,35.269"},
    {"name": "Far Clinic", "kind": "clinic", "distanceKm": 2.0, "lat": 0.5300, "lon": 35.2800, "phone": "", "emergency": False, "openingHours": "", "directionsUrl": "https://www.google.com/maps/dir/?api=1&destination=0.53,35.28"},
]
def fake_find(lat, lon):
    if lat < -80: raise FacilitiesError("Map data service is down")      # -> HTTP 502, like a real Overpass outage
    if lat > 80: return {"facilities": [], "radiusKm": 40.0}              # nothing found
    return {"facilities": FAC, "radiusKm": 5.0}
appmod.find_facilities = fake_find
c = db.connect(appmod.app.config["DATABASE"]); create_clinician.create_or_promote(c, "dr@clinic.ke", "Dr Otieno", "clinician-pass-1"); c.close()
appmod.app.run(port=5055, debug=False, use_reloader=False, threaded=True)
