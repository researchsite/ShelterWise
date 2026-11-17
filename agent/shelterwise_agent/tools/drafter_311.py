from typing import Dict, Any

def draft_311_inspection_request(
    hazard_description: str,
    block_address: str = "1000 Block Fillmore St, San Francisco, CA",
    priority: str = "Emergency Life Safety"
) -> Dict[str, Any]:
    """
    Drafts a formal San Francisco Department of Building Inspection (DBI) service request
    when zero 311 records exist on the block, establishing official city documentation.
    """
    filing_text = (
        f"MUNICIPAL 311 / SF DBI EMERGENCY INSPECTION REQUEST\n"
        f"Address: {block_address}\n"
        f"Complaint Type: Habitability / Heating & Electrical Hazard\n"
        f"Priority Level: {priority}\n\n"
        f"Hazard Description:\n{hazard_description}\n\n"
        f"Urgent Request: Request immediate on-site inspection by DBI Housing Inspection Services (HIS). "
        f"Tenant dwelling unit is lacking central heat required by SF Housing Code § 701 and ceiling water leak "
        f"is actively dripping near electrical panel box creating immediate hazard of electrical fire/arcing. "
        f"Official inspection record is urgently required for eviction defense and emergency habitability repair bridge grant."
    )
    return {
        "agency": "San Francisco Department of Building Inspection (DBI)",
        "department": "Housing Inspection Services (HIS)",
        "block_address": block_address,
        "priority": priority,
        "filing_channel": "SF311 Mobile App / Phone: 3-1-1 / Online: sf311.org",
        "draft_text": filing_text,
        "expected_timeline": "DBI emergency response required within 24 hours for life-safety hazards."
    }
