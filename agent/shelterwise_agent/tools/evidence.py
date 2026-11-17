"""Tool 2 (`search_public_evidence`): BigQuery VECTOR_SEARCH + deterministic business-rule decoy filter."""

from typing import Any

from ..config import ToolContext, normalize_geoid_11, resolve_metro_name
from ..db import get_housing_repository
from ..schemas import (
    EvidenceQuery,
    EvidenceRecord,
    EvidenceSearchResult,
    ExcludedCandidate,
    ExclusionCode,
    assert_no_audit_columns,
)
from .intake import scrub_pii_narrative

_PORTAL_URLS: dict[str, str] = {
    "San Francisco": "https://data.sfgov.org/",
    "Chicago": "https://data.cityofchicago.org/",
    "New York": "https://opendata.cityofnewyork.us/",
    "Austin": "https://data.austintexas.gov/",
    "Baton Rouge": "https://data.brla.gov/",
    "Cincinnati": "https://data.cincinnati-oh.gov/",
}


def evaluate_311_candidate_eligibility(
    row: dict[str, Any],
    expected_metro: str,
    semantic_rank: int,
) -> tuple[bool, ExclusionCode | None, str]:
    """Validate a semantic 311 candidate using ONLY legitimate public source fields.

    CRITICAL RULE (from `docs/RETRIEVAL_AND_EVIDENCE.md`):
    Never inspect `request_id` prefixes (such as `DECOY-*`) or `audit_*` fields to reject
    records. All 9 planted decoys per metro fail legitimate residential/open-violation rules:
      - 3 Commercial properties (`property_type != 'Residential'`)
      - 3 Closed - Abated historical cases (`closed_date IS NOT NULL` / `Closed - Abated`)
      - 3 Closed - No Violation inspections (`Closed - No Violation`)
    """
    row_metro = str(row.get("metro_area") or "").strip()
    prop_type = str(row.get("property_type") or "").strip()
    status_raw = str(row.get("inspection_status") or "").strip()
    status_lower = status_raw.lower()
    closed_raw = row.get("closed_date")
    has_closed_date = closed_raw is not None and str(closed_raw).strip().lower() not in (
        "",
        "none",
        "nat",
        "null",
    )
    dist = float(row.get("cosine_distance", 1.0))

    if row_metro.lower() != expected_metro.lower():
        return (
            False,
            "wrong_jurisdiction",
            (
                f"Excluded at semantic rank #{semantic_rank} (cosine distance {dist:.4f}): "
                f"metro_area is {row_metro!r}, outside requested jurisdiction {expected_metro!r}."
            ),
        )

    if prop_type.lower() != "residential":
        return (
            False,
            "non_residential_property",
            (
                f"Excluded at semantic rank #{semantic_rank} (cosine distance {dist:.4f}): "
                f"property_type is {prop_type!r} rather than 'Residential'. Emergency tenant "
                "stabilization funds and implied-warranty habitability defenses require residential occupancy."
            ),
        )

    if "no violation" in status_lower or "zero violation" in status_lower:
        return (
            False,
            "no_violation_inspection",
            (
                f"Excluded at semantic rank #{semantic_rank} (cosine distance {dist:.4f}): "
                f"inspection_status is {status_raw!r} (closed_date={closed_raw}). A clearance "
                "inspection finding zero violations cannot corroborate an active habitability defect."
            ),
        )

    if has_closed_date or status_lower.startswith("closed") or "abated" in status_lower:
        return (
            False,
            "closed_or_abated_case",
            (
                f"Excluded at semantic rank #{semantic_rank} (cosine distance {dist:.4f}): "
                f"case is already closed/resolved (inspection_status={status_raw!r}, "
                f"closed_date={closed_raw}). Habitability-contingent stabilization grants require an active, unclosed case."
            ),
        )

    return (True, None, "")


def _normalize_block_number(block_str: str) -> str:
    tokens = block_str.lower().replace("block", " ").split()
    for tok in tokens:
        if tok.isdigit():
            return tok
    return ""


