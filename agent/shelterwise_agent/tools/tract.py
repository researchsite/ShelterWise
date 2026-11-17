from google.adk.tools import tool
from shelterwise_agent.schemas import TractContext
from shelterwise_agent.db.bigquery_client import BQClient

@tool
def get_tract_displacement_baseline(geoid: str) -> dict:
    """Queries pre-aggregated tract displacement context without audit columns."""
    bq = BQClient()
    row = bq.get_tract_context(geoid.zfill(11))
    
    if not row:
        return {"error": "Tract not found"}
        
    ctx = TractContext(
        census_tract_geoid=row['census_tract_geoid'],
        severe_rent_burden_pct=row['severe_rent_burden_pct'],
        annual_filings_total=row['annual_filings_total'],
        open_residential_311_count=row['open_residential_311_count'],
        is_silent_distress_candidate=row['is_silent_distress_candidate']
    )
    return ctx.model_dump()
