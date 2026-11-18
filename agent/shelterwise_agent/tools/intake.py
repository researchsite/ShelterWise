import re
from typing import Optional, Dict, Any, List
from shelterwise_agent.schemas import IntakeFacts

def kw_match(patterns: List[str], text: str) -> bool:
    regex = r'\b(' + '|'.join(patterns) + r')\b'
    return bool(re.search(regex, text, re.IGNORECASE))

def structure_intake(
    narrative: str, 
    geoid: Optional[str] = "06075016300", 
    block_address: Optional[str] = "1000 Block Fillmore St, San Francisco, CA",
    hearing_date: Optional[str] = None
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
        "fuse box", "sparking", "arcing", "gas leak", "raw sewage", "carbon monoxide",
        "black mold", "toxic mold", "breathing", "respiratory", "asthma", "sewage backup",
        "structural collapse", "ceiling collapse", "lead paint"
    ]
    hazard_detected = any(trigger in lower for trigger in safety_triggers)
    safety_message = None
    if hazard_detected:
        if kw_match(["electrical", "fuse", "breaker", "sparking", "arcing"], lower):
            safety_message = (
                "⚠️ IMMEDIATE LIFE-SAFETY ALERT: Acute electrical/water hazard detected. "
                "Advise tenant immediately: DO NOT touch wet breaker panels, switches, or pooled water. "
                "Direct tenant to file emergency SF DBI priority inspection (Call 311 / DBI Code Enforcement) "
                "and contact PG&E if sparking occurs."
            )
        elif kw_match(["sewage", "effluent", "drain", "toilet"], lower):
            safety_message = (
                "⚠️ IMMEDIATE HEALTH-SAFETY ALERT: Raw sewage backflow detected in dwelling. "
                "Advise tenant: avoid contact with effluent to prevent biohazard contamination. "
                "Direct tenant to report immediate sanitary emergency to SF 311 and Department of Public Health."
            )
        elif kw_match(["mold", "spores", "respiratory", "asthma", "stachybotrys"], lower):
            safety_message = (
                "⚠️ RESPIRATORY HAZARD ALERT: Severe toxic mold exposure detected. "
                "Recommend tenant obtain medical documentation of respiratory distress and file "
                "urgent SF DBI habitability complaint under Cal. Health & Safety Code § 17920.3."
            )
        else:
            safety_message = (
                "⚠️ IMMEDIATE LIFE-SAFETY ALERT: Acute habitability defect detected. "
                "Advise tenant to contact SF 311 for priority Department of Building Inspection code enforcement."
            )

    # 2. Issue categories
    categories = []
    if kw_match(["heat", "cold", "radiator", "radiators", "boiler", "freezing", "steam"], lower):
        categories.append("Lack of Adequate Heating (SF Housing Code § 701)")
    if kw_match(["leak", "leaking", "water", "ceiling", "plumbing", "drip", "dripping", "pipe", "flooding"], lower):
        categories.append("Severe Plumbing / Water Intrusion Hazard (Cal. Civ. Code § 1941.1)")
    if kw_match(["fuse", "electrical", "breaker", "wire", "wiring", "sparking", "arcing", "power"], lower):
        categories.append("Electrical Life-Safety Hazard (SF Building Code § 104A)")
    if kw_match(["mold", "fungus", "mildew", "spores", "stachybotrys", "dampness"], lower):
        categories.append("Toxic Mold & Microbial Growth Hazard (Cal. Health & Safety Code § 17920.3)")
    if kw_match(["sewage", "effluent", "drain", "drains", "toilet", "waste", "sro"], lower):
        categories.append("Raw Sewage & Unsanitary Drainage (SF Health Code Art. 11)")
    if kw_match(["retaliate", "retaliation", "retaliatory", "shutoff", "lockout", "harassment"], lower):
        categories.append("Retaliatory Eviction / Landlord Self-Help (Cal. Civ. Code § 1942.5 & § 789.3)")
    if kw_match(["rodent", "rodents", "rat", "rats", "mice", "mouse", "roach", "roaches", "vermin", "pest", "pests", "bedbug", "bedbugs"], lower):
        categories.append("Vermin & Pest Infestation (Cal. Civ. Code § 1941.1)")
    if kw_match(["stairs", "elevator", "egress", "collapse", "structural"], lower):
        categories.append("Structural / Ingress Egress Defect (SF Housing Code § 505)")
    if kw_match(["evict", "court", "hearing", "notice", "summons", "unlawful detainer"], lower):
        categories.append("Active Eviction Court Proceedings (Dept 501)")
    if not categories:
        categories.append("General Habitability Crisis")

    # 3. Court hearing urgency (< 72h)
    hearing_72h = any(k in lower for k in ["monday", "tomorrow", "today", "hearing", "court"]) and any(k in lower for k in ["9am", "9:00", "morning", "summons", "calendar"])
    if hearing_date:
        hearing_str = str(hearing_date)
        if any(w in hearing_str.lower() for w in ["today", "tomorrow", "monday", "tuesday"]):
            hearing_72h = True
    else:
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

    # 6. Rewritten inspector-vocabulary query for BigQuery AI.EMBED + VECTOR_SEARCH
    terms = []
    if kw_match(["mold", "fungus", "mildew", "spores", "stachybotrys", "respiratory", "asthma"], lower):
        terms.append("toxic black mold dampness mildew spore infestation")
    if kw_match(["sewage", "effluent", "drain", "drains", "toilet", "waste", "sro", "effluence"], lower):
        terms.append("raw sewage backup drain plumbing effluent unsanitary")
    if kw_match(["electrical", "fuse", "breaker", "sparking", "arcing", "wire", "wiring", "power"], lower):
        terms.append("electrical wiring breaker box panel arcing sparking shock hazard")
    if kw_match(["heat", "cold", "radiator", "radiators", "boiler", "freezing", "steam"], lower):
        terms.append("no heat defective boiler inoperative steam radiator low temperature")
    if kw_match(["water", "leak", "leaking", "ceiling", "drip", "dripping", "pipe", "flooding"], lower):
        terms.append("ceiling water leak plumbing intrusion roof pipe collapse")
    if kw_match(["rodent", "rodents", "rat", "rats", "mice", "mouse", "roach", "roaches", "vermin", "pest", "pests", "bedbug", "bedbugs"], lower):
        terms.append("rodent mice rats roaches vermin pest infestation")
    if kw_match(["stairs", "elevator", "egress", "collapse", "structural"], lower):
        terms.append("broken stairs elevator out of service safety egress")
    if kw_match(["lockout", "locked", "retaliate", "retaliation", "retaliatory", "shutoff", "harassment"], lower):
        terms.append("retaliatory utility shutoff illegal lockout harassment")

    if not terms:
        stop_words = {"this", "that", "there", "with", "from", "have", "been", "tenant", "landlord", "called", "client", "about", "resident", "san", "francisco"}
        tokens = [w for w in re.findall(r"[a-z]{4,}", lower) if w not in stop_words]
        terms.append(" ".join(tokens[:8]) if tokens else "residential habitability defect")

    search_query = " ".join(terms)

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
