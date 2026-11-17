"""Navigator tool: explain why a 311 record was kept or excluded."""

from __future__ import annotations

from google.adk.tools import ToolContext

REASON_TEXT = {
    "not_residential": "it is a commercial / non-residential property, so it says nothing about a tenant's home",
    "closed_abated": "the case is closed: the city verified the problem was fixed",
    "closed_no_violation": "the case is closed: the inspector found no violation",
    "closed_other": "the case is closed",
    "outside_radius": "it is too far from the tenant's block to corroborate her conditions",
    "other_metro": "it is in a different city",
}


def explain_exclusion(request_id: str, tool_context: ToolContext) -> dict:
    """Explain why a 311 record was kept as evidence or excluded from the brief.

    Args:
        request_id: The 311 request ID, e.g. "SF-202665182".
    """
    evidence = tool_context.state.get("evidence") or {}
    for hit in evidence.get("kept", []):
        if hit["request_id"] == request_id:
            return {"request_id": request_id, "status": "kept",
                    "explanation": "Open, residential and within the search radius, so it corroborates "
                                   "block-level conditions (not her specific unit).",
                    "record": hit}
    for hit in evidence.get("excluded", []):
        if hit["request_id"] == request_id:
            return {"request_id": request_id, "status": "excluded",
                    "semantic_rank_before_rules": hit["similarity_rank"],
                    "reasons": [REASON_TEXT.get(r, r) for r in hit["reasons"]],
                    "record": {k: hit[k] for k in ("block_address", "property_type", "inspection_status",
                                                   "closed_date", "meters_away", "narrative")}}
    return {"request_id": request_id, "status": "not_found",
            "explanation": "That ID was not among the search candidates for this intake."}
