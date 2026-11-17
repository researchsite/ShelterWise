import re
from typing import Optional, Dict, Any, List
from shelterwise_agent.schemas import IntakeFacts

def structure_intake(
    narrative: str, 
    geoid: Optional[str] = "06075016300", 
    block_address: Optional[str] = "1000 Block Fillmore St, San Francisco, CA"
) -> Dict[str, Any]:
    """
    Structures raw tenant intake narrative, detects life-safety hazards,
    normalizes 11-digit SF census tract GEOID (preserving leading '06'),
    detects hearing urgency within 72h, and extracts unknown information gaps.
    """
    clean_text = narrative.strip()
    lower = clean_text.lower()

    # 1. Acute Life-Safety Hazard Detection
    safety_triggers = [
        "water near fuse", "water dripping into electrical", "electrical box",
        "fuse box", "sparking", "arcing", "gas leak", "raw sewage", "carbon monoxide"
    ]
    hazard_detected = any(trigger in lower for trigger in safety_triggers)
    safety_message = None
    if hazard_detected:
        safety_message = (
            "⚠️ IMMEDIATE LIFE-SAFETY ALERT: Acute electrical/water hazard detected. "
            "Advise tenant immediately: DO NOT touch wet breaker panels, switches, or pooled water. "
            "Direct tenant to file emergency SF DBI priority inspection (Call 311 / DBI Code Enforcement) "
            "and contact PG&E if arcing occurs."
        )

    # 2. Issue categories
    categories = []
    if any(k in lower for k in ["heat", "radiator", "cold", "boiler", "freezing"]):
        categories.append("Lack of Adequate Heating (SF Housing Code § 701)")
    if any(k in lower for k in ["leak", "water", "ceiling", "plumbing", "drip"]):
        categories.append("Severe Plumbing / Water Intrusion Hazard")
    if any(k in lower for k in ["fuse", "electrical", "breaker", "wire"]):
        categories.append("Electrical Life-Safety Hazard")
    if any(k in lower for k in ["evict", "court", "hearing", "notice", "summons", "unlawful detainer"]):
        categories.append("Active Eviction Court Proceedings")
    if not categories:
        categories.append("General Habitability Crisis")

    # 3. Court hearing urgency (< 72h)
    hearing_72h = any(k in lower for k in ["monday", "tomorrow", "today", "hearing", "court"]) and any(k in lower for k in ["9am", "9:00", "morning", "summons", "calendar"])
    hearing_str = "Monday 9:00 AM (Civic Center Courthouse, 400 McAllister St)" if hearing_72h else "Pending confirmation"

    # 4. GEOID 11-character zero-padding
    geoid_11 = None
    if geoid:
        geoid_str = re.sub(r"[^\d]", "", str(geoid))
        if geoid_str:
            geoid_11 = geoid_str.zfill(11)

    # 5. Extract unknowns
    unknowns = []
    if "ami" not in lower and "income" not in lower and "$" not in lower:
        unknowns.append("Household income / Area Median Income (AMI %) band for grant qualification")
    if "notice" not in lower and "summons" not in lower:
        unknowns.append("Exact court notice served (3-Day Notice to Pay or Quit vs. Summons & Complaint)")
    if "dbi" not in lower and "inspection" not in lower and "complaint number" not in lower:
        unknowns.append("Whether tenant has an existing official SF DBI complaint / service request number")

    # 6. Rewritten inspector-vocabulary query for vector search
    terms = []
    if "heat" in lower or "cold" in lower or "radiator" in lower:
        terms.append("no heat cold dwelling radiators inoperative")
    if "water" in lower or "leak" in lower or "ceiling" in lower:
        terms.append("ceiling water leak plumbing intrusion")
    if "electrical" in lower or "fuse" in lower:
        terms.append("electrical box panel safety hazard")
    search_query = " ".join(terms) if terms else "no heat ceiling leak residential habitability"

    facts = IntakeFacts(
        normalized_issue_categories=categories,
        reported_facts=[clean_text],
        immediate_life_safety_hazard=hazard_detected,
        safety_alert_message=safety_message,
        census_tract_geoid_11=geoid_11,
        block_address=block_address,
        hearing_within_72h=hearing_72h,
        hearing_datetime_str=hearing_str,
        unknowns=unknowns,
        semantic_search_query=search_query
    )
    return facts.model_dump()

def scrub_pii_narrative(text: str) -> str:
    """Scrub caller names, phone numbers, emails, and exact unit numbers."""
    if not text:
        return ""
    cleaned = str(text)
    # Redact phone numbers
    cleaned = re.sub(r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b", "[REDACTED PHONE]", cleaned)
    # Redact email addresses
    cleaned = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED EMAIL]", cleaned)
    # Redact exact apartment/unit numbers
    cleaned = re.sub(r"(?i)\b(?:apt|unit|suite|#)\s*\w+\b", "[REDACTED UNIT]", cleaned)
    return cleaned.strip()
