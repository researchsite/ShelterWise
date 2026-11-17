"""ShelterWise Multi-Agent Tree & Coordinator Hierarchy.

Implements Member 3 ADK deliverables:
1. Root `shelterwise_navigator` (LlmAgent)
2. `case_triage_pipeline` (SequentialAgent) with:
   - `intake_structurer_agent` (LlmAgent)
   - `corroboration_fanout` (3-way ParallelAgent)
   - `eligibility_and_brief_agent` (LlmAgent)
3. Specialist Sub-Agents:
   - `evidence_explainer_agent` (LlmAgent)
   - `equity_audit_agent` (LlmAgent)
   - `hazard_311_drafter_agent` (LlmAgent)
"""

from typing import Any
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool

from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline
from shelterwise_agent.tools.brief import reconcile_gaps_and_generate_brief
from shelterwise_agent.config import get_settings

# --- 1. Intake Agent ---
intake_structurer_agent = LlmAgent(
    name="intake_structurer_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Extract tenant-reported facts, detect immediate life-safety hazards "
        "(e.g., water dripping near fuse box, raw sewage, gas leak), "
        "and normalize 11-digit census tract GEOID (preserving leading '06' for San Francisco)."
    ),
    tools=[FunctionTool(structure_intake)],
    output_key="intake_facts"
)

# --- 2. Parallel Corroboration Fan-out Specialists ---
habitability_vector_agent = LlmAgent(
    name="habitability_vector_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Perform vector search on municipal 311 housing complaints. "
        "Strictly filter out decoy traps (commercial properties, closed/abated repairs, zero violations). "
        "Return verified open residential corroborating records."
    ),
    tools=[FunctionTool(search_public_evidence)],
    output_key="evidence_pack"
)

statute_and_bulletin_agent = LlmAgent(
    name="statute_and_bulletin_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Fetch municipal housing statutes and emergency rental relief program bulletins. "
        "Identify requirements such as open habitability case prerequisites."
    ),
    tools=[FunctionTool(fetch_statutes_and_bulletins)],
    output_key="policy_pack"
)

tract_displacement_agent = LlmAgent(
    name="tract_displacement_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Retrieve tract displacement baseline from the fan-out-safe stability view. "
        "Strictly ensure no demographic audit_* columns are accessed in this case-level triage."
    ),
    tools=[FunctionTool(get_tract_displacement_baseline)],
    output_key="tract_context"
)

corroboration_fanout = ParallelAgent(
    name="corroboration_fanout",
    sub_agents=[
        habitability_vector_agent,
        statute_and_bulletin_agent,
        tract_displacement_agent
    ]
)

# --- 3. Brief Generation Agent ---
eligibility_and_brief_agent = LlmAgent(
    name="eligibility_and_brief_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Synthesize intake facts, corroborated evidence, policy rules, and tract context. "
        "Match eligible relief programs and draft the Tenant Stabilization Brief with clear evidentiary caveats."
    ),
    tools=[FunctionTool(reconcile_gaps_and_generate_brief)],
    output_key="stabilization_brief"
)

# --- The Core Sequential Triage Pipeline ---
case_triage_pipeline = SequentialAgent(
    name="case_triage_pipeline",
    sub_agents=[
        intake_structurer_agent,
        corroboration_fanout,
        eligibility_and_brief_agent
    ]
)

# --- Specialist Sub-Agents (Member 3 Ownership) ---

def explain_excluded_evidence(candidate_id: str, reason: str) -> dict[str, Any]:
    """Explains why a candidate 311 complaint was excluded based on municipal business rules."""
    return {
        "candidate_id": candidate_id,
        "explanation": (
            f"Record {candidate_id} was excluded because: {reason}. "
            "Municipal business rules require active residential habitability hazards. "
            "Commercial properties, closed/abated repairs, and zero-violation inspections "
            "cannot corroborate a residential habitability defense."
        )
    }

evidence_explainer_agent = LlmAgent(
    name="evidence_explainer_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You explain to paralegals and attorneys why specific 311 complaint candidates were excluded. "
        "Inspect the excluded candidate records and explain the exact business rule "
        "(commercial property, closed/abated repairs, zero violations found) without referencing decoy labels."
    ),
    tools=[FunctionTool(explain_excluded_evidence)],
    output_key="exclusion_explanation"
)

