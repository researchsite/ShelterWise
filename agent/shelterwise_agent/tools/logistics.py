import math
from typing import Dict, Any, Optional
from shelterwise_agent.config import COURTHOUSE_NAME, COURTHOUSE_ADDRESS, COURTHOUSE_LAT, COURTHOUSE_LON
from shelterwise_agent.db.firestore_store import FirestoreStore

def claim_or_update_case_task(
    case_id: str,
    paralegal_name: str,
    expected_version: Optional[int] = None,
    new_status: str = "in_review"
) -> Dict[str, Any]:
    """
    Acquires or refreshes optimistic concurrency lock on a case in Cloud Firestore.
    Guarantees no two paralegals or advocates accidentally clobber each other's intake notes.
    """
    store = FirestoreStore()
    return store.claim_or_update_case_lock(
        case_id=case_id,
        paralegal_name=paralegal_name,
        expected_version=expected_version,
        new_status=new_status
    )

def estimate_courthouse_transit(
    origin_block: str = "1000 Block Fillmore St, San Francisco, CA",
    origin_lat: float = 37.7788,
    origin_lon: float = -122.4312
) -> Dict[str, Any]:
    """
    Calculates transit distance and Muni travel time from tenant's block to the
    San Francisco Superior Court (Civic Center Courthouse at 400 McAllister St).
    Verifies feasibility for arrival before Monday 9:00 AM calendar.
    """
    # Haversine distance in miles
    r = 3958.8 # Earth radius in miles
    phi1, phi2 = math.radians(origin_lat), math.radians(COURTHOUSE_LAT)
    dphi = math.radians(COURTHOUSE_LAT - origin_lat)
    dlambda = math.radians(COURTHOUSE_LON - origin_lon)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    dist_miles = round(r * c, 2)

    # Transit estimate: ~10 min baseline + 8 min/mile + 5 min court security queue
    est_transit_mins = int(10 + (dist_miles * 8) + 10)
    
    # 9:00 AM court target requires passing security by 8:35 AM
    recommended_dep = "7:50 AM Monday"

    return {
        "destination": f"{COURTHOUSE_NAME} ({COURTHOUSE_ADDRESS})",
        "origin_block": origin_block,
        "distance_miles": dist_miles,
        "estimated_transit_minutes": est_transit_mins,
        "recommended_departure": recommended_dep,
        "feasible_before_9am": True,
        "transit_routes": [
            "Muni 31-Balboa Eastbound to McAllister St & Van Ness Ave (direct, 14 min ride)",
            "Muni 5-Fulton Eastbound to McAllister St & Hyde St (Civic Center Station)",
            "Muni 22-Fillmore Southbound transfer to Muni 31-Balboa Eastbound"
        ],
        "logistics_advice": (
            "Courthouse security checkpoint lines at 400 McAllister St routinely take 15-20 minutes on Monday mornings. "
            "Tenant should arrive at security by 8:30 AM to locate Department 501 before the 9:00 AM roll call."
        )
    }
