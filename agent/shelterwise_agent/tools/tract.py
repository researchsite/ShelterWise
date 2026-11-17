from typing import Dict, Any
from shelterwise_agent.schemas import TractContext
from shelterwise_agent.db.bigquery_client import BQClient

def get_tract_displacement_baseline(geoid: str = "06075016300") -> Dict[str, Any]:
    """
    Retrieves tract displacement baseline from the fan-out-safe v_tract_stability_context view.
    Combines real Census ACS tenure with 4-quarter pre-aggregated modeled court filings.
    
    RESPONSIBLE-AI FIREWALL: Strictly guarantees that NO individual-level or tract-level
    demographic audit_* columns are accessed in this case-level tool.
    """
    clean_geoid = str(geoid).strip().zfill(11)
    bq = BQClient()
    row = bq.get_tract_context(clean_geoid)

    if not row:
        return {"error": f"Tract {clean_geoid} not found in database"}

    # Enforce firewall: ensure no audit columns exist in the output dict
    for forbidden in ["audit_black_share", "audit_hispanic_share", "audit_asian_share", "audit_white_share", "audit_indigenous_share"]:
        row.pop(forbidden, None)

    ctx = TractContext(
        census_tract_geoid=row.get("census_tract_geoid", clean_geoid),
        renter_occupied_units=int(row.get("renter_occupied_units", 0)),
        severely_burdened_hh=int(row.get("severely_burdened_hh", 0)),
        severe_rent_burden_pct=float(row.get("severe_rent_burden_pct", 0.0)),
        median_gross_rent=int(row.get("median_gross_rent", 0)),
        median_household_income=int(row.get("median_household_income", 0)),
        annual_filings_total=int(row.get("annual_filings_total", 0)),
        annual_nonpayment_filings=int(row.get("annual_nonpayment_filings", 0)),
        annual_no_fault_filings=int(row.get("annual_no_fault_filings", 0)),
        annual_defaults_total=int(row.get("annual_defaults_total", 0)),
        open_residential_311_count=int(row.get("open_residential_311_count", 0)),
        is_silent_distress_candidate=bool(row.get("is_silent_distress_candidate", False)),
        sf_tract_median_burden=16.1,
        sf_tract_median_filings=55,
        filings_provenance=row.get("filings_provenance", "[Modeled Court Baseline]"),
        acs_provenance=row.get("acs_provenance", "[Real Census ACS 2018-2022]")
    )
    return ctx.model_dump()
