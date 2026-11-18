"""Tool 3 (`fetch_statutes_and_bulletins`): Statutory protections & emergency relief bulletins."""

from typing import Any

from ..config import ToolContext, resolve_metro_name
from ..db import get_housing_repository
from ..schemas import (
    PolicyLookupResult,
    ReliefProgramBulletin,
    StatuteMatch,
    UrgencyTier,
    assert_no_audit_columns,
)


def _parse_categories(raw_categories: str, fallback: list[str]) -> list[str]:
    if raw_categories and raw_categories.strip():
        parts = [
            p.strip().lower()
            for p in raw_categories.replace(";", ",").split(",")
            if p.strip()
        ]
        if parts:
            return parts
    return list(fallback)


def _annotate_statute(
    row: dict[str, Any], categories: list[str], urgency: UrgencyTier
) -> tuple[int, StatuteMatch]:
    text_lower = f"{row.get('ordinance_title', '')} {row.get('raw_statute_text', '')}".lower()
    matched: list[str] = []
    score = 0

    if any(c in categories for c in ("heating_loss", "electrical_water_hazard", "water_intrusion_leak", "mold_dampness", "plumbing_sewage")):
        if any(k in text_lower for k in ("habitability", "heat", "wiring", "untenantable", "repair", "1941", "701")):
            matched.append("habitability_and_repair_duty")
            score += 3
    if "nonpayment_eviction_notice" in categories:
        if any(k in text_lower for k in ("nonpayment", "3-day", "unlawful detainer", "rent", "escrow", "1942.4", "37.9")):
            matched.append("nonpayment_eviction_defense_or_escrow")
            score += 3
    if any(k in text_lower for k in ("retaliat", "180", "six-month", "complaint")):
        matched.append("anti_retaliation_after_311_report")
        score += 2 if "retaliation_or_lockout" in categories else 1

    raw_text = str(row.get("raw_statute_text") or "").strip()
    summary = raw_text if len(raw_text) <= 260 else raw_text[:257].rsplit(" ", 1)[0] + "..."

    if urgency == "immediate_72h":
        pre_hearing_note = (
            "IMMEDIATE (<72h HEARING CLOCK): Supervising attorney must review statutory habitability "
            "affirmative defenses, notice-service defects, and court answer filing deadlines before hearing."
        )
    elif urgency == "urgent_7d":
        pre_hearing_note = (
            "URGENT (<7d WINDOW): Review statutory notice-to-cure timelines and preserve proof of landlord notice."
        )
    else:
        pre_hearing_note = "Standard triage window: verify repair-notice timeline with housing counsel."

    statute = StatuteMatch(
        statute_section_id=str(row.get("statute_section_id") or ""),
        state_code=str(row.get("state_code") or ""),
        metro_area=str(row.get("metro_area") or ""),
        jurisdiction=str(row.get("jurisdiction") or ""),
        code_citation=str(row.get("code_citation") or ""),
        ordinance_title=str(row.get("ordinance_title") or ""),
        plain_language_summary=summary,
        raw_statute_text=raw_text,
        matched_topics=matched or ["general_residential_tenant_protection"],
        pre_hearing_relevance_note=pre_hearing_note,
        applicability_conditions=(
            "Requires verification by a licensed attorney or supervised paralegal of residential tenancy "
            "coverage, prior landlord notice, absence of tenant-caused damage, and procedural deadlines."
        ),
        reviewer_questions=[
            "Did the landlord receive written or actual notice of the habitability condition?",
            "Was the 3-day / eviction notice properly served with accurate rent figures?",
            "Has an official municipal code citation or 311 inspection been opened on this building?",
        ],
        data_provenance=str(row.get("data_provenance") or "[Public Legal Reference]"),
    )
    return score, statute


def fetch_statutes_and_bulletins(
    metro: str = "",
    issue_categories_csv: str = "",
    urgency_tier: str = "",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Fetches state/municipal housing statutes and all 4 emergency rental relief bulletins.

    Safe to execute concurrently inside ADK `ParallelAgent` (`output_key='raw_policy_pack'`);
    final `requires_open_habitability_case` cross-checking against 311 evidence happens
    deterministically in Step 3 (`reconcile_relief_and_gaps`).

    Args:
        metro: Target metro name (defaults to 'San Francisco' or intake_facts.metro).
        issue_categories_csv: Optional comma-separated issue categories from intake.
        urgency_tier: Optional urgency tier ('immediate_72h', 'urgent_7d', 'standard_30d', 'unspecified').

    Returns:
        Dictionary with ranked 'statutes', all 4 'relief_bulletins', and non-legal-advice caveats.
    """
    state_intake: dict[str, Any] = {}
    if tool_context is not None and hasattr(tool_context, "state"):
        state_intake = tool_context.state.get("intake_facts") or {}

    try:
        effective_metro = resolve_metro_name(
            metro.strip() or str(state_intake.get("metro") or "San Francisco")
        )
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}

    categories = _parse_categories(
        issue_categories_csv, state_intake.get("issue_categories") or []
    )
    raw_urg = (urgency_tier.strip() or str(state_intake.get("urgency_tier") or "unspecified")).lower()
    valid_urg: UrgencyTier = (
        raw_urg  # type: ignore[assignment]
        if raw_urg in ("immediate_72h", "urgent_7d", "standard_30d", "unspecified")
        else "unspecified"
    )

    repo = get_housing_repository()
    try:
        raw_statutes = repo.fetch_statutes(effective_metro)
        raw_bulletins = repo.fetch_relief_bulletins(effective_metro)
    except Exception as exc:
        return {
            "status": "error",
            "error_message": f"Policy/bulletin lookup failed for {effective_metro}: {exc}",
        }

    scored_statutes = [
        _annotate_statute(row, categories, valid_urg) for row in raw_statutes
    ]
    scored_statutes.sort(key=lambda pair: (-pair[0], pair[1].statute_section_id))

    bulletins = [
        ReliefProgramBulletin(
            bulletin_id=str(b.get("bulletin_id") or ""),
            state_code=str(b.get("state_code") or ""),
            metro_area=str(b.get("metro_area") or effective_metro),
            service_region=str(b.get("service_region") or effective_metro),
            program_name=str(b.get("program_name") or ""),
            administering_agency=str(b.get("administering_agency") or ""),
            funding_stream=str(b.get("funding_stream") or ""),
            requires_open_habitability_case=bool(b.get("requires_open_habitability_case")),
            residential_tenants_only=bool(b.get("residential_tenants_only", True)),
            raw_bulletin_text=str(b.get("raw_bulletin_text") or ""),
            intake_url=str(b.get("intake_url") or ""),
            effective_date=str(b.get("effective_date") or ""),
            data_provenance=str(b.get("data_provenance") or "[Curated Benchmark]"),
        )
        for b in raw_bulletins
    ]

    result_model = PolicyLookupResult(
        status="success",
        backend_mode=repo.backend_mode,
        metro=effective_metro,
        urgency_tier=valid_urg,
        statutes=[s for _, s in scored_statutes],
        relief_bulletins=bulletins,
    )
    result_dict = result_model.model_dump()
    assert_no_audit_columns(result_dict)

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["raw_policy_pack"] = result_dict

    return result_dict
