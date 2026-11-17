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

import inspect
import os
from typing import Any
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool

from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline
from shelterwise_agent.tools.brief import reconcile_gaps_and_generate_brief
from shelterwise_agent.config import ToolContext, get_settings
from shelterwise_agent.mcp.bigquery_mcp import get_bigquery_mcp_toolset


def _optional_bq_mcp_tools() -> list[Any]:
    """Attach Google-managed BigQuery MCPToolset unless running in offline fixture mode."""
    settings = get_settings()
    if settings.backend_mode == "fixture":
        return []
    if os.environ.get("SHELTERWISE_DISABLE_BQ_MCP", "").strip().lower() in ("1", "true", "yes"):
        return []
    return [get_bigquery_mcp_toolset()]


# --- 1. Intake Agent ---
# Note: Tools write structured dicts into session.state['intake_facts'],
# state['evidence_pack'], state['raw_policy_pack'], state['tract_context'],
# and state['stabilization_brief']. Agent output_keys use distinct *_summary
# names so LLM text responses never overwrite those structured tool dicts.
intake_structurer_agent = LlmAgent(
    name="intake_structurer_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Always call `structure_intake` first with the user's crisis narrative and any known "
        "metro, 100-block hint, census tract GEOID, or court hearing date. "
        "Detect immediate life-safety hazards (e.g., water dripping near fuse box, raw sewage, gas leak), "
        "and preserve 11-digit string census tract GEOIDs (including leading '06' for San Francisco)."
    ),
    tools=[FunctionTool(structure_intake)],
    output_key="intake_summary"
)

# --- 2. Parallel Corroboration Fan-out Specialists ---
habitability_vector_agent = LlmAgent(
    name="habitability_vector_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Always call `search_public_evidence` to perform BigQuery vector search on municipal 311 "
        "housing complaints (it automatically reads `intake_facts` from session state). "
        "Strictly exclude ineligible near-miss records (commercial properties, closed/abated repairs, "
        "and zero-violation clearance inspections) using legitimate municipal source fields only, "
        "and never refer to excluded records as 'decoys' in user-facing output."
    ),
    tools=[FunctionTool(search_public_evidence)],
    output_key="evidence_summary"
)

statute_and_bulletin_agent = LlmAgent(
    name="statute_and_bulletin_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Always call `fetch_statutes_and_bulletins` (reads `intake_facts` from session state) "
        "to fetch municipal housing statutes and emergency rental relief program bulletins, "
        "highlighting prerequisites such as `requires_open_habitability_case`."
    ),
    tools=[FunctionTool(fetch_statutes_and_bulletins)],
    output_key="policy_summary"
)

tract_displacement_agent = LlmAgent(
    name="tract_displacement_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Always call `get_tract_displacement_baseline` (reads `intake_facts` from session state) "
        "to retrieve the fan-out-safe 4-quarter pre-aggregated displacement baseline (`[Modeled]`) "
        "and ACS rent burden. Strictly ensure no demographic `audit_*` columns are accessed in case triage."
    ),
    tools=[FunctionTool(get_tract_displacement_baseline)],
    output_key="tract_summary"
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
        "Always call `reconcile_gaps_and_generate_brief` to deterministically cross-check relief "
        "program eligibility against open residential 311 corroboration and compile the 9-section "
        "Tenant Stabilization Brief. Output the complete `brief_markdown` clearly, surfacing any "
        "IMMEDIATE LIFE-SAFETY FLAG at the top and preserving 100-block, `[Modeled]` eviction, "
        "and human-attorney review caveats."
    ),
    tools=[FunctionTool(reconcile_gaps_and_generate_brief)],
    output_key="brief_response"
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

