"""Tool 5 (`reconcile_gaps_and_generate_brief`): Relief eligibility gating, evidence gaps & 9-section Brief.

Exports three compatible ADK FunctionTools so Member 3's `eligibility_and_brief_agent` works
seamlessly whether it calls two granular steps or one combined step:
  - `reconcile_relief_and_gaps`
  - `generate_stabilization_brief`
  - `reconcile_gaps_and_generate_brief`
"""

from typing import Any

from ..config import ToolContext, get_metro_metadata
from ..schemas import (
    EvaluatedReliefProgram,
    EvidenceGapItem,
    EvidenceRecord,
    ExcludedCandidate,
    MetroDisplacementBaseline,
    ReliefProgramBulletin,
    ReviewerChecklistItem,
    SafetyAlert,
    StabilizationBrief,
    StatuteMatch,
    TractDisplacementContext,
    UrgencyTier,
    assert_no_audit_columns,
)


def evaluate_relief_programs_deterministic(
    bulletins: list[dict[str, Any]],
    corroborating_records: list[dict[str, Any]],
    urgency_tier: UrgencyTier,
) -> list[EvaluatedReliefProgram]:
    """Deterministically gate relief programs on `requires_open_habitability_case` & residential rule."""
    has_open_311 = len(corroborating_records) > 0
    open_ids = [str(r.get("request_id")) for r in corroborating_records[:3] if r.get("request_id")]

    scored: list[tuple[int, EvaluatedReliefProgram]] = []
    for raw in bulletins:
        b = ReliefProgramBulletin(**raw) if not isinstance(raw, ReliefProgramBulletin) else raw
        req_hab = b.requires_open_habitability_case

        if req_hab and has_open_311:
            fit = "eligible_to_screen"
            sort_score = 0 if urgency_tier == "immediate_72h" else 1
            rationale = (
                f"MEETS OPEN-HABITABILITY PREREQUISITE: `requires_open_habitability_case = TRUE` is "
                f"corroborated at the 100-block level by open residential 311 case(s) "
                f"({', '.join(open_ids)}). Paralegal must still verify unit-level proof, residential "
                f"lease, and household AMI cap."
            )
            docs = [
                f"Cite open municipal 311 request ID(s): {', '.join(open_ids)}",
                "Unit-level habitability proof (dated photos, landlord repair texts)",
                "Written 3-day notice or court summons + residential lease / rent ledger",
                "Household income / AMI verification",
            ]
        elif req_hab and not has_open_311:
            fit = "conditional_needs_open_311_case"
            sort_score = 3
            rationale = (
                "CONDITIONAL — OPEN 311 CASE REQUIRED: `requires_open_habitability_case = TRUE`, "
                "and 0 open residential 311 complaints were found near this block. Absence of a 311 "
                "record does NOT disprove the tenant's report; file an official 311/DBI inspection "
                "request immediately to unlock this fund, and screen for general stabilization funds first."
            )
            docs = [
                "New municipal 311 / DBI residential inspection request confirmation number",
                "Dated unit photos of reported habitability defect",
                "Residential lease, arrears notice, and household AMI proof",
            ]
        else:
            fit = "eligible_to_screen"
            # When 0 open 311s exist OR court is <72h away, general funds without 311 gate are critical
            sort_score = 0 if (not has_open_311 or urgency_tier == "immediate_72h") else 2
            rationale = (
                "ELIGIBLE TO SCREEN IMMEDIATELY (`requires_open_habitability_case = FALSE`): "
                "General emergency rental stabilization fund that does NOT require a prior municipal "
                "311 habitability case — critical fast-track option ahead of court deadlines or on "
                "under-reported blocks."
            )
            docs = [
                "Copy of 3-day pay-or-quit notice or unlawful detainer summons",
                "Residential lease or proof of tenancy & rent arrears ledger",
                "Household income / hardship documentation",
            ]

        scored.append(
            (
                sort_score,
                EvaluatedReliefProgram(
                    bulletin_id=b.bulletin_id,
                    program_name=b.program_name,
                    administering_agency=b.administering_agency,
                    funding_stream=b.funding_stream,
                    requires_open_habitability_case=b.requires_open_habitability_case,
                    residential_tenants_only=b.residential_tenants_only,
                    screening_fit=fit,  # type: ignore[arg-type]
                    priority_rank=1,
                    fit_rationale=rationale,
                    required_documents_to_confirm=docs,
                    intake_url=b.intake_url,
                    effective_date=b.effective_date,
                    data_provenance=b.data_provenance,
                ),
            )
        )

    scored.sort(key=lambda pair: (pair[0], pair[1].bulletin_id))
    ranked: list[EvaluatedReliefProgram] = []
    for idx, (_, prog) in enumerate(scored, start=1):
        prog.priority_rank = idx
        ranked.append(prog)
    return ranked