def search_public_evidence(
    search_query: str = "",
    metro: str = "",
    census_tract_geoid: str = "",
    block_address_hint: str = "",
    top_k: int = 25,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Runs BigQuery AI.EMBED + VECTOR_SEARCH over 311 narratives and enforces eligibility rules.

    Retrieves the top semantically similar 311 records (`gemini-embedding-2`, `use_brute_force: true`)
    and deterministically separates valid open residential records from ineligible near-misses
    (such as commercial buildings, closed/abated repairs, and no-violation inspections).

    Args:
        search_query: Semantic habitability description (auto-hydrates from intake_facts if blank).
        metro: Target metro name (defaults to 'San Francisco' or intake_facts.metro).
        census_tract_geoid: Optional 11-character string census tract GEOID (e.g., '06075012401').
        block_address_hint: Optional 100-block location hint (e.g., '400 Block Ellis St').
        top_k: Number of raw vector candidates to scan before post-filtering (default 25).

    Returns:
        Dictionary with 'corroborating_records', 'excluded_candidates' (with exact exclusion
        reasons and pre-filter semantic ranks), 'has_open_residential_311', and boundary caveats.
    """
    state_intake: dict[str, Any] = {}
    if tool_context is not None and hasattr(tool_context, "state"):
        state_intake = tool_context.state.get("intake_facts") or {}

    effective_query = (
        search_query.strip()
        or str(state_intake.get("semantic_search_query") or "").strip()
        or str(state_intake.get("scrubbed_narrative") or "").strip()
    )
    if not effective_query:
        return {
            "status": "error",
            "error_message": "search_query is required (or run structure_intake first).",
        }

    try:
        effective_metro = resolve_metro_name(
            metro.strip() or str(state_intake.get("metro") or "San Francisco")
        )
        raw_tract = census_tract_geoid.strip() or str(
            state_intake.get("census_tract_geoid") or ""
        )
        clean_tract = normalize_geoid_11(raw_tract) if raw_tract else ""
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}

    effective_block = block_address_hint.strip() or str(
        state_intake.get("block_address_hint") or ""
    ).strip()
    scrubbed_query = scrub_pii_narrative(effective_query)
    bounded_k = max(10, min(int(top_k), 50))

    repo = get_housing_repository()
    try:
        candidates = repo.vector_search_311_candidates(
            metro=effective_metro, semantic_query=scrubbed_query, top_k=bounded_k
        )
    except Exception as exc:
        return {
            "status": "error",
            "error_message": f"311 vector search failed for {effective_metro}: {exc}",
        }

    seen_ids: set[str] = set()
    corroborating: list[EvidenceRecord] = []
    excluded: list[ExcludedCandidate] = []
    exclusion_counts: dict[str, int] = {}

    hint_block_num = _normalize_block_number(effective_block)
    portal_url = _PORTAL_URLS.get(effective_metro, "")

    for rank_idx, cand in enumerate(candidates, start=1):
        req_id = str(cand.get("request_id") or "").strip()
        dist = round(float(cand.get("cosine_distance", 1.0)), 4)
        sim = round(max(0.0, 1.0 - dist), 4)
        cand_geoid = (
            normalize_geoid_11(cand["census_tract_geoid"])
            if cand.get("census_tract_geoid")
            else ""
        )
        closed_val = cand.get("closed_date")
        closed_str = (
            None
            if closed_val is None or str(closed_val).strip().lower() in ("", "none", "nat", "null")
            else str(closed_val).strip()
        )

        if req_id in seen_ids:
            exclusion_counts["duplicate_record"] = exclusion_counts.get("duplicate_record", 0) + 1
            excluded.append(
                ExcludedCandidate(
                    request_id=req_id,
                    block_address=str(cand.get("block_address") or ""),
                    census_tract_geoid=cand_geoid,
                    property_type=str(cand.get("property_type") or ""),
                    raw_complaint_type=str(cand.get("raw_complaint_type") or ""),
                    inspection_status=str(cand.get("inspection_status") or ""),
                    created_date=str(cand.get("created_date") or ""),
                    closed_date=closed_str,
                    cosine_distance=dist,
                    similarity_score=sim,
                    semantic_rank_before_filter=rank_idx,
                    exclusion_code="duplicate_record",
                    exclusion_reason=f"Duplicate request_id {req_id} already evaluated.",
                    complaint_narrative_excerpt=str(cand.get("complaint_narrative") or "")[:220],
                    data_provenance=str(cand.get("data_provenance") or ""),
                )
            )
            continue
        seen_ids.add(req_id)

        is_valid, exc_code, exc_reason = evaluate_311_candidate_eligibility(
            cand, expected_metro=effective_metro, semantic_rank=rank_idx
        )
        if not is_valid and exc_code is not None:
            exclusion_counts[exc_code] = exclusion_counts.get(exc_code, 0) + 1
            excluded.append(
                ExcludedCandidate(
                    request_id=req_id,
                    block_address=str(cand.get("block_address") or ""),
                    census_tract_geoid=cand_geoid,
                    property_type=str(cand.get("property_type") or ""),
                    raw_complaint_type=str(cand.get("raw_complaint_type") or ""),
                    inspection_status=str(cand.get("inspection_status") or ""),
                    created_date=str(cand.get("created_date") or ""),
                    closed_date=closed_str,
                    cosine_distance=dist,
                    similarity_score=sim,
                    semantic_rank_before_filter=rank_idx,
                    exclusion_code=exc_code,
                    exclusion_reason=exc_reason,
                    complaint_narrative_excerpt=str(cand.get("complaint_narrative") or "")[:240],
                    data_provenance=str(cand.get("data_provenance") or ""),
                )
            )
            continue

        cand_block = str(cand.get("block_address") or "")
        cand_block_num = _normalize_block_number(cand_block)
        matched_fields = [
            f"metro_area={effective_metro}",
            "property_type=Residential",
            "closed_date=NULL",
            f"inspection_status={cand.get('inspection_status')}",
            f"semantic_similarity={sim:.4f}",
        ]

        if effective_block and (
            effective_block.lower() in cand_block.lower()
            or (hint_block_num and hint_block_num == cand_block_num)
        ):
            geo_level = "same_100_block"
            matched_fields.append(f"block_address~={effective_block}")
        elif clean_tract and cand_geoid == clean_tract:
            geo_level = "same_census_tract"
            matched_fields.append(f"census_tract_geoid={clean_tract}")
        else:
            geo_level = "metro_corridor_semantic_match"

        corroborating.append(
            EvidenceRecord(
                request_id=req_id,
                state_code=str(cand.get("state_code") or ""),
                metro_area=effective_metro,
                jurisdiction=str(cand.get("jurisdiction") or ""),
                agency_code=str(cand.get("agency_code") or ""),
                block_address=cand_block,
                census_tract_geoid=cand_geoid,
                property_type=str(cand.get("property_type") or "Residential"),
                raw_complaint_type=str(cand.get("raw_complaint_type") or ""),
                inspection_status=str(cand.get("inspection_status") or ""),
                created_date=str(cand.get("created_date") or ""),
                closed_date=None,
                latitude=cand.get("latitude"),
                longitude=cand.get("longitude"),
                cosine_distance=dist,
                similarity_score=sim,
                semantic_rank_before_filter=rank_idx,
                geography_match_level=geo_level,
                matched_fields=matched_fields,
                complaint_narrative=str(cand.get("complaint_narrative") or ""),
                inclusion_rationale=(
                    f"Active open residential 311 habitability complaint ({geo_level.replace('_', ' ')}, "
                    f"similarity {sim:.2f}) matching reported hazard profile."
                ),
                data_provenance=str(cand.get("data_provenance") or ""),
                source_portal_url=portal_url,
            )
        )

    # Transparent ranking among eligible records: block match -> tract match -> cosine distance
    geo_priority = {
        "same_100_block": 0,
        "same_census_tract": 1,
        "metro_corridor_semantic_match": 2,
    }
    corroborating.sort(
        key=lambda r: (geo_priority[r.geography_match_level], r.cosine_distance)
    )

    inferred_tract = clean_tract
    if not inferred_tract and corroborating:
        inferred_tract = corroborating[0].census_tract_geoid

    has_open = len(corroborating) > 0
    result_model = EvidenceSearchResult(
        status="success",
        backend_mode=repo.backend_mode,
        evidence_status=(
            "corroborating_records_found"
            if has_open
            else "no_matching_open_residential_record"
        ),
        has_open_residential_311=has_open,
        inferred_tract_geoid=inferred_tract,
        query=EvidenceQuery(
            metro=effective_metro,
            semantic_query=scrubbed_query,
            census_tract_geoid=clean_tract,
            block_address_hint=effective_block,
            top_k_scanned=bounded_k,
        ),
        corroborating_records=corroborating[:10],
        excluded_candidates=excluded[:12],
        exclusion_summary_counts=exclusion_counts,
    )

    result_dict = result_model.model_dump()
    assert_no_audit_columns(result_dict)

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["evidence_pack"] = result_dict

    return result_dict
