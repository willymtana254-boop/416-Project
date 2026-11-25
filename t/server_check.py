import json, os, re, sys, tempfile
from pathlib import Path
os.environ["MEDITECH_DB"] = os.path.join(tempfile.mkdtemp(), "t.db"); os.environ["SECRET_KEY"] = "x" * 40; os.environ.pop("GEMINI_API_KEY", None)
ROOT = Path("/home/claude/meditech-ai-py"); sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
import app as appmod, pwa
c = appmod.app.test_client(); n = 0
def ok(cond, m):
    global n
    if not cond: print("FAIL:", m); sys.exit(1)
    n += 1
html = c.get("/").data.decode()
for el in ['id="facNote"', 'id="facForget"', 'id="netBanner"', 'id="emergNav"', 'id="emergencyCard"', 'id="updateBanner"', 'id="installBtn"', 'js/pwa.js']:
    ok(el in html, f"page has {el}")
sw = c.get("/sw.js").data.decode(); urls = json.loads(re.search(r"const PRECACHE = (\[.*?\]);", sw, re.S).group(1))
ok(len(urls) == 16 and all(c.get(u).status_code == 200 for u in urls), "all 16 shell files are served")
ok(c.get("/manifest.webmanifest").get_json(force=True)["shortcuts"][0]["url"] == "/?view=emergency", "manifest shortcut intact")
csp = c.get("/").headers["Content-Security-Policy"]; ok("font-src 'self'" in csp and "googleapis" not in csp, "CSP unchanged")
ok(not re.search(r"googleapis|gstatic", html + (ROOT / "static/css/styles.css").read_text(encoding="utf-8")), "still nothing loaded from Google")
ok(c.post("/api/facilities", json={}).status_code == 400 and c.post("/api/facilities", json={"lat": 0.5, "lon": 35}).status_code in (200, 502), "facilities endpoint unchanged")
print(f"server checks OK ({n})")
