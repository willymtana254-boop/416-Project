import logging
import math
import re
import time

import requests

log = logging.getLogger(__name__)

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "MediTECH-AI/0.3 (fourth-year university project)"

# Search progressively wider: rural areas may have nothing within 5 km.
RADII_M = [5000, 15000, 40000]
MIN_RESULTS = 5
MAX_RESULTS = 40
CACHE_TTL_SECONDS = 600

# The public Overpass servers are shared and are often busy (HTTP 429/504).
# Try every mirror, pause briefly, then do one more round, but give up after
# TIME_BUDGET_S so the patient is not left waiting on a spinner.
ROUNDS = 2
ROUND_PAUSE_S = 1.5
REQUEST_TIMEOUT_S = 25
TIME_BUDGET_S = 90

_cache: dict = {}


class FacilitiesError(Exception):
    """Raised when facilities can't be fetched. The message is safe to show."""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _classify(tags: dict):
    amenity = tags.get("amenity")
    health = tags.get("healthcare")
    if amenity == "hospital" or health == "hospital":
        return "hospital"
    if amenity == "pharmacy" or health == "pharmacy":
        return "pharmacy"
    if amenity in ("clinic", "doctors") or health in ("clinic", "doctor", "centre"):
        return "clinic"
    return None


def _clean_phone(tags: dict) -> str:
    raw = tags.get("phone") or tags.get("contact:phone") or ""
    first = str(raw).split(";")[0]
    return re.sub(r"[^\d+\-\s()]", "", first).strip()[:30]


def parse_elements(elements: list, lat: float, lon: float) -> list:
    """Turns raw Overpass elements into a distance-sorted list of
    facilities, dropping unnamed duplicates of the same place."""
    found = []
    for el in elements:
        tags = el.get("tags") or {}
        kind = _classify(tags)
        if not kind:
            continue
        if "lat" in el and "lon" in el:
            f_lat, f_lon = el["lat"], el["lon"]
        else:
            center = el.get("center") or {}
            if "lat" not in center or "lon" not in center:
                continue
            f_lat, f_lon = center["lat"], center["lon"]

        name = (tags.get("name") or "").strip()
        found.append(
            {
                "name": name[:80],
                "kind": kind,
                "distanceKm": round(haversine_km(lat, lon, f_lat, f_lon), 1),
                "_dist": haversine_km(lat, lon, f_lat, f_lon),
                "lat": f_lat,
                "lon": f_lon,
                "phone": _clean_phone(tags),
                "emergency": tags.get("emergency") == "yes",
                "openingHours": str(tags.get("opening_hours") or "")[:80],
                "directionsUrl": (
                    f"https://www.google.com/maps/dir/?api=1&destination={f_lat},{f_lon}"
                ),
            }
        )

    found.sort(key=lambda f: f["_dist"])

    # OSM often has both a node and a building outline for one hospital.
    # Drop a later entry with the same name and kind within 150 m.
    unique = []
    for f in found:
        dup = any(
            u["kind"] == f["kind"]
            and f["name"]
            and u["name"].lower() == f["name"].lower()
            and haversine_km(u["lat"], u["lon"], f["lat"], f["lon"]) < 0.15
            for u in unique
        )
        if not dup:
            unique.append(f)

    for f in unique:
        f.pop("_dist", None)
    return unique


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    # Exact tag matches (not regular expressions): the public servers answer
    # these much faster, which matters when they are busy.
    around = f"(around:{radius_m},{lat},{lon});"
    pairs = [
        ("amenity", "hospital"), ("amenity", "clinic"), ("amenity", "doctors"), ("amenity", "pharmacy"),
        ("healthcare", "hospital"), ("healthcare", "clinic"), ("healthcare", "doctor"),
        ("healthcare", "pharmacy"), ("healthcare", "centre"),
    ]
    body = "".join(f'  nwr["{k}"="{v}"]{around}\n' for k, v in pairs)
    return "[out:json][timeout:25];\n(\n" + body + ");\nout tags center 150;\n"


def _overpass(query: str) -> list:
    """POSTs the query, trying each mirror in turn and retrying once after a
    short pause. Returns raw elements. Every failed attempt is logged so the
    reason is visible in the server terminal."""
    started = time.time()
    last_problem = "no response"
    for round_no in range(ROUNDS):
        if round_no:
            time.sleep(ROUND_PAUSE_S)
        for url in OVERPASS_URLS:
            if time.time() - started > TIME_BUDGET_S:
                break
            try:
                res = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=REQUEST_TIMEOUT_S,
                )
            except requests.RequestException as exc:
                last_problem = f"{exc.__class__.__name__}"
                log.warning("Overpass %s failed: %s", url, last_problem)
                continue
            if res.status_code != 200:
                last_problem = f"HTTP {res.status_code}"
                log.warning("Overpass %s failed: %s", url, last_problem)
                continue
            try:
                return res.json().get("elements", [])
            except ValueError:
                last_problem = "invalid JSON"
                log.warning("Overpass %s returned invalid JSON", url)
    raise FacilitiesError(
        "Could not reach the map data service right now. Please try again in a moment. "
        f"({last_problem})"
    )


def _elements_for(lat: float, lon: float, radius_m: int) -> list:
    key = (round(lat, 2), round(lon, 2), radius_m)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]
    elements = _overpass(_build_query(lat, lon, radius_m))
    _cache[key] = (time.time(), elements)
    return elements


def find_facilities(lat: float, lon: float) -> dict:
    """Returns {"facilities": [...], "radiusKm": n}, nearest first."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise FacilitiesError("Invalid coordinates.")

    facilities: list = []
    radius_m = RADII_M[-1]
    for radius_m in RADII_M:
        facilities = parse_elements(_elements_for(lat, lon, radius_m), lat, lon)
        if len(facilities) >= MIN_RESULTS:
            break

    return {"facilities": facilities[:MAX_RESULTS], "radiusKm": radius_m / 1000}