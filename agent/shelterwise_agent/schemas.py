from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IntakeFacts(BaseModel):
    normalized_issue_categories: List[str] = Field(default_factory=list, description="Categories of issues reported (e.g. Heat Loss, Electrical Hazard)")
    reported_facts: List[str] = Field(default_factory=list, description="Explicit tenant statements preserved as reported")
    immediate_life_safety_hazard: bool = Field(default=False, description="True if acute safety risk detected (water near fuse box, gas leak, arcing)")
    safety_alert_message: Optional[str] = Field(default=None, description="Urgent safety instructions if hazard detected")
    census_tract_geoid_11: Optional[str] = Field(default=None, description="11-character GEOID with leading zero preserved ('06075...')")
    block_address: Optional[str] = Field(default=None, description="100-block address coarsened for privacy")
    hearing_within_72h: bool = Field(default=False, description="True if eviction court date is within 72 hours")
    hearing_datetime_str: Optional[str] = Field(default=None, description="Reported date and time of court hearing")
    unknowns: List[str] = Field(default_factory=list, description="Missing case facts that need advocate clarification")
    semantic_search_query: str = Field(default="", description="Rewritten inspector-vocabulary query for vector search")

class EvidenceRecord(BaseModel):
    request_id: str
    block_address: str
    property_type: str = "Residential"
    inspection_status: str
    closed_date: Optional[str] = None
    complaint_narrative: str
    cosine_distance: float = 0.0
    match_strength: str = "Moderate"
    is_decoy_trap: bool = False
    exclusion_reason: Optional[str] = None
    data_provenance: str = "[Real 311 Public Record]"

class EvidencePack(BaseModel):
    corroborating_records: List[EvidenceRecord] = Field(default_factory=list, description="Active residential habitability records")
    excluded_candidates: List[EvidenceRecord] = Field(default_factory=list, description="Excluded decoy records with explanation")
    has_open_residential_311: bool = Field(default=False, description="True if at least one corroborating 311 case exists")
    query_used: str = ""

class PolicyRecord(BaseModel):
    id: str
    title: str
    citation: str
    summary: str
    jurisdiction: str = "San Francisco, CA"
    applies: str = "Yes" # "Yes", "Yes, if", "No"
    application_rationale: str = ""
    requires_open_habitability_case: Optional[bool] = None
    intake_url: Optional[str] = None
    data_provenance: str = "[Public Legal Reference]"

class PolicyPack(BaseModel):
    applicable_statutes: List[PolicyRecord] = Field(default_factory=list)
    applicable_relief_funds: List[PolicyRecord] = Field(default_factory=list)
    repair_clock_days: int = 16
    statutory_deadline_date: str = "2026-12-09"

class TractContext(BaseModel):
    census_tract_geoid: str
    renter_occupied_units: int = 0
    severely_burdened_hh: int = 0
    severe_rent_burden_pct: float = 0.0
    median_gross_rent: int = 0
    median_household_income: int = 0
    annual_filings_total: int = 0
    annual_nonpayment_filings: int = 0
    annual_no_fault_filings: int = 0
    annual_defaults_total: int = 0
    open_residential_311_count: int = 0
    is_silent_distress_candidate: bool = False
    sf_tract_median_burden: float = 16.1
    sf_tract_median_filings: int = 55
    filings_provenance: str = "[Modeled Court Baseline]"
    acs_provenance: str = "[Real Census ACS 2018-2022]"

class EvidenceGapItem(BaseModel):
    missing_item: str
    why_it_matters: str
    safe_next_step: str

class StabilizationBrief(BaseModel):
    case_id: str
    intake_date: str
    hearing_date: str
    urgency_level: str
    location_summary: str
    tenant_reported_facts: List[str]
    verified_evidence: List[EvidenceRecord]
    excluded_lookalikes: List[EvidenceRecord]
    applicable_statutes: List[PolicyRecord]
    recommended_relief_funds: List[PolicyRecord]
    evidence_gaps: List[EvidenceGapItem]
    suggested_next_steps: List[str]
    uncertainty_and_limitations: List[str]
    reviewer_checklist: List[str]
    brief_markdown: str

class CaseTaskLock(BaseModel):
    case_id: str
    assigned_paralegal: str
    status: str = "open"
    lock_version: int = 1
    updated_at: str = ""

class TransitEstimate(BaseModel):
    destination: str
    origin_block: str
    distance_miles: float
    estimated_transit_minutes: int
    recommended_departure: str
    feasible_before_9am: bool
    transit_routes: List[str]
