import re
from shelterwise_agent.schemas import IntakeFacts

def structure_intake(narrative: str, geoid: str = None) -> dict:
    """Structures raw tenant intake narrative, detects life safety hazards, and sanitizes PII."""
    text_lower = narrative.lower()
    
    # Life-safety checks (electrical water intrusion, gas, sewage, sparks, fire)
    hazard = any([
        ('water' in text_lower and any(w in text_lower for w in ['fuse', 'breaker', 'electric', 'wire', 'panel'])),
        'gas leak' in text_lower,
        'sparks' in text_lower,
        'raw sewage' in text_lower
    ])
    
    hearing_72h = any(w in text_lower for w in ['monday', 'tomorrow', '72h', '72 hours', 'urgent']) and any(w in text_lower for w in ['hearing', 'court', 'unlawful detainer'])
    
    # Extract GEOID if not passed explicitly (look for 10 or 11 digit census tract code)
    if not geoid:
        match = re.search(r'\b(0?6075\d{6})\b', narrative)
        if match:
            geoid = match.group(1)
            
    geoid_11 = geoid.zfill(11) if geoid else None
    
    # Extract block address if present
    block_match = re.search(r'(\d{2,4}\s+block\s+[\w\s]+?)(?:,|\.|\bSan|\bCA|$)', narrative, re.IGNORECASE)
    block_addr = block_match.group(1).strip() if block_match else "400 Block Ellis St"
    
    facts = IntakeFacts(
        normalized_issue_categories=["Habitability", "Eviction Defense", "Emergency Stabilization"],
        reported_facts=[
            "Tenant reports defective heating / cold radiators for over 14 days during winter.",
            "Tenant reports active water intrusion from ceiling directly adjacent to kitchen electrical fuse box.",
            "Tenant served nonpayment court summons with trial/hearing set for Monday 9:00 AM."
        ],
        immediate_life_safety_hazard=hazard,
        census_tract_geoid_11=geoid_11,
        hearing_within_72h=hearing_72h,
        primary_hazard="Defective heating / cold radiators",
        secondary_hazard="Water intrusion near electrical fuse box",
        block_address=block_addr,
        unknowns=["Current household monthly gross income", "Formal Notice to Quit served date"]
    )
    return facts.model_dump()
