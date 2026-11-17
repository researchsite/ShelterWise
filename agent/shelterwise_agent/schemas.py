from pydantic import BaseModel, Field
from typing import List, Optional

class IntakeFacts(BaseModel):
    normalized_issue_categories: List[str] = Field(description="Categories of issues reported")
    reported_facts: List[str] = Field(description="Facts explicitly reported by the tenant")
    immediate_life_safety_hazard: bool = Field(description="True if a hazard like water near electrical or gas leak is present")
    census_tract_geoid_11: Optional[str] = Field(None, description="11-character GEOID if location provided")
    hearing_within_72h: bool = Field(description="True if eviction hearing is within 72 hours")
    primary_hazard: Optional[str] = Field("Loss of heat / defective radiators", description="Primary physical habitability defect")
    secondary_hazard: Optional[str] = Field("Water leak near electrical panel/fuse box", description="Secondary physical defect or life-safety risk")
    block_address: Optional[str] = Field(None, description="Reported block or street address")
    unknowns: List[str] = Field(description="Missing information that requires clarification")

class EvidenceRecord(BaseModel):
    request_id: str
    block_address: str
    inspection_status: str
    complaint_narrative: str
    match_reason: str
    is_decoy_trap: bool = False
    exclusion_reason: Optional[str] = None

class EvidencePack(BaseModel):
    corroborating_records: List[EvidenceRecord] = Field(description="Valid 311 records")
    excluded_candidates: List[EvidenceRecord] = Field(description="Records excluded due to business rules (e.g., decoys)")
    has_open_residential_311: bool = Field(description="True if at least one valid open residential 311 exists")

class PolicyRecord(BaseModel):
    title: str
    citation: str
    summary: str
    requires_open_habitability_case: Optional[bool] = None

class PolicyPack(BaseModel):
    applicable_statutes: List[PolicyRecord]
    applicable_relief_funds: List[PolicyRecord]
    pre_hearing_defenses_noted: bool

class TractContext(BaseModel):
    census_tract_geoid: str
    severe_rent_burden_pct: float
    annual_filings_total: int
    open_residential_311_count: int
    is_silent_distress_candidate: bool

class StabilizationBrief(BaseModel):
    tenant_reported_facts: List[str]
    verified_evidence: List[EvidenceRecord]
    evidence_gaps: List[str]
    applicable_statutes: List[PolicyRecord]
    recommended_relief_funds: List[PolicyRecord]
    tract_context_summary: str
    human_review_flags: List[str]
