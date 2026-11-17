"""Turn "1000 block of Fillmore St" into a point.

1. Block centroid from our own 311 data (no API needed).
2. Google Maps Geocoding API fallback (only if GOOGLE_MAPS_API_KEY is set).
3. Otherwise unknown: the agent must ask for the block.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from .. import config
from ..data import Repo, get_repo
from .evidence import haversine_m

_SUFFIX = {
    "street": "st", "st.": "st", "avenue": "av", "ave": "av", "ave.": "av", "boulevard": "bl", "blvd": "bl",
    "way": "wy", "terrace": "tr", "ter": "tr", "alley": "al", "court": "ct", "drive": "dr", "place": "pl",
    "road": "rd",
}
_ADDR = re.compile(r"(\d{1,5})\s*(?:-\s*\d+\s*)?(?:block\s+(?:of\s+)?)?(.+)", re.I)


def normalize_block(address_text: str) -> Optional[tuple[int, str]]:
    """'1032 Fillmore Street' or '1000 block of Fillmore St' -> (1000, 'fillmore st')."""
    if not address_text:
        return None
    text = address_text.split(",")[0].strip()
    m = _ADDR.search(text)
    if not m:
        return None
    block = int(m.group(1)) // 100 * 100
    words = re.sub(r"[^\w\s.]", " ", m.group(2).lower()).split()
    words = [_SUFFIX.get(w, w) for w in words if w not in ("san", "francisco", "sf", "ca")]
    return (block, " ".join(words)) if words else None


def _block_key(block_address: str) -> Optional[tuple[int, str]]:
    m = re.match(r"(\d+) Block (.+?),", block_address or "")
    return (int(m.group(1)), m.group(2).lower()) if m else None


def _nearest_tract(lat: float, lng: float, repo: Repo) -> Optional[str]:
    best = min(repo.acs(), key=lambda t: haversine_m(lat, lng, t["latitude"], t["longitude"]), default=None)
    return str(best["census_tract_geoid"]) if best else None


def _maps_geocode(address_text: str) -> Optional[tuple[float, float]]:
    if not config.MAPS_API_KEY:
        return None
    import requests

    resp = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": f"{address_text}, {config.METRO}, CA", "key": config.MAPS_API_KEY},
        timeout=10,
    )
    results = resp.json().get("results") or []
    if not results:
        return None
    loc = results[0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


def locate(address_text: str, repo: Repo | None = None) -> dict:
    repo = repo or get_repo()
    key = normalize_block(address_text)
    if key:
        rows = [r for r in repo.complaints() if _block_key(r["block_address"]) == key]
        if rows:
            lat = sum(float(r["latitude"]) for r in rows) / len(rows)
            lng = sum(float(r["longitude"]) for r in rows) / len(rows)
            tract = Counter(str(r["census_tract_geoid"]) for r in rows).most_common(1)[0][0]
            return {"lat": round(lat, 6), "lng": round(lng, 6), "matched_block": rows[0]["block_address"],
                    "location_source": "block_centroid_311", "census_tract_geoid": tract,
                    "tract_source": "311 records on this block"}
    point = _maps_geocode(address_text) if address_text else None
    if point:
        return {"lat": point[0], "lng": point[1], "matched_block": None, "location_source": "google_maps",
                "census_tract_geoid": _nearest_tract(*point, repo=repo),
                "tract_source": "nearest tract centroid (approximate)"}
    return {"lat": None, "lng": None, "matched_block": None, "location_source": "unknown",
            "census_tract_geoid": None, "tract_source": None}