def build_evidence_gaps_deterministic(
    intake_facts: dict[str, Any],
    corroborating_records: list[dict[str, Any]],
) -> list[EvidenceGapItem]:
    """Identify missing unit-level, procedural, and 311 corroboration items safely."""
    categories = set(intake_facts.get("issue_categories") or [])
    has_open_311 = len(corroborating_records) > 0
    gaps: list[EvidenceGapItem] = [
        EvidenceGapItem(
            missing_item="Unit-level condition proof (inside tenant's specific apartment)",
            why_it_matters=(
                "Municipal 311 records are redacted to the 100-block and corroborate building/block "
                "context only — housing court and escrow defenses require unit-specific evidence."
            ),
            safe_next_step=(
                "Capture dated, unedited photos/videos from a safe, dry distance (e.g., indoor "
                "thermometer reading next to cold radiator, ceiling leak stain — NEVER touch wet "
                "fuse/breaker boxes or exposed wiring)."
            ),
            priority="immediate",
        ),
        EvidenceGapItem(
            missing_item="Complete written eviction / 3-day notice & delivery envelope",
            why_it_matters=(
                "Supervising attorney must inspect exact statutory notice wording, claimed rent "
                "amount, service method, and court answer/hearing deadline."
            ),
            safe_next_step=(
                "Bring or photograph every page of the notice, court summons, and mailing envelope."
            ),
            priority="immediate",
        ),
        EvidenceGapItem(
            missing_item="Prior landlord / property manager repair requests",
            why_it_matters=(
                "Establishes landlord actual/written notice date for implied warranty of habitability "
                "and 180-day statutory anti-retaliation protections."
            ),
            safe_next_step=(
                "Export dated screenshots of texts, emails, portal tickets, or call logs without "
                "altering timestamps; avoid confrontational in-person disputes."
            ),
            priority="high",
        ),
    ]

    if not has_open_311 and (
        categories
        & {
            "heating_loss",
            "electrical_water_hazard",
            "water_intrusion_leak",
            "mold_dampness",
            "plumbing_sewage",
            "pest_infestation",
        }
    ):
        gaps.insert(
            1,
            EvidenceGapItem(
                missing_item="Active municipal 311 / code-enforcement residential case number",
                why_it_matters=(
                    "No open residential 311 record matched near this block (which does NOT mean no "
                    "hazard exists), and two local stabilization grants require `requires_open_habitability_case = TRUE`."
                ),
                safe_next_step=(
                    "Use ShelterWise's 311 Inspection Drafter to submit an official residential "
                    "inspection request today while applying immediately to general arrears funds "
                    "(`requires_open_habitability_case = FALSE`)."
                ),
                priority="immediate",
            ),
        )

    gaps.append(
        EvidenceGapItem(
            missing_item="Residential lease / rent ledger & household income proof",
            why_it_matters="Required by emergency rental stabilization administrators to confirm tenancy and AMI eligibility.",
            safe_next_step="Gather lease, recent rent receipts/venmo/money-order stubs, and recent paystubs or benefits letter.",
            priority="standard",
        )
    )
    return gaps


