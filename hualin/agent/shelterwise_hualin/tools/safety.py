"""Life-safety check. Runs on the raw intake before anything else is shown."""

from __future__ import annotations

import re

_WATER = r"(water|leak\w*|drip\w*|wet|flood\w*|soak\w*)"
_ELEC = r"(fuse|breaker|electric\w*|panel|outlet\w*|wiring|wires|socket\w*)"

RULES = [
    {
        "id": "water_near_electrical",
        "test": lambda t, h: bool(re.search(_WATER, t) and re.search(_ELEC, t)) or {"water_leak", "electrical"} <= h,
        "message": "Water near electrical equipment: do not touch the panel, outlets or wet switches. "
                   "If there is sparking, smoke or a burning smell, leave the unit and call 911. "
                   "Report it to SF Building Inspection (311) as an emergency.",
    },
    {
        "id": "gas",
        "test": lambda t, h: bool(re.search(r"\b(gas (smell|leak)|smell\w* (of )?gas|rotten egg)", t)) or "gas" in h,
        "message": "Possible gas leak: leave the building now, don't use switches or flames, "
                   "and call 911 and PG&E's gas emergency line from outside.",
    },
    {
        "id": "carbon_monoxide",
        "test": lambda t, h: bool(re.search(r"carbon monoxide|\bco (alarm|detector)", t)),
        "message": "Carbon monoxide risk: get everyone outside and call 911.",
    },
    {
        "id": "fire_smoke",
        "test": lambda t, h: bool(re.search(r"\b(fire|smoke|sparks?|sparking|burning smell)\b", t)) or "fire" in h,
        "message": "Fire or sparking hazard: if active, leave and call 911.",
    },
    {
        "id": "sewage",
        "test": lambda t, h: bool(re.search(r"sewage|sewer back", t)) or "sewage" in h,
        "message": "Sewage exposure is a health risk: keep children away, avoid contact, report to 311 / DBI.",
    },
    {
        "id": "cold_vulnerable",
        "test": lambda t, h: ("heat" in h or bool(re.search(r"no heat|freezing|\b[3-5]\d\s*(degrees|°)", t)))
        and bool(re.search(r"\b(baby|infant|newborn|kid|child\w*|elderly|senior|sick|pneumonia|asthma)\b", t)),
        "message": "No heat with a child, elderly or sick person in the home: consider a warm place to stay "
                   "tonight and report it to 311 as a no-heat emergency.",
    },
]


def check_safety(raw_text: str, hazards: list[str] | None = None) -> dict:
    text = (raw_text or "").lower()
    hz = set(hazards or [])
    alerts = [{"id": r["id"], "message": r["message"]} for r in RULES if r["test"](text, hz)]
    return {"alerts": alerts, "has_alerts": bool(alerts)}
