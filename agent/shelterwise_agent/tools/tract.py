"""Tool 4 (`get_tract_displacement_baseline`): Fan-out-safe 4Q eviction + ACS tenure context."""

from typing import Any

from ..config import ToolContext, normalize_geoid_11, resolve_metro_name
from ..db import get_housing_repository
from ..schemas import (
    MetroDisplacementBaseline,
    TractContextResult,
    TractDisplacementContext,
    assert_no_audit_columns,
)


def get_tract_displacement_baseline(
    metro: str = "",
    census_tract_geoid: str = "",
    block_address_hint: str = "",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Computes fan-out-safe census tract rent burden and modeled annual eviction context.

    Pre-aggregates `court_eviction_filings` across its 4 quarterly rows per tract before
    joining `acs_tract_housing_tenure`, preserves 11-character leading-zero GEOIDs
    (such as San Francisco's '06075...'), compares the tract against the metro baseline,
    and strictly excludes all `audit_*` demographic columns.

    Args:
        metro: Target metro name (defaults to 'San Francisco' or intake_facts.metro).
        census_tract_geoid: Optional 11-character string census tract GEOID.
        block_address_hint: Optional 100-block hint used to infer tract if GEOID is omitted.

    Returns:
        Dictionary with 'tract_context', 'metro_baseline', and explicit [Modeled] caveats.
    """
    state_intake: dict[str, Any] = {}
    state_evidence: dict[str, Any] = {}
    if tool_context is not None and hasattr(tool_context, "state"):
        state_intake = tool_context.state.get("intake_facts") or {}
        state_evidence = tool_context.state.get("evidence_pack") or {}

    try:
        effective_metro = resolve_metro_name(
            metro.strip() or str(state_intake.get("metro") or "San Francisco")
        )
        raw_geoid = (
            census_tract_geoid.strip()
            or str(state_intake.get("census_tract_geoid") or "").strip()
            or str(state_evidence.get("inferred_tract_geoid") or "").strip()
        )
        clean_geoid = normalize_geoid_11(raw_geoid) if raw_geoid else ""
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}

    effective_block = block_address_hint.strip() or str(
        state_intake.get("block_address_hint") or ""
    ).strip()

    repo = get_housing_repository()
    try:
        tract_dict, metro_dict = repo.fetch_tract_and_metro_baseline(
            metro=effective_metro,
            census_tract_geoid=clean_geoid,
            block_address_hint=effective_block,
        )
    except Exception as exc:
        return {
            "status": "error",
            "error_message": f"Tract displacement baseline query failed for {effective_metro}: {exc}",
        }

    result_model = TractContextResult(
        status="success",
        backend_mode=repo.backend_mode,
        tract_context=TractDisplacementContext(**tract_dict),
        metro_baseline=MetroDisplacementBaseline(**metro_dict),
    )
    result_dict = result_model.model_dump()
    assert_no_audit_columns(result_dict)

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["tract_context"] = result_dict

    return result_dict