def _render_brief_markdown(brief: StabilizationBrief) -> str:
    """Format the 9-section Tenant Stabilization Brief per `docs/TENANT_STABILIZATION_BRIEF.md`."""
    lines: list[str] = [
        f"# Tenant Stabilization Brief — `{brief.case_ref}`",
        "",
        f"> **{brief.human_review_notice}**",
        "",
    ]
    if brief.immediate_safety_alert.immediate_danger:
        lines.extend(
            [
                f"> **IMMEDIATE LIFE-SAFETY FLAG:** {brief.immediate_safety_alert.emergency_guidance}",
                f"> **Emergency Contacts:** {' · '.join(brief.immediate_safety_alert.local_emergency_contacts)}",
                "",
            ]
        )

    lines.extend(
        [
            "## 1. Case snapshot",
            f"- **Case reference (non-identifying):** `{brief.case_ref}`",
            f"- **Metro / jurisdiction:** {brief.metro} ({brief.jurisdiction})",
            f"- **Date prepared:** {brief.prepared_date}",
            f"- **Main concern:** {brief.main_concern}",
            f"- **Time-sensitive dates (tenant-reported; verify):** {brief.time_sensitive_dates} (`{brief.urgency_tier}`)",
            f"- **Immediate safety flag:** {'YES — Immediate Escalation' if brief.immediate_safety_alert.immediate_danger else 'No acute physical emergency detected'}",
            "",
            "## 2. Tenant-reported situation",
            f"{brief.tenant_reported_summary}",
            "",
        ]
    )
    for rf in brief.reported_facts:
        lines.append(f"- {rf}")
    lines.append("")

    lines.append("## 3. Evidence found (100-block public records & neighborhood context)")
    if brief.corroborating_311_records:
        for rec in brief.corroborating_311_records:
            lines.extend(
                [
                    f"### `{rec.request_id}` — {rec.raw_complaint_type} ({rec.block_address})",
                    f"- **Evidence label:** {rec.evidence_label}",
                    f"- **Source / agency:** {rec.jurisdiction or rec.metro_area} ({rec.agency_code or '311'}) · `{rec.data_provenance}`",
                    f"- **Created / status:** `{rec.created_date or 'N/A'}` · **{rec.inspection_status}** (`closed_date=NULL`)",
                    f"- **Location precision:** 100-block coarsened (`{rec.block_address}`, Tract `{rec.census_tract_geoid}`, `{rec.geography_match_level}`)",
                    f"- **Semantic match:** similarity `{rec.similarity_score:.2f}` (cosine distance `{rec.cosine_distance:.4f}`)",
                    f"- **Narrative:** {rec.complaint_narrative}",
                    f"- **What this does NOT establish:** {rec.what_it_does_not_establish}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "- **No matching open residential 311 record found.** Absence of a public 311 record does **not** disprove the tenant's reported conditions; many households face retaliation or access barriers to calling inspectors.",
                "",
            ]
        )

    if brief.excluded_311_decoys:
        lines.append("### Excluded near-miss 311 candidates (post-vector eligibility filter)")
        for ex in brief.excluded_311_decoys[:5]:
            lines.append(
                f"- **`{ex.request_id}`** (`{ex.property_type}`, `{ex.inspection_status}`, pre-filter rank #{ex.semantic_rank_before_filter}, distance `{ex.cosine_distance:.4f}`): {ex.exclusion_reason}"
            )
        lines.append("")

    if brief.tract_context and brief.metro_baseline:
        tc = brief.tract_context
        mb = brief.metro_baseline
        lines.extend(
            [
                f"### Census Tract Context — `{tc.census_tract_geoid}` ({tc.county_name})",
                f"- **Severe rent burden (`50%+`):** `{tc.severe_rent_burden_pct}%` across `{tc.renter_occupied_units:,}` renter units (vs. `{mb.metro_severe_rent_burden_pct}%` {mb.metro_area} baseline) — *Real US Census ACS 5-Year*",
                f"- **Annual modeled eviction filings (4 quarters pre-aggregated, no 4x fan-out):** `{tc.annual_filings_total}` filings / `{tc.annual_defaults_total}` defaults (vs. `{mb.metro_median_tract_annual_filings}` metro tract median) — **`[Modeled]` baseline, NOT a personal court docket**",
                f"- **Open real residential 311 count in tract:** `{tc.open_residential_311_count}` {'(Silent-distress candidate: high rent burden with <=1 open 311)' if tc.is_silent_distress_candidate else ''}",
                "",
            ]
        )

    lines.append("## 4. Legal information to review")
    for st in brief.legal_statutes_to_review:
        lines.extend(
            [
                f"- **{st.code_citation} — {st.ordinance_title}** ({st.jurisdiction} · `{st.data_provenance}`)",
                f"  - *Summary:* {st.plain_language_summary}",
                f"  - *Pre-hearing note:* {st.pre_hearing_relevance_note}",
                f"  - *Conditions to confirm:* {st.applicability_conditions}",
            ]
        )
    lines.append("")

    lines.append("## 5. Potential assistance and referrals")
    for prog in brief.evaluated_relief_programs:
        lines.extend(
            [
                f"{prog.priority_rank}. **{prog.program_name}** (`{prog.bulletin_id}` · {prog.administering_agency})",
                f"   - **Screening status:** `{prog.screening_fit}` (`requires_open_habitability_case={prog.requires_open_habitability_case}`)",
                f"   - **Rationale:** {prog.fit_rationale}",
                f"   - **Intake link:** {prog.intake_url} (Effective `{prog.effective_date}`)",
            ]
        )
    lines.append("")

    lines.extend(
        [
            "## 6. Evidence gaps",
            "| Missing item | Why it matters | Safe next step |",
            "|---|---|---|",
        ]
    )
    for g in brief.evidence_gaps:
        lines.append(f"| {g.missing_item} | {g.why_it_matters} | {g.safe_next_step} |")
    lines.append("")

    lines.append("## 7. Suggested next steps (ordered by urgency)")
    for idx, step_txt in enumerate(brief.suggested_next_steps, start=1):
        lines.append(f"{idx}. {step_txt}")
    lines.append("")

    lines.append("## 8. Uncertainty and limitations")
    for lim in brief.uncertainty_and_limitations:
        lines.append(f"- {lim}")
    lines.append("")

    lines.append("## 9. Reviewer checklist")
    for chk in brief.reviewer_checklist:
        mark = "x" if chk.checked else " "
        lines.append(f"- [{mark}] {chk.label}")

    return "\n".join(lines)


