from shelterwise_agent.schemas import EvidencePack, EvidenceRecord
from shelterwise_agent.db.bigquery_client import BQClient

def search_public_evidence(narrative_query: str) -> dict:
    """Runs vector search on 311 complaints and applies business rules to exclude decoys."""
    bq = BQClient()
    results = bq.search_complaints_vector(narrative_query, top_k=15)
    
    valid = []
    excluded = []
    
    for r in results:
        is_decoy = False
        reason = None
        
        if r.property_type != 'Residential':
            is_decoy = True
            reason = "Commercial property decoy"
        elif 'no violation' in str(r.inspection_status).lower():
            is_decoy = True
            reason = "Zero violation decoy"
        elif r.closed_date is not None or 'closed' in str(r.inspection_status).lower():
            is_decoy = True
            reason = "Closed/Abated case decoy"
            
        record = EvidenceRecord(
            request_id=r.request_id,
            block_address=r.block_address,
            inspection_status=r.inspection_status,
            complaint_narrative=r.complaint_narrative,
            match_reason=f"Vector distance: {r.distance:.3f}",
            is_decoy_trap=is_decoy,
            exclusion_reason=reason
        )
        
        if is_decoy:
            excluded.append(record)
        else:
            valid.append(record)
            
    pack = EvidencePack(
        corroborating_records=valid,
        excluded_candidates=excluded,
        has_open_residential_311=len(valid) > 0
    )
    return pack.model_dump()
