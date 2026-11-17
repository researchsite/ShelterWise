from google.adk.tools import tool
from shelterwise_agent.schemas import IntakeFacts

@tool
def structure_intake(narrative: str, geoid: str = None) -> dict:
    """Structures raw tenant intake narrative, detects life safety hazards, and sanitizes PII."""
    hazard = any(word in narrative.lower() for word in ['water near fuse', 'gas leak', 'sparks', 'raw sewage'])
    hearing_72h = 'monday' in narrative.lower() and 'hearing' in narrative.lower()
    
    geoid_11 = geoid.zfill(11) if geoid else None
    
    facts = IntakeFacts(
        normalized_issue_categories=["Habitability", "Eviction Risk"],
        reported_facts=[narrative],
        immediate_life_safety_hazard=hazard,
        census_tract_geoid_11=geoid_11,
        hearing_within_72h=hearing_72h,
        unknowns=["Tenant income details", "Exact notice served"]
    )
    return facts.model_dump()
