"""Canonical Pydantic v2 JSON contracts shared across all 6 ShelterWise lanes.

Every runtime case tool validates its output through these models AND runs
`assert_no_audit_columns()` to guarantee protected demographic `audit_*` shares
never enter individual household triage, ranking, or prompts.
"""

from typing import Any, Literal
from pydantic import BaseModel as _PydanticBaseModel, Field

try:
    from pydantic import ConfigDict, field_validator  # Pydantic v2 (used by google-adk)

    _PYDANTIC_V2 = True
except ImportError:  # Fallback if a teammate runs older local Conda Pydantic v1
    from pydantic import validator as _v1_validator  # type: ignore[assignment]

    _PYDANTIC_V2 = False
    ConfigDict = None  # type: ignore[assignment]

    def field_validator(field_name: str):  # type: ignore[no-redef]
        return _v1_validator(field_name, allow_reuse=True)


class _ShelterWiseModel(_PydanticBaseModel):
    """Base schema supporting Pydantic v2 (`model_dump`) cleanly across environments."""

    if _PYDANTIC_V2:
        model_config = ConfigDict(extra="forbid")
    else:

        class Config:
            extra = "forbid"

        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return self.dict(**kwargs)

from .config import AUDIT_FORBIDDEN_COLUMNS, normalize_geoid_11

UrgencyTier = Literal["immediate_72h", "urgent_7d", "standard_30d", "unspecified"]

ScreeningFit = Literal[
    "eligible_to_screen",
    "conditional_needs_open_311_case",
    "ineligible_non_residential",
    "needs_human_review",
]

ExclusionCode = Literal[
    "non_residential_property",
    "closed_or_abated_case",
    "no_violation_inspection",
    "wrong_jurisdiction",
    "duplicate_record",
]


