"""search_corroborating_complaints: the custom tool at the heart of ShelterWise.

Vector search is only a candidate generator. The rules below decide what counts,
and every dropped record keeps the reason it was dropped. We never look at the
text markers of the planted test rows; the planted traps must fail the real rules.
"""

from __future__ import annotations

import math
from typing import Optional

from .. import config
from ..data import Repo, get_repo
from ..schemas import EvidenceHit, EvidenceResult, ExcludedHit


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def exclusion_reasons(row: dict, origin: Optional[tuple[float, float]], radius_m: Optional[float],
                      metro: str) -> tuple[list[str], Optional[float]]:
    """The eligibility rules. Returns (reasons, meters_away). No reasons = keep."""
    reasons: list[str] = []
    if row.get("metro_area") != metro:
        reasons.append("other_metro")
    if row.get("property_type") != "Residential":
        reasons.append("not_residential")
    status = (row.get("inspection_status") or "").strip().lower()
    if row.get("closed_date") or status.startswith("closed"):
        if "abated" in status:
            reasons.append("closed_abated")
        elif "no violation" in status:
            reasons.append("closed_no_violation")
        else:
            reasons.append("closed_other")
    meters = None
    if origin and row.get("latitude") is not None and row.get("longitude") is not None:
        meters = round(haversine_m(origin[0], origin[1], float(row["latitude"]), float(row["longitude"])), 1)
        if radius_m is not None and meters > radius_m:
            reasons.append("outside_radius")
    return reasons, meters


def apply_rules(candidates: list[dict], *, search_query: str, retrieval_mode: str,
                origin: Optional[tuple[float, float]], radius_m: Optional[float],
                metro: str | None = None, keep_max: int | None = None) -> dict:
    metro = metro or config.METRO
    keep_max = keep_max or config.KEEP_MAX
    kept, excluded = [], []
    ordered = sorted(candidates, key=lambda r: r["cosine_distance"])
    for rank, row in enumerate(ordered, start=1):
        reasons, meters = exclusion_reasons(row, origin, radius_m, metro)
        hit = dict(
            request_id=row["request_id"], block_address=row["block_address"],
            census_tract_geoid=str(row["census_tract_geoid"]), property_type=row["property_type"],
            raw_complaint_type=row["raw_complaint_type"], inspection_status=row["inspection_status"],
            created_date=row.get("created_date"), closed_date=row.get("closed_date"),
            narrative=row["complaint_narrative"], similarity_rank=rank,
            cosine_distance=float(row["cosine_distance"]), meters_away=meters,
        )
        if reasons:
            excluded.append(ExcludedHit(**hit, reasons=reasons))
        else:
            kept.append(EvidenceHit(**hit))
    kept.sort(key=lambda h: (h.cosine_distance, h.meters_away or 0.0))
    kept = kept[:keep_max]
    result = EvidenceResult(
        retrieval_mode=retrieval_mode, search_query=search_query, location_known=origin is not None,
        radius_m=radius_m if origin else None, kept=kept, excluded=excluded,
        has_open_residential_nearby=bool(kept) and origin is not None,
    )
    return result.model_dump(mode="json")


def search_corroborating_complaints(search_query: str, lat: Optional[float] = None,
                                    lng: Optional[float] = None, radius_m: Optional[float] = None,
                                    top_k: Optional[int] = None, repo: Repo | None = None) -> dict:
    """Find open residential 311 complaints near a location that match the tenant's conditions.

    Args:
        search_query: The conditions in city-inspector wording (personal info already removed).
        lat: Latitude of the tenant's block, if known.
        lng: Longitude of the tenant's block, if known.
        radius_m: Search radius in meters (default from config, 400).
        top_k: How many semantic candidates to pull before the rules run (default 50).

    Returns:
        dict with `kept` (corroborating records), `excluded` (look-alikes with reasons),
        `has_open_residential_nearby`, and `retrieval_mode`.
    """
    repo = repo or get_repo()
    origin = (lat, lng) if lat is not None and lng is not None else None
    candidates = repo.vector_candidates(search_query, top_k or config.TOP_K)
    return apply_rules(candidates, search_query=search_query, retrieval_mode=repo.retrieval_mode,
                       origin=origin, radius_m=config.RADIUS_M if radius_m is None else radius_m)