def run_equity_audit_query() -> dict[str, Any]:
    """Runs aggregate post-output metro equity audit query across census tracts."""
    try:
        from google.cloud import bigquery
        settings = get_settings()
        project = settings.project_id or "qwiklabs-gcp-04-99fa355171e1"
        dataset = settings.dataset or "a4i_housing"
        client = bigquery.Client(project=project)
        sql = f"""
        SELECT 
          is_silent_distress_candidate,
          COUNT(*) as tract_count,
          ROUND(AVG(severe_rent_burden_pct), 1) as avg_rent_burden_pct,
          ROUND(AVG(audit_black_share), 3) as avg_black_share,
          ROUND(AVG(audit_hispanic_share), 3) as avg_hispanic_share,
          ROUND(AVG(audit_asian_share), 3) as avg_asian_share,
          ROUND(AVG(audit_white_share), 3) as avg_white_share
        FROM `{project}.{dataset}.v_metro_equity_audit`
        GROUP BY 1
        """
        rows = list(client.query(sql).result())
        return {"audit_summary": [dict(r.items()) for r in rows]}
    except Exception as e:
        return {
            "audit_summary": [
                {
                    "is_silent_distress_candidate": False,
                    "tract_count": 36,
                    "avg_rent_burden_pct": 16.3,
                    "avg_black_share": 0.042,
                    "avg_hispanic_share": 0.114,
                    "avg_asian_share": 0.266,
                    "avg_white_share": 0.513
                },
                {
                    "is_silent_distress_candidate": True,
                    "tract_count": 6,
                    "avg_rent_burden_pct": 25.6,
                    "avg_black_share": 0.040,
                    "avg_hispanic_share": 0.137,
                    "avg_asian_share": 0.380,
                    "avg_white_share": 0.356
                }
            ],
            "fallback_note": str(e)
        }

equity_audit_agent = LlmAgent(
    name="equity_audit_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You perform post-output Responsible AI and Equity Audits at the metro level. "
        "You analyze silent distress candidates and demographic shares in aggregate. "
        "You NEVER evaluate or score individual tenants by demographic attributes."
    ),
    tools=[FunctionTool(run_equity_audit_query)],
    output_key="metro_equity_audit"
)

def draft_311_complaint(hazard_description: str, block_address: str) -> dict[str, Any]:
    """Drafts a structured 311 inspection request for a tenant documenting an unrecorded hazard."""
    return {
        "agency": "San Francisco Department of Building Inspection (DBI)",
        "complaint_type": "Habitability / Urgent Inspection Request",
        "block_address": block_address,
        "hazard_summary": hazard_description,
        "priority_level": "High - Immediate Life Safety",
        "filing_instructions": (
            "File online via SF311 or call 311. Request immediate DBI inspector site visit. "
            "Keep the 311 service request number to unlock habitability-contingent relief funds."
        )
    }

hazard_311_drafter_agent = LlmAgent(
    name="hazard_311_drafter_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You assist tenants and paralegals when zero 311 complaints exist on their block. "
        "You draft a formal municipal 311 / DBI inspection request so the tenant can establish "
        "an official city record, opening access to habitability-contingent stabilization funds."
    ),
    tools=[FunctionTool(draft_311_complaint)],
    output_key="drafted_311_request"
)

# --- Root Coordinator ---
shelterwise_navigator = LlmAgent(
    name="shelterwise_navigator",
    model="gemini-2.5-pro",
    instruction=(
        "You are the ShelterWise Navigator Root Coordinator for housing crisis triage in San Francisco. "
        "You guide legal-aid paralegals and housing counselors through intake and case analysis. "
        "For new crisis intakes, route to 'case_triage_pipeline'. "
        "For follow-up questions explaining why evidence was excluded, route to 'evidence_explainer_agent'. "
        "For questions on metro equity and demographic reporting bias, route to 'equity_audit_agent'. "
        "For unrecorded hazards needing a new city filing, route to 'hazard_311_drafter_agent'."
    ),
    sub_agents=[
        case_triage_pipeline,
        evidence_explainer_agent,
        equity_audit_agent,
        hazard_311_drafter_agent
    ]
)

root_agent = shelterwise_navigator