def assert_no_audit_columns(payload: Any, path: str = "root") -> None:
    """Recursively verify that zero `audit_*` demographic keys exist in a case payload."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            key_str = str(k).lower()
            if key_str in AUDIT_FORBIDDEN_COLUMNS or key_str.startswith("audit_"):
                raise ValueError(
                    f"Responsible-AI firewall violation: forbidden field {k!r} found at {path}.{k}"
                )
            assert_no_audit_columns(v, f"{path}.{k}")
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            assert_no_audit_columns(item, f"{path}[{idx}]")


class SafetyAlert(_ShelterWiseModel):

    immediate_danger: bool = False
    triggered_signals: list[str] = Field(default_factory=list)
    emergency_guidance: str = ""
    local_emergency_contacts: list[str] = Field(default_factory=list)


class IntakeFacts(_ShelterWiseModel):
    """Structured output of Tool 1 (`structure_intake`)."""

    case_ref: str
    metro: str
    state_code: str
    state_fips: str
    prepared_date: str
    raw_tenant_narrative: str = Field(
        description="Original tenant/advocate statement preserved verbatim as reported."
    )
    scrubbed_narrative: str = Field(
        description="PII-redacted narrative safe for BigQuery AI.EMBED and telemetry."
    )
    semantic_search_query: str = Field(
        description="Targeted habitability search string passed to AI.EMBED(gemini-embedding-2)."
    )
    reported_facts: list[str] = Field(default_factory=list)
    issue_categories: list[str] = Field(default_factory=list)
    block_address_hint: str = ""
    census_tract_geoid: str = ""
    has_written_notice: bool = False
    hearing_or_deadline_date: str = ""
    urgency_tier: UrgencyTier = "unspecified"
    safety_alert: SafetyAlert = Field(default_factory=SafetyAlert)
    unknowns: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)

    @field_validator("census_tract_geoid")
    @classmethod
    def _validate_geoid(cls, v: str) -> str:
        return normalize_geoid_11(v) if v else ""


class EvidenceQuery(_ShelterWiseModel):
    """Query metadata recorded for `search_public_evidence`."""

    metro: str
    semantic_query: str
    census_tract_geoid: str = ""
    block_address_hint: str = ""
    top_k_scanned: int = 25
    embedding_model: str = "gemini-embedding-2"
    vector_search_options: str = '{"use_brute_force":true}'


class EvidenceRecord(_ShelterWiseModel):
    """Eligible open residential 311 habitability record corroborating block context."""

    evidence_label: str = "Public-record match (100-block context — NOT unit proof)"
    request_id: str
    state_code: str
    metro_area: str
    jurisdiction: str = ""
    agency_code: str = ""
    block_address: str
    census_tract_geoid: str
    property_type: str
    raw_complaint_type: str
    inspection_status: str
    created_date: str = ""
    closed_date: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cosine_distance: float
    similarity_score: float
    semantic_rank_before_filter: int
    geography_match_level: Literal[
        "same_100_block", "same_census_tract", "metro_corridor_semantic_match"
    ]
    matched_fields: list[str] = Field(default_factory=list)
    complaint_narrative: str
    inclusion_rationale: str
    what_it_does_not_establish: str = (
        "Coarsened to the 100-block level. Corroborates building/block-area conditions only; "
        "does NOT establish conditions inside the tenant's individual apartment unit."
    )
    data_provenance: str
    source_portal_url: str = ""

    @field_validator("census_tract_geoid")
    @classmethod
    def _validate_geoid(cls, v: str) -> str:
        return normalize_geoid_11(v)


class ExcludedCandidate(_ShelterWiseModel):
    """Near-miss 311 record (including planted DECOY-* traps) rejected by business rules."""

    request_id: str
    block_address: str
    census_tract_geoid: str = ""
    property_type: str
    raw_complaint_type: str = ""
    inspection_status: str
    created_date: str = ""
    closed_date: str | None = None
    cosine_distance: float
    similarity_score: float
    semantic_rank_before_filter: int
    exclusion_code: ExclusionCode
    exclusion_reason: str
    complaint_narrative_excerpt: str = ""
    data_provenance: str = ""


class EvidenceSearchResult(_ShelterWiseModel):
    """Structured output of Tool 2 (`search_public_evidence`)."""

    status: Literal["success", "error"] = "success"
    backend_mode: Literal["bigquery_live", "offline_sf_fixture"]
    evidence_status: Literal[
        "corroborating_records_found", "no_matching_open_residential_record"
    ]
    has_open_residential_311: bool
    inferred_tract_geoid: str = ""
    query: EvidenceQuery
    corroborating_records: list[EvidenceRecord] = Field(default_factory=list)
    excluded_candidates: list[ExcludedCandidate] = Field(default_factory=list)
    exclusion_summary_counts: dict[str, int] = Field(default_factory=dict)
    evidentiary_boundary_notice: str = (
        "Public 311 records are redacted to the 100-block and corroborate neighborhood/block "
        "context only; they never prove conditions inside an individual dwelling unit. "
        "Conversely, absence of an open 311 record is NOT proof that no habitability defect exists."
    )


class StatuteMatch(_ShelterWiseModel):
    """Statutory reference from `municipal_housing_ordinance_statutes`."""

    evidence_label: str = "Official legal reference (requires attorney/paralegal review)"
    statute_section_id: str
    state_code: str
    metro_area: str
    jurisdiction: str
    code_citation: str
    ordinance_title: str
    plain_language_summary: str
    raw_statute_text: str
    matched_topics: list[str] = Field(default_factory=list)
    pre_hearing_relevance_note: str = ""
    applicability_conditions: str
    reviewer_questions: list[str] = Field(default_factory=list)
    data_provenance: str


class ReliefProgramBulletin(_ShelterWiseModel):
    """Raw/annotated emergency relief bulletin from `rental_relief_program_bulletins`."""

    bulletin_id: str
    state_code: str
    metro_area: str
    service_region: str
    program_name: str
    administering_agency: str
    funding_stream: str
    requires_open_habitability_case: bool
    residential_tenants_only: bool
    raw_bulletin_text: str
    intake_url: str
    effective_date: str
    data_provenance: str


class PolicyLookupResult(_ShelterWiseModel):
    """Structured output of Tool 3 (`fetch_statutes_and_bulletins`)."""

    status: Literal["success", "error"] = "success"
    backend_mode: Literal["bigquery_live", "offline_sf_fixture"]
    metro: str
    urgency_tier: UrgencyTier = "unspecified"
    statutes: list[StatuteMatch] = Field(default_factory=list)
    relief_bulletins: list[ReliefProgramBulletin] = Field(default_factory=list)
    legal_disclaimer: str = (
        "Statutory and program summaries support internal paralegal/coordinator triage only "
        "and do NOT constitute legal advice or a binding eligibility determination."
    )


class MetroDisplacementBaseline(_ShelterWiseModel):
    """Metro-wide aggregate comparison stats (zero `audit_*` fields)."""

    metro_area: str
    tract_count: int
    total_renter_occupied_units: int
    metro_severe_rent_burden_pct: float
    metro_median_gross_rent: float
    metro_annual_modeled_filings_total: int
    metro_median_tract_annual_filings: float
    metro_open_residential_311_total: int


class TractDisplacementContext(_ShelterWiseModel):
    """Fan-out-safe tract displacement context (4 quarters pre-aggregated, zero `audit_*`)."""

    evidence_label: str = (
        "Contextual tract statistic (ACS real + [Modeled] 4Q filings — NOT individual court docket)"
    )
    census_tract_geoid: str
    resolution_method: Literal[
        "explicit_geoid", "inferred_from_block_311", "metro_top_hotspot_fallback"
    ]
    county_name: str
    metro_area: str
    renter_occupied_units: int
    median_household_income: float
    median_gross_rent: float
    moderate_rent_burden_30_49_count: int
    severe_rent_burden_50_plus_count: int
    severe_rent_burden_pct: float
    poverty_pct: float
    no_vehicle_pct: float
    annual_nonpayment_filings: int
    annual_no_fault_filings: int
    annual_filings_total: int
    annual_defaults_total: int
    avg_claimed_arrears_usd: float
    open_residential_311_count: int
    tract_vs_metro_rent_burden_ratio: float
    tract_vs_metro_filings_ratio: float
    is_silent_distress_candidate: bool
    tract_lat: float | None = None
    tract_lon: float | None = None
    acs_provenance: str
    filings_provenance: str
    provenance_caveat: str = (
        "ACS housing tenure & severe rent burden are real US Census 5-Year estimates. "
        "Quarterly eviction filings are [Modeled] across 4 pre-aggregated quarters (2025-Q3..2026-Q2) "
        "because Princeton Eviction Lab lacks California tract coverage — never present as a live personal court docket."
    )

    @field_validator("census_tract_geoid")
    @classmethod
    def _validate_geoid(cls, v: str) -> str:
        return normalize_geoid_11(v)


class TractContextResult(_ShelterWiseModel):
    """Structured output of Tool 4 (`get_tract_displacement_baseline`)."""

    status: Literal["success", "error"] = "success"
    backend_mode: Literal["bigquery_live", "offline_sf_fixture"]
    tract_context: TractDisplacementContext
    metro_baseline: MetroDisplacementBaseline


class EvaluatedReliefProgram(_ShelterWiseModel):
    """Relief program after cross-checking `requires_open_habitability_case` against 311 proof."""

    bulletin_id: str
    program_name: str
    administering_agency: str
    funding_stream: str
    requires_open_habitability_case: bool
    residential_tenants_only: bool
    screening_fit: ScreeningFit
    priority_rank: int
    fit_rationale: str
    required_documents_to_confirm: list[str] = Field(default_factory=list)
    intake_url: str
    effective_date: str
    human_verification_needed: str = (
        "Confirm live program funding availability, household AMI threshold, and lease/arrears ledger."
    )
    data_provenance: str


class EvidenceGapItem(_ShelterWiseModel):
    """Missing unit-level or procedural evidence and safe collection guidance."""

    missing_item: str
    why_it_matters: str
    safe_next_step: str
    priority: Literal["immediate", "high", "standard"] = "high"


class ReviewerChecklistItem(_ShelterWiseModel):
    """Human review gate item matching `docs/TENANT_STABILIZATION_BRIEF.md` Section 9."""

    item_id: str
    label: str
    checked: bool = False


class StabilizationBrief(_ShelterWiseModel):
    """9-Section Tenant Stabilization Brief matching `docs/TENANT_STABILIZATION_BRIEF.md`."""

    # Section 1: Case snapshot
    case_ref: str
    metro: str
    jurisdiction: str
    prepared_date: str
    main_concern: str
    time_sensitive_dates: str
    urgency_tier: UrgencyTier
    immediate_safety_alert: SafetyAlert

    # Section 2: Tenant-reported situation
    tenant_reported_summary: str
    reported_facts: list[str]

    # Section 3: Public evidence found + excluded decoys + tract context
    corroborating_311_records: list[EvidenceRecord]
    excluded_311_decoys: list[ExcludedCandidate]
    tract_context: TractDisplacementContext | None = None
    metro_baseline: MetroDisplacementBaseline | None = None

    # Section 4: Legal information to review
    legal_statutes_to_review: list[StatuteMatch]

    # Section 5: Potential assistance and referrals
    evaluated_relief_programs: list[EvaluatedReliefProgram]

    # Section 6: Evidence gaps
    evidence_gaps: list[EvidenceGapItem]

    # Section 7: Suggested next steps (urgency ordered)
    suggested_next_steps: list[str]

    # Section 8: Uncertainty, provenance & evidentiary boundaries
    uncertainty_and_limitations: list[str]

    # Section 9: Reviewer checklist & disclaimer
    reviewer_checklist: list[ReviewerChecklistItem]
    human_review_notice: str = (
        "DRAFT FOR QUALIFIED PARALEGAL / ADVOCATE / ATTORNEY REVIEW ONLY. "
        "ShelterWise is an intake corroboration aid, not legal advice and not an automated eligibility determination."
    )
    brief_markdown: str = ""


# ---------------------------------------------------------------------------
# Shared Contracts for Member 4 (Firestore, Bonus Tools, FastAPI) & Member 5 (UI)
# ---------------------------------------------------------------------------


class Draft311InspectionPacket(_ShelterWiseModel):
    """Contract for Bonus Tool 6 (`draft_311_inspection_request`)."""

    metro: str
    target_agency: str
    recommended_complaint_category: str
    block_location: str
    structured_311_summary: str
    safe_photo_checklist: list[str]
    interim_general_funds: list[str]
    retaliation_protection_note: str


class CaseLockState(_ShelterWiseModel):
    """Contract for Firestore optimistic concurrency (`claim_or_update_case_task`)."""

    case_ref: str
    assigned_paralegal: str
    workflow_status: Literal["intake", "in_review", "attorney_ready", "closed"] = "in_review"
    lock_version: int = 1
    updated_at_iso: str
    checklist_overrides: dict[str, bool] = Field(default_factory=dict)


class CourthouseTransitEstimate(_ShelterWiseModel):
    """Contract for Bonus Tool (`estimate_courthouse_transit`)."""

    metro: str
    courthouse_name: str
    origin_label: str
    straight_line_miles: float
    estimated_transit_minutes: int
    recommended_departure_before_9am: str
    accessibility_note: str


class MetroEquityCohortRow(_ShelterWiseModel):
    """Strictly post-output cohort comparison row for `equity_audit_agent` ONLY."""

    cohort_name: str
    tract_count: int
    renter_units: int
    avg_severe_rent_burden_pct: float
    total_annual_modeled_filings: int
    avg_no_vehicle_pct: float
    audit_black_pct: float
    audit_hispanic_pct: float
    audit_asian_pct: float
    audit_indigenous_pct: float
    audit_white_pct: float


class MetroEquityAuditResult(_ShelterWiseModel):
    """Post-output Metro Equity Audit report (isolated to `equity_audit_agent`)."""

    metro: str
    methodology_note: str
    cohorts: list[MetroEquityCohortRow]
    silent_distress_tract_geoids: list[str]
    operational_recommendations: list[str]
