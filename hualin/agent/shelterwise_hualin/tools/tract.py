"""Neighborhood context for one census tract. Filings are MODELED and pre-summed per tract."""

from __future__ import annotations

from typing import Optional

from ..data import Repo, get_repo


def tract_context(geoid: Optional[str], repo: Repo | None = None) -> dict:
    repo = repo or get_repo()
    if not geoid:
        return {"available": False, "reason": "Tract unknown because the block could not be located."}
    geoid = str(geoid)  # GEOIDs are text: '06075...' must keep its leading zero
    tracts = {t["census_tract_geoid"]: t for t in repo.acs()}
    filings = repo.filings_annual()
    t = tracts.get(geoid)
    if not t:
        return {"available": False, "reason": f"Tract {geoid} not found in {len(tracts)} metro tracts."}

    renters = sum(int(x["renter_occupied_units"] or 0) for x in tracts.values())
    severe = sum(int(x["renter_hh_rent_50_pct_plus_count"] or 0) for x in tracts.values())
    f = filings.get(geoid, {"annual_total": 0, "annual_nonpayment": 0, "annual_no_fault": 0, "quarters": 0})
    totals = sorted(v["annual_total"] for v in filings.values())
    pct_rank = round(100 * sum(1 for v in totals if v <= f["annual_total"]) / len(totals)) if totals else None
    open_res = sum(1 for c in repo.complaints() if str(c["census_tract_geoid"]) == geoid
                   and c["property_type"] == "Residential" and not c["closed_date"])
    t_renters = int(t["renter_occupied_units"] or 0)
    t_severe = int(t["renter_hh_rent_50_pct_plus_count"] or 0)
    return {
        "available": True,
        "census_tract_geoid": geoid,
        "renter_households": t_renters,
        "severe_rent_burden_households": t_severe,
        "severe_rent_burden_pct": round(100 * t_severe / t_renters, 1) if t_renters else None,
        "metro_severe_rent_burden_pct": round(100 * severe / renters, 1) if renters else None,
        "median_gross_rent": t["median_gross_rent"],
        "median_household_income": t["median_household_income"],
        "annual_filings_modeled": f["annual_total"],
        "annual_nonpayment_modeled": f["annual_nonpayment"],
        "annual_no_fault_modeled": f["annual_no_fault"],
        "quarters_summed": f["quarters"],
        "filings_percentile_in_metro": pct_rank,
        "metro_annual_filings_modeled": sum(totals),
        "open_residential_311_in_tract": open_res,
        "filings_are_modeled": True,
        "provenance": "Rent burden: US Census ACS 5-year (real). Filings: MODELED from county court "
                      "baselines, not real court records.",
    }
