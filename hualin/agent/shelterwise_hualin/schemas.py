"""Data contracts for every state.* key. The UI renders `state.brief` (Brief)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Hazard = Literal[
    "heat", "hot_water", "water_leak", "electrical", "mold", "sewage",
    "pests", "structural", "gas", "fire", "weatherproofing", "plumbing", "other",
]


# ---- Step 1: LLM output -------------------------------------------------------
class IntakeFacts(BaseModel):
    """What the intake_parser LLM extracts. No names, unit numbers or demographics."""

    address_text: str = Field("", description="Street block only, e.g. '1000 block of Fillmore St'. Never a unit number.")
    hazards: list[Hazard] = Field(default_factory=list)
    hazard_summary: str = Field("", description="One plain-language sentence describing the conditions.")
    search_query: str = Field("", description="The conditions rewritten the way a city building inspector would log them.")
    hearing_date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD of the court hearing, if known.")
    case_type: Literal["nonpayment", "no_fault", "other", "unknown"] = "unknown"
    is_residential_tenant: Optional[bool] = True
    tenant_has_own_dbi_case: Optional[bool] = None
    tenant_complained_to_city: Optional[bool] = None
    household_size: Optional[int] = None
    annual_income_usd: Optional[float] = None
    income_pct_ami: Optional[float] = Field(None, description="Only if stated explicitly, e.g. 'she is at 50% AMI'.")
    medical_or_wage_loss: Optional[bool] = None
    months_behind: Optional[float] = None


# ---- Step 3: evidence -----------------------------------------------------------
ExclusionReason = Literal[
    "not_residential", "closed_abated", "closed_no_violation", "closed_other",
    "outside_radius", "other_metro",
]


class EvidenceHit(BaseModel):
    request_id: str
    block_address: str
    census_tract_geoid: str
    property_type: str
    raw_complaint_type: str
    inspection_status: str
    created_date: Optional[str]
    closed_date: Optional[str]
    narrative: str
    similarity_rank: int
    cosine_distance: float
    meters_away: Optional[float]


class ExcludedHit(EvidenceHit):
    reasons: list[ExclusionReason]


class EvidenceResult(BaseModel):
    retrieval_mode: str
    search_query: str
    location_known: bool
    radius_m: Optional[float]
    kept: list[EvidenceHit]
    excluded: list[ExcludedHit]
    has_open_residential_nearby: bool


# ---- Step 4: decisions ----------------------------------------------------------
class StatuteFinding(BaseModel):
    statute_section_id: str
    code_citation: str
    ordinance_title: str
    verdict: Literal["APPLIES", "APPLIES_IF", "NOT_YET", "NOT_APPLICABLE"]
    why: str
    key_protection: str
    recheck_on: Optional[str] = None


class ConditionCheck(BaseModel):
    condition: str
    status: Literal["met", "not_met", "unknown"]
    detail: str


class ReliefVerdict(BaseModel):
    bulletin_id: str
    program_name: str
    administering_agency: str
    amount: str
    intake_url: str
    verdict: Literal["ELIGIBLE", "CONDITIONAL", "INELIGIBLE"]
    urgent: bool
    checks: list[ConditionCheck]
    to_confirm: list[str]


# ---- Step 5: LLM output -------------------------------------------------------
class BriefDraft(BaseModel):
    summary: str = Field(description="3-5 plain sentences for the paralegal.")
    memo_markdown: str = Field(description="Intake corroboration memo for the supervising attorney.")
    questions_for_tenant: list[str] = Field(default_factory=list)