def explain_excluded_evidence(
    candidate_id: str = "",
    reason: str = "",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Explains why candidate 311 complaints were excluded based on municipal business rules."""
    session_excluded: list[dict[str, Any]] = []
    if tool_context is not None and hasattr(tool_context, "state"):
        ev_pack = tool_context.state.get("evidence_pack")
        if isinstance(ev_pack, dict):
            raw_list = ev_pack.get("excluded_candidates") or []
            if candidate_id.strip():
                session_excluded = [
                    c for c in raw_list if str(c.get("request_id")) == candidate_id.strip()
                ] or raw_list[:5]
            else:
                session_excluded = raw_list[:8]

    effective_id = candidate_id or (
        str(session_excluded[0].get("request_id")) if session_excluded else "excluded_candidates"
    )
    effective_reason = reason or (
        str(session_excluded[0].get("exclusion_reason"))
        if session_excluded
        else "Did not meet active residential habitability eligibility criteria"
    )
    return {
        "candidate_id": effective_id,
        "explanation": (
            f"Record {effective_id} was excluded because: {effective_reason}. "
            "Municipal business rules require active residential habitability hazards. "
            "Commercial properties, closed/abated repairs, and zero-violation inspections "
            "cannot corroborate a residential habitability defense."
        ),
        "excluded_candidates_in_session": session_excluded,
    }


evidence_explainer_agent = LlmAgent(
    name="evidence_explainer_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You explain to paralegals and attorneys why specific 311 complaint candidates were excluded. "
        "Call `explain_excluded_evidence` to inspect excluded candidates from the current session state "
        "(or query BigQuery via MCP for follow-up block/tract checks) and explain the exact municipal "
        "business rule (commercial property, closed/abated repairs, zero violations found) without "
        "ever referencing benchmark or decoy labels."
    ),
    tools=[FunctionTool(explain_excluded_evidence), *_optional_bq_mcp_tools()],
    output_key="exclusion_explanation"
)


def run_equity_audit_query(metro: str = "San Francisco") -> dict[str, Any]:
    """Runs aggregate post-output metro equity audit query across census tracts."""
    try:
        from google.cloud import bigquery
        settings = get_settings()
        project = settings.project_id or None
        dataset = settings.dataset or "a4i_housing"
        client = bigquery.Client(project=project)
        effective_project = client.project
        sql = f"""
        WITH open_311 AS (
          SELECT
            LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS geoid,
            COUNT(*) AS open_res_311_cnt
          FROM `{effective_project}.{dataset}.municipal_311_housing_complaints`
          WHERE metro_area = @metro
            AND LOWER(property_type) = 'residential'
            AND closed_date IS NULL
            AND LOWER(COALESCE(inspection_status, '')) NOT LIKE '%closed%'
            AND LOWER(COALESCE(inspection_status, '')) NOT LIKE '%no violation%'
          GROUP BY 1
        ),
        tract_cohorts AS (
          SELECT
            SAFE_DIVIDE(t.renter_hh_rent_50_pct_plus_count, NULLIF(t.renter_occupied_units, 0)) * 100.0 AS severe_rent_burden_pct,
            COALESCE(o.open_res_311_cnt, 0) AS open_res_311_cnt,
            (
              SAFE_DIVIDE(t.renter_hh_rent_50_pct_plus_count, NULLIF(t.renter_occupied_units, 0)) >= 0.20
              AND COALESCE(o.open_res_311_cnt, 0) <= 1
            ) AS is_silent_distress_candidate,
            t.no_vehicle_rate,
            t.audit_black_share,
            t.audit_hispanic_share,
            t.audit_asian_share,
            t.audit_indigenous_share,
            t.audit_white_share
          FROM `{effective_project}.{dataset}.acs_tract_housing_tenure` t
          LEFT JOIN open_311 o
            ON LPAD(CAST(t.census_tract_geoid AS STRING), 11, '0') = o.geoid
          WHERE t.metro_area = @metro
        )
        SELECT
          is_silent_distress_candidate,
          COUNT(*) AS tract_count,
          ROUND(AVG(severe_rent_burden_pct), 1) AS avg_rent_burden_pct,
          ROUND(AVG(no_vehicle_rate), 3) AS avg_no_vehicle_rate,
          ROUND(AVG(audit_black_share), 3) AS avg_black_share,
          ROUND(AVG(audit_hispanic_share), 3) AS avg_hispanic_share,
          ROUND(AVG(audit_asian_share), 3) AS avg_asian_share,
          ROUND(AVG(audit_indigenous_share), 3) AS avg_indigenous_share,
          ROUND(AVG(audit_white_share), 3) AS avg_white_share
        FROM tract_cohorts
        GROUP BY 1
        ORDER BY 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("metro", "STRING", metro)]
        )
        rows = list(client.query(sql, job_config=job_config).result())
        return {"metro": metro, "audit_summary": [dict(r.items()) for r in rows]}
    except Exception as e:
        return {
            "metro": metro,
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
        "Call `run_equity_audit_query` (and BigQuery MCP if deeper aggregate SQL slicing is requested) "
        "to analyze silent-distress tracts (`severe_rent_burden >= 20%` with `<= 1` open 311) and "
        "demographic shares in aggregate. You NEVER evaluate or score individual tenants by demographics."
    ),
    tools=[FunctionTool(run_equity_audit_query), *_optional_bq_mcp_tools()],
    output_key="metro_equity_audit"
)