def reconcile_relief_and_gaps(
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Cross-checks relief program rules against 311 evidence and identifies evidence gaps.

    Reads `intake_facts`, `evidence_pack`, and `raw_policy_pack` from ADK session state,
    deterministically gates `requires_open_habitability_case = TRUE` programs on whether
    open residential 311 corroboration exists, and generates safe unit-level evidence gaps.

    Returns:
        Dictionary with 'evaluated_relief_programs', 'evidence_gaps', and 'has_open_residential_311'.
    """
    if tool_context is None or not hasattr(tool_context, "state"):
        return {
            "status": "error",
            "error_message": "ToolContext session state is required for reconcile_relief_and_gaps.",
        }

    intake_facts = tool_context.state.get("intake_facts") or {}
    evidence_pack = tool_context.state.get("evidence_pack") or {}
    policy_pack = tool_context.state.get("raw_policy_pack") or {}

    corroborating = evidence_pack.get("corroborating_records") or []
    bulletins = policy_pack.get("relief_bulletins") or []
    urg: UrgencyTier = intake_facts.get("urgency_tier") or "unspecified"

    evaluated_programs = evaluate_relief_programs_deterministic(
        bulletins=bulletins,
        corroborating_records=corroborating,
        urgency_tier=urg,
    )
    gaps = build_evidence_gaps_deterministic(
        intake_facts=intake_facts, corroborating_records=corroborating
    )

    reconciled = {
        "status": "success",
        "has_open_residential_311": len(corroborating) > 0,
        "evaluated_relief_programs": [p.model_dump() for p in evaluated_programs],
        "evidence_gaps": [g.model_dump() for g in gaps],
    }
    assert_no_audit_columns(reconciled)
    tool_context.state["reconciled_eligibility"] = reconciled
    return reconciled


def generate_stabilization_brief(
    reviewer_notes: str = "",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Compiles the 9-section Tenant Stabilization Brief (JSON + Markdown) for human review.

    Synthesizes `intake_facts`, `evidence_pack`, `raw_policy_pack`, `tract_context`, and
    `reconciled_eligibility` from ADK session state, stamps every item with explicit source
    provenance, and optionally persists the draft to Firestore if configured.

    Args:
        reviewer_notes: Optional paralegal intake note to append to limitations/context.

    Returns:
        Dictionary with 'status': 'success', 'stabilization_brief' (typed dict), and 'brief_markdown'.
    """
    if tool_context is None or not hasattr(tool_context, "state"):
        return {
            "status": "error",
            "error_message": "ToolContext session state is required to generate brief.",
        }

    intake_facts = tool_context.state.get("intake_facts") or {}
    if not intake_facts:
        return {
            "status": "error",
            "error_message": "Missing intake_facts in session state; run structure_intake first.",
        }

    evidence_pack = tool_context.state.get("evidence_pack") or {}
    policy_pack = tool_context.state.get("raw_policy_pack") or {}
    tract_pack = tool_context.state.get("tract_context") or {}
    reconciled = tool_context.state.get("reconciled_eligibility")
    if not reconciled:
        reconciled = reconcile_relief_and_gaps(tool_context=tool_context)

    metro = str(intake_facts.get("metro") or "San Francisco")
    meta = get_metro_metadata(metro)
    safety = SafetyAlert(**(intake_facts.get("safety_alert") or {}))
    urg: UrgencyTier = intake_facts.get("urgency_tier") or "unspecified"

    corroborating = [
        EvidenceRecord(**r) for r in (evidence_pack.get("corroborating_records") or [])
    ]
    excluded = [
        ExcludedCandidate(**e) for e in (evidence_pack.get("excluded_candidates") or [])
    ]
    statutes = [StatuteMatch(**s) for s in (policy_pack.get("statutes") or [])]
    eval_programs = [
        EvaluatedReliefProgram(**p)
        for p in (reconciled.get("evaluated_relief_programs") or [])
    ]
    gaps = [EvidenceGapItem(**g) for g in (reconciled.get("evidence_gaps") or [])]

    tract_ctx = (
        TractDisplacementContext(**tract_pack["tract_context"])
        if tract_pack.get("tract_context")
        else None
    )
    metro_base = (
        MetroDisplacementBaseline(**tract_pack["metro_baseline"])
        if tract_pack.get("metro_baseline")
        else None
    )

    next_steps: list[str] = []
    if safety.immediate_danger:
        next_steps.append(
            f"[EMERGENCY SAFETY FIRST] {safety.emergency_guidance} ({', '.join(safety.local_emergency_contacts[:2])})."
        )
    if urg in ("immediate_72h", "urgent_7d"):
        next_steps.append(
            f"[COURT CLOCK — {urg}] Escalate intake brief immediately to supervising right-to-counsel attorney ahead of {intake_facts.get('hearing_or_deadline_date') or 'imminent hearing'}."
        )
    if eval_programs:
        top_prog = eval_programs[0]
        next_steps.append(
            f"[PRIMARY RELIEF REFERRAL] Screen household for {top_prog.program_name} ({top_prog.administering_agency} — {top_prog.intake_url})."
        )
    if not corroborating:
        next_steps.append(
            "[OPEN 311 CORROBORATION] Submit official residential 311/DBI inspection request today to document active hazards and unlock habitability-gated grants."
        )
    next_steps.append(
        "[UNIT DOCUMENTATION] Assist tenant in safely preserving dated unit photos, written eviction notice, and landlord text/email repair requests."
    )

    limitations = [
        "100-Block Evidentiary Boundary: Municipal 311 complaints corroborate neighborhood/block-area conditions only and NEVER prove conditions inside an individual dwelling unit.",
        "Modeled Eviction Counts: Census housing tenure (`acs_tract_housing_tenure`) and real 311 records are public records, whereas `court_eviction_filings` is `[Modeled]` across 4 pre-aggregated quarters (Princeton Eviction Lab has zero California coverage) — never cite as a live personal court docket.",
        "Program & Statutory Review: Relief funds (`[Curated Benchmark]`) and statutory summaries (`[Public Legal Reference]`) require live confirmation of current funding caps, AMI thresholds, and procedural deadlines by a qualified human reviewer.",
    ]
    if reviewer_notes.strip():
        limitations.append(f"Paralegal Intake Note: {reviewer_notes.strip()}")

    checklist = [
        ReviewerChecklistItem(
            item_id="chk_facts", label="Tenant-reported facts and timeline confirmed directly with tenant."
        ),
        ReviewerChecklistItem(
            item_id="chk_geo", label="100-block 311 records verified for building/geography context (not treated as unit proof)."
        ),
        ReviewerChecklistItem(
            item_id="chk_law", label="Applicable statutes, notice validity, and court hearing/answer deadlines checked by attorney."
        ),
        ReviewerChecklistItem(
            item_id="chk_relief", label="Emergency stabilization program funding status, AMI cap, and required documents verified."
        ),
        ReviewerChecklistItem(
            item_id="chk_safety", label="Immediate life-safety hazards (electrical/water/gas/heat) escalated appropriately."
        ),
        ReviewerChecklistItem(
            item_id="chk_signoff", label="Brief approved by qualified paralegal/advocate/attorney before external use."
        ),
    ]

    categories_str = ", ".join(intake_facts.get("issue_categories") or ["housing instability"])
    deadline_str = (
        intake_facts.get("hearing_or_deadline_date")
        or ("Imminent hearing/notice reported (date unconfirmed)" if urg == "immediate_72h" else "Not specified — confirm notice dates")
    )

    brief_model = StabilizationBrief(
        case_ref=str(intake_facts.get("case_ref") or "SW-DRAFT"),
        metro=metro,
        jurisdiction=f"{metro}, {meta['state_code']}",
        prepared_date=str(intake_facts.get("prepared_date") or ""),
        main_concern=categories_str,
        time_sensitive_dates=deadline_str,
        urgency_tier=urg,
        immediate_safety_alert=safety,
        tenant_reported_summary=(
            f"Tenant/advocate reported account (unverified until unit documentation is reviewed): "
            f"{intake_facts.get('scrubbed_narrative') or intake_facts.get('raw_tenant_narrative')}"
        ),
        reported_facts=list(intake_facts.get("reported_facts") or []),
        corroborating_311_records=corroborating,
        excluded_311_decoys=excluded,
        tract_context=tract_ctx,
        metro_baseline=metro_base,
        legal_statutes_to_review=statutes,
        evaluated_relief_programs=eval_programs,
        evidence_gaps=gaps,
        suggested_next_steps=next_steps,
        uncertainty_and_limitations=limitations,
        reviewer_checklist=checklist,
    )
    brief_model.brief_markdown = _render_brief_markdown(brief_model)

    brief_dict = brief_model.model_dump()
    assert_no_audit_columns(brief_dict)
    tool_context.state["stabilization_brief"] = brief_dict

    # Non-blocking hook for Member 4's Firestore store once merged (`firestore_store.py`)
    persisted_to_firestore = False
    try:
        from ..db import firestore_store  # type: ignore[attr-defined]

        if hasattr(firestore_store, "save_case_brief"):
            firestore_store.save_case_brief(brief_model.case_ref, brief_dict)
            persisted_to_firestore = True
    except Exception:
        persisted_to_firestore = False

    return {
        "status": "success",
        "case_ref": brief_model.case_ref,
        "persisted_to_firestore": persisted_to_firestore,
        "stabilization_brief": brief_dict,
        "brief_markdown": brief_model.brief_markdown,
    }


def reconcile_gaps_and_generate_brief(
    reviewer_notes: str = "",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """One-step tool combining `reconcile_relief_and_gaps` + `generate_stabilization_brief`.

    Args:
        reviewer_notes: Optional paralegal intake note to include in the brief.

    Returns:
        Dictionary with 'stabilization_brief' (JSON) and 'brief_markdown'.
    """
    rec = reconcile_relief_and_gaps(tool_context=tool_context)
    if rec.get("status") == "error":
        return rec
    return generate_stabilization_brief(
        reviewer_notes=reviewer_notes, tool_context=tool_context
    )