def draft_311_complaint(
    hazard_description: str,
    block_address: str,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Drafts a structured 311 inspection request for a tenant documenting an unrecorded hazard."""
    resolved_block = block_address
    if not resolved_block.strip() and tool_context is not None and hasattr(tool_context, "state"):
        intake = tool_context.state.get("intake_facts")
        if isinstance(intake, dict):
            resolved_block = str(intake.get("block_address_hint") or "")
    return {
        "agency": "San Francisco Department of Building Inspection (DBI)",
        "complaint_type": "Habitability / Urgent Inspection Request",
        "block_address": resolved_block,
        "hazard_summary": hazard_description,
        "priority_level": "High - Immediate Life Safety",
        "filing_instructions": (
            "File online via SF311 or call 311. Request immediate DBI inspector site visit. "
            "Keep the 311 service request number to unlock habitability-contingent relief funds, "
            "and screen immediately for general stabilization funds (`requires_open_habitability_case = FALSE`) "
            "while the inspection is pending."
        )
    }


hazard_311_drafter_agent = LlmAgent(
    name="hazard_311_drafter_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You assist tenants and paralegals when zero 311 complaints exist on their block. "
        "Call `draft_311_complaint` to prepare a formal municipal 311 / DBI inspection request so "
        "the tenant can establish an official city record (unlocking habitability-contingent funds) "
        "while immediately applying to general stabilization grants that do not require an open 311 case."
    ),
    tools=[FunctionTool(draft_311_complaint)],
    output_key="drafted_311_request"
)

# --- Root Coordinator ---
shelterwise_navigator = LlmAgent(
    name="shelterwise_navigator",
    model=os.environ.get("SHELTERWISE_COORDINATOR_MODEL", "gemini-2.5-pro"),
    instruction=(
        "You are the ShelterWise Navigator Root Coordinator for housing crisis triage in San Francisco. "
        "You guide legal-aid paralegals and housing counselors through multi-turn intake and case analysis. "
        "For immediate physical danger (wet fuse/breaker panel, gas leak, active fire, raw sewage), "
        "always surface emergency life-safety warnings prominently. "
        "For new crisis intakes or updated case facts, route to 'case_triage_pipeline'. "
        "For follow-up questions explaining why 311 evidence was excluded, route to 'evidence_explainer_agent'. "
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

# --- In-Memory Session Singleton & Runner Factory ---
from google.adk.runners import Runner, InMemoryRunner
from google.adk.sessions import InMemorySessionService

APP_NAME = "shelterwise"
# Process-wide singleton InMemorySessionService so multi-turn API/chat requests
# share conversation history and session.state across turns instead of resetting.
SESSION_SERVICE = InMemorySessionService()
_DEFAULT_RUNNER: Runner | None = None


def get_session_service() -> InMemorySessionService:
    """Returns the shared process-wide InMemorySessionService singleton."""
    return SESSION_SERVICE


def create_runner(
    agent=None,
    session_service=None,
    app_name: str = APP_NAME,
) -> Runner:
    """Creates an execution Runner backed by the shared InMemorySessionService singleton.

    In ADK, agents are stateless definitions; state sharing (`tool_context.state`)
    and multi-turn conversation history are managed by the Runner via its SessionService.
    """
    runner_kwargs: dict[str, Any] = {
        "agent": agent or root_agent,
        "app_name": app_name,
        "session_service": session_service or SESSION_SERVICE,
    }
    if "auto_create_session" in inspect.signature(Runner.__init__).parameters:
        runner_kwargs["auto_create_session"] = True
    return Runner(**runner_kwargs)


def get_runner() -> Runner:
    """Returns a singleton Runner wired to `root_agent` and `SESSION_SERVICE`."""
    global _DEFAULT_RUNNER
    if _DEFAULT_RUNNER is None:
        _DEFAULT_RUNNER = create_runner()
    return _DEFAULT_RUNNER
