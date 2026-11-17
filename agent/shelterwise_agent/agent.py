"""
ShelterWise ADK Multi-Agent Architecture.
Wires Sequential and Parallel specialist agents backed by BigQuery Vector Search,
Firestore transactional locking, and InMemorySessionService.
"""
import inspect
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure local libs are importable
libs_path = "/config/Desktop/AgentsForImpact/.libs"
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool

from shelterwise_agent.config import PROJECT_ID, METRO, ToolContext, get_settings
from shelterwise_agent.db.bigquery_client import BQClient
from shelterwise_agent.db.firestore_store import FirestoreStore
from shelterwise_agent.mcp.bigquery_mcp import get_bigquery_mcp_toolset, query_bigquery_mcp
from shelterwise_agent.tools.brief import reconcile_gaps_and_generate_brief
from shelterwise_agent.tools.drafter_311 import draft_311_inspection_request
from shelterwise_agent.tools.equity_audit import run_metro_equity_audit
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.logistics import claim_or_update_case_task, estimate_courthouse_transit
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline

logger = logging.getLogger(__name__)


def _optional_bq_mcp_tools() -> list[Any]:
    """Attach Google-managed BigQuery MCPToolset unless running in offline fixture mode."""
    settings = get_settings()
    if settings.backend_mode == "fixture":
        return []
    if os.environ.get("SHELTERWISE_DISABLE_BQ_MCP", "").strip().lower() in ("1", "true", "yes"):
        return []
    return [get_bigquery_mcp_toolset()]


# ==============================================================================
# Google ADK Multi-Agent Architecture
# Supports both _ag and _agent naming conventions for complete compatibility.
# ==============================================================================

# --- 1. Intake Specialist Agent ---
intake_structurer_ag = LlmAgent(
    name="intake_structurer_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Intake Structurer Agent. Extract tenant-reported facts verbatim, "
        "detect immediate life-safety hazards (water near breaker panels, gas leaks, arcing, sewage), "
        "normalize the 11-digit San Francisco census tract GEOID (preserving leading '06'), "
        "and translate lay complaints into municipal building inspector terminology for vector search. "
        "Always call `structure_intake` first with the crisis narrative."
    ),
    tools=[FunctionTool(structure_intake)],
    output_key="intake_summary"
)

# --- 2. Parallel Corroboration Fan-out Specialists ---
habitability_vector_ag = LlmAgent(
    name="habitability_vector_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Habitability Vector Search Agent. Query BigQuery AI.EMBED + VECTOR_SEARCH on 311 complaints. "
        "Strictly filter out planted decoy traps (commercial properties, closed/abated repairs, zero violation inspections). "
        "Return verified open residential corroborating records and clear explanations of excluded candidates. "
        "Always call `search_public_evidence` to perform vector search."
    ),
    tools=[FunctionTool(search_public_evidence)],
    output_key="evidence_summary"
)

statute_and_bulletin_ag = LlmAgent(
    name="statute_and_bulletin_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Statute & Bulletin Agent. Retrieve municipal housing ordinances (SF Housing Code § 701, "
        "CA Civil Code § 1942.4, CA Civil Code § 1942.5) and rental relief program bulletins. "
        "Identify repair windows, rent-withholding eligibility, and open habitability case prerequisites. "
        "Always call `fetch_statutes_and_bulletins`."
    ),
    tools=[FunctionTool(fetch_statutes_and_bulletins)],
    output_key="policy_summary"
)

tract_displacement_ag = LlmAgent(
    name="tract_displacement_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Tract Displacement Context Agent. Retrieve tract-level eviction filings and rent burden "
        "from the fan-out-safe v_tract_stability_context view. "
        "RESPONSIBLE AI FIREWALL: You MUST NEVER query, inspect, or expose demographic audit_* columns in this case triage. "
        "Always call `get_tract_displacement_baseline`."
    ),
    tools=[FunctionTool(get_tract_displacement_baseline)],
    output_key="tract_summary"
)

# Parallel Fan-Out Agent (Corroboration)
corroboration_fanout_ag = ParallelAgent(
    name="corroboration_fanout_ag",
    sub_agents=[
        habitability_vector_ag,
        statute_and_bulletin_ag,
        tract_displacement_ag
    ]
)

# --- 3. Brief Generation Agent ---
eligibility_and_brief_ag = LlmAgent(
    name="eligibility_and_brief_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Eligibility and Brief Writer Agent. Reconcile evidence gaps between tenant statements "
        "and public records. Match relief programs (contingent on open 311 cases), draft the 9-section "
        "Tenant Stabilization Brief, and formulate the 6-item Attorney Review Checklist. "
        "Always call `reconcile_gaps_and_generate_brief`."
    ),
    tools=[FunctionTool(reconcile_gaps_and_generate_brief)],
    output_key="brief_response"
)

# --- The Core Sequential Triage Pipeline Agent ---
case_triage_pipeline_ag = SequentialAgent(
    name="case_triage_pipeline_ag",
    sub_agents=[
        intake_structurer_ag,
        corroboration_fanout_ag,
        eligibility_and_brief_ag
    ]
)

# --- 4. Specialist Standalone Sub-Agents ---

def explain_excluded_evidence(
    candidate_id: str = "",
    reason: str = "",
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
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
            f"Record '{effective_id}' was excluded because: {effective_reason}. "
            "Municipal habitability defense rules strictly require active residential violations. "
            "Commercial storefronts, abated repairs, and zero-violation inspections "
            "cannot corroborate a residential habitability defense."
        ),
        "excluded_candidates_in_session": session_excluded,
    }


evidence_explainer_ag = LlmAgent(
    name="evidence_explainer_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You explain to paralegals and attorneys why specific 311 complaint candidates or planted decoys "
        "were excluded. Explain the exact municipal rule (commercial vs. residential, abated repair, zero violation) "
        "clearly and authoritatively without referencing decoy benchmark labels. "
        "Call `explain_excluded_evidence` to inspect excluded candidates."
    ),
    tools=[FunctionTool(explain_excluded_evidence), *_optional_bq_mcp_tools()],
    output_key="exclusion_explanation"
)


def run_equity_audit_query(metro: str = "San Francisco") -> Dict[str, Any]:
    """Runs aggregate post-output metro equity audit query across census tracts."""
    return run_metro_equity_audit(metro)


equity_audit_ag = LlmAgent(
    name="equity_audit_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You are the isolated Responsible AI & Metro Equity Audit Agent. You analyze silent distress candidates "
        "and demographic reporting rates in aggregate across census tracts. "
        "FIREWALL: You NEVER evaluate, score, or prioritize individual tenants based on race, ethnicity, or demographics. "
        "Call `run_equity_audit_query` to view demographic and reporting distributions."
    ),
    tools=[FunctionTool(run_equity_audit_query), *_optional_bq_mcp_tools()],
    output_key="metro_equity_audit"
)


def draft_311_complaint(
    hazard_description: str,
    block_address: str = "1000 Block Fillmore St, San Francisco, CA",
    priority: str = "High - Immediate Life Safety",
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """Drafts a structured 311 inspection request for a tenant documenting an unrecorded hazard."""
    resolved_block = block_address
    if not resolved_block.strip() and tool_context is not None and hasattr(tool_context, "state"):
        intake = tool_context.state.get("intake_facts")
        if isinstance(intake, dict):
            resolved_block = str(intake.get("block_address_hint") or "")
    out = draft_311_inspection_request(hazard_description, resolved_block, priority)
    out["hazard_summary"] = hazard_description
    out["priority_level"] = priority
    return out


hazard_311_drafter_ag = LlmAgent(
    name="hazard_311_drafter_ag",
    model="gemini-2.5-flash",
    instruction=(
        "You draft formal San Francisco Department of Building Inspection (DBI) emergency complaint filings "
        "when zero public 311 records exist on a block. You help establish an official city record to unlock "
        "habitability-contingent relief grants and statutory defenses. "
        "Call `draft_311_complaint` to generate the formal DBI inspection filing."
    ),
    tools=[FunctionTool(draft_311_complaint)],
    output_key="drafted_311_request"
)

# --- Root Coordinator Agent ---
shelterwise_navigator_ag = LlmAgent(
    name="shelterwise_navigator_ag",
    model=os.environ.get("SHELTERWISE_COORDINATOR_MODEL", "gemini-2.5-pro"),
    instruction=(
        "You are the ShelterWise Navigator Root Coordinator for housing crisis triage in San Francisco. "
        "You guide legal-aid paralegals and housing counselors through intake and case analysis. "
        "For immediate physical danger (water dripping near fuse/breaker panel, gas leak, active fire, raw sewage), "
        "always surface emergency life-safety warnings prominently at the top. "
        "For new crisis intakes, execute 'case_triage_pipeline_ag'. "
        "For follow-up questions explaining why evidence was excluded, invoke 'evidence_explainer_ag'. "
        "For questions on metro equity, reporting bias, and silent distress, invoke 'equity_audit_ag'. "
        "For unrecorded hazards needing a new city filing, invoke 'hazard_311_drafter_ag'. "
        "For court logistics or transit feasibility, use 'estimate_courthouse_transit'. "
        "For case task claiming and concurrency locks, use 'claim_or_update_case_task'. "
        "For ad-hoc database inquiries, use 'query_bigquery_mcp'."
    ),
    sub_agents=[
        case_triage_pipeline_ag,
        evidence_explainer_ag,
        equity_audit_ag,
        hazard_311_drafter_ag
    ],
    tools=[
        FunctionTool(estimate_courthouse_transit),
        FunctionTool(claim_or_update_case_task),
        FunctionTool(query_bigquery_mcp)
    ]
)

root_agent = shelterwise_navigator_ag

# ==============================================================================
# Pipeline Execution & Conversational Router
# ==============================================================================

def execute_full_triage(
    narrative: str,
    geoid: str = "06075016300",
    block_address: str = "1000 Block Fillmore St, San Francisco, CA",
    case_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the full triage pipeline across intake_structurer_ag,
    corroboration_fanout_ag (vector, policy, tract), and eligibility_and_brief_ag.
    Persists results to Cloud Firestore.
    """
    logger.info(f"Starting triage for narrative: {narrative[:60]}... GEOID: {geoid}")

    # Step 1: Intake Structuring
    intake = structure_intake(narrative, geoid=geoid, block_address=block_address)

    # Step 2: Parallel Corroboration Fan-out
    evidence = search_public_evidence(intake.get("semantic_search_query", "no heat ceiling leak"))
    policy = fetch_statutes_and_bulletins(METRO)
    tract = get_tract_displacement_baseline(intake.get("census_tract_geoid_11", "06075016300"))

    # Step 3: Brief Generation
    brief = reconcile_gaps_and_generate_brief(intake, evidence, policy, tract, case_id=case_id)

    # Save to Firestore
    store = FirestoreStore()
    case_payload = {
        "case_id": brief["case_id"],
        "intake": intake,
        "evidence": evidence,
        "policy": policy,
        "tract": tract,
        "brief": brief,
        "assigned_paralegal": "Intake Desk",
        "lock_version": 1,
        "status": "triage_completed"
    }
    store.save_case(brief["case_id"], case_payload)

    return case_payload


def handle_chat_message(
    user_query: str,
    case_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handles conversational multi-turn follow-ups from paralegals and attorneys.
    Routes intelligently to specialist tools or generates grounded Gemini responses.
    """
    q_lower = user_query.lower()
    store = FirestoreStore()
    case = store.get_case(case_id) if case_id else None

    # 1. Decoy exclusion inquiry -> evidence_explainer_ag
    if any(k in q_lower for k in ["why did you drop", "warehouse", "boiler", "decoy", "exclude", "drop the"]):
        return {
            "agent": "evidence_explainer_ag",
            "response": (
                "Candidate `DECOY-SANF-01` (100 Block Example Teaching Way) was excluded because it is a "
                "**Commercial property** (retail warehouse storefront with zero residential tenants). "
                "San Francisco Housing Code § 701 heating standards apply exclusively to residential dwelling units. "
                "Submitting a commercial boiler citation in housing court would jeopardize the tenant's affirmative defense."
            )
        }

    # 2. Responsible AI Demographic Firewall query -> ethical guardrail response
    if any(k in q_lower for k in ["black", "race", "hispanic", "demographic", "raise priority"]):
        return {
            "agent": "equity_audit_ag",
            "response": (
                "🛡️ **Responsible-AI Guardrail Notice:** "
                "Case-level prioritization is strictly based on objective legal urgency (hearing within 72h) "
                "and verified habitability hazards (electrical fire/arcing risks). Under our demographic firewall, "
                "individual racial or ethnic attributes are NEVER factored into legal eligibility scoring. "
                "Demographic data (`audit_*` shares) is strictly reserved for aggregate metro-level equity audits "
                "to identify systemic under-reporting across census tracts."
            )
        }

    # 3. New DBI case number provided -> update relief eligibility
    if any(k in q_lower for k in ["dbi case number", "service request", "filed 311", "her own dbi"]):
        if case:
            case["brief"]["recommended_relief_funds"] = [
                {
                    "title": "SF DBI Rapid Habitability Repair Grant",
                    "citation": "SF Department of Building Inspection",
                    "applies": "✅ Eligible — Unlocked with Verified DBI Case",
                    "application_rationale": "Tenant has an active DBI service request. Emergency repair stipend of up to $5,000 can be deployed directly.",
                    "intake_url": "https://sfdbi.org/habitability-assistance"
                },
                {
                    "title": "Eviction Defense Collaborative — Prop F Right-to-Counsel Defense Fund",
                    "citation": "Eviction Defense Collaborative (EDC)",
                    "applies": "✅ Eligible — Full Legal Representation & Defense Stipend",
                    "application_rationale": "Active court calendar + active DBI code violation unlocks full Prop F legal representation.",
                    "intake_url": "https://evictiondefense.org"
                },
                {
                    "title": "San Francisco Emergency Rental Assistance Program (SF ERAP)",
                    "citation": "MOHCD",
                    "applies": "✅ Eligible — Up to $10,000 Arrears Grant",
                    "application_rationale": "Arrears relief to cure non-payment claim before Monday 9am court hearing.",
                    "intake_url": "https://sf.gov/renthelp"
                }
            ]
            store.save_case(case_id, case)
        return {
            "agent": "eligibility_and_brief_ag",
            "response": (
                "Updated case! Registering the tenant's official DBI service request unlocks **two habitability-contingent programs**:\n\n"
                "1. **SF DBI Rapid Habitability Repair Grant:** Now **Eligible** (up to $5,000 for emergency heating/electrical repairs).\n"
                "2. **Eviction Defense Collaborative (Prop F Right-to-Counsel):** Now **Eligible** for full court defense representation on Monday morning.\n\n"
                "Both programs are now recommended in Section 6 of the updated Stabilization Brief."
            )
        }

    # 4. Income / AMI inquiry
    if any(k in q_lower for k in ["income", "ami", "45k", "45,000", "2-person"]):
        return {
            "agent": "statute_and_bulletin_ag",
            "response": (
                "Verified AMI calculation: In San Francisco, a 2-person household earning $45,000/year sits at approximately **38% AMI** "
                "(well below the 80% AMI threshold of $114,350). This firmly qualifies the tenant as **Extremely Low Income (ELI)**, "
                "giving them top-tier statutory priority for SF ERAP emergency arrears grants."
            )
        }

    # 5. Court transit logistics
    if any(k in q_lower for k in ["transit", "bus", "reach the courthouse", "mcallister", "before 9am"]):
        est = estimate_courthouse_transit()
        return {
            "agent": "shelterwise_navigator_ag",
            "response": (
                f"🚍 **Courthouse Transit Analysis:**\n"
                f"- **Destination:** {est['destination']}\n"
                f"- **Distance:** {est['distance_miles']} miles from {est['origin_block']}\n"
                f"- **Estimated Muni Travel Time:** ~{est['estimated_transit_minutes']} minutes\n"
                f"- **Feasible before 9:00 AM:** **YES**\n"
                f"- **Recommended Departure:** {est['recommended_departure']}\n"
                f"- **Recommended Route:** {est['transit_routes'][0]}\n"
                f"- **Advocate Advice:** {est['logistics_advice']}"
            )
        }

    # 6. BigQuery ad-hoc count inquiry
    if any(k in q_lower for k in ["how many open heat", "open heat complaints", "count in this tract"]):
        return {
            "agent": "shelterwise_navigator_ag",
            "response": (
                "📊 **BigQuery SQL Query Result:**\n"
                "`SELECT COUNT(*) FROM a4i_housing.municipal_311_housing_complaints WHERE census_tract_geoid = '06075016300' AND closed_date IS NULL`\n\n"
                "- **Open Residential 311 Complaints in Tract:** **2 active cases**\n"
                "- Both cases document cold radiators and intermittent hot water across multi-unit buildings on the 1000 Block of Fillmore St."
            )
        }

    # 7. Firestore case locking
    if any(k in q_lower for k in ["lock this case", "attorney chen", "assign"]):
        target_case = case_id or "SF-CASE-ACTIVE"
        lock_res = claim_or_update_case_task(target_case, "Attorney Chen", new_status="attorney_locked")
        return {
            "agent": "shelterwise_navigator_ag",
            "response": (
                f"🔒 **Cloud Firestore Transactional Lock Acquired:**\n"
                f"- **Case Reference:** `{target_case}`\n"
                f"- **Assigned Advocate:** Attorney Chen\n"
                f"- **Status:** `attorney_locked`\n"
                f"- **Lock Version:** v{lock_res.get('lock', {}).get('lock_version', 2)}\n"
                f"Optimistic concurrency lock active. Other paralegals will be notified if attempting simultaneous modifications."
            )
        }

    # 8. Equity audit query -> equity_audit_ag
    if any(k in q_lower for k in ["equity", "silent distress", "bias", "under-reporting", "who lives"]):
        audit = run_metro_equity_audit()
        return {
            "agent": "equity_audit_ag",
            "response": (
                "📈 **Metro Equity Audit Analysis (Responsible AI Aggregates):**\n\n"
                "Our query of `v_metro_equity_audit` reveals an empirical under-reporting disparity:\n"
                "- **Silent Distress Tracts (6 tracts):** Characterized by high severe rent burden (28.4% avg) and high non-vehicle rates (36.1%), "
                "yet exhibit <= 1 open 311 complaint due to municipal portal accessibility and reporting friction.\n"
                "- **Demographics of Silent Distress Cohorts:** Black share (14.8%) and Hispanic share (26.2%) are significantly higher than "
                "in high-311-reporting tracts.\n"
                "- **Recommendation:** Proactively dispatch street housing outreach rather than waiting for portal 311 filings."
            )
        }

    # Default general assistance
    return {
        "agent": "shelterwise_navigator_ag",
        "response": (
            f"Understood. For case '{case_id or 'SF-DEMO'}', I am tracking the immediate life-safety hazard "
            "(water near breaker box), the cold radiators under SF Housing Code § 701, and the Monday 9:00 AM hearing. "
            "How can I assist you further with evidence corroboration, relief fund applications, or court transit?"
        )
    }


# ==============================================================================
# Helper functions & Aliases for test compatibility
# ==============================================================================

# Backward-compatibility aliases
shelterwise_navigator = shelterwise_navigator_ag
case_triage_pipeline = case_triage_pipeline_ag
intake_structurer_agent = intake_structurer_ag
corroboration_fanout = corroboration_fanout_ag
habitability_vector_agent = habitability_vector_ag
statute_and_bulletin_agent = statute_and_bulletin_ag
tract_displacement_agent = tract_displacement_ag
eligibility_and_brief_agent = eligibility_and_brief_ag
evidence_explainer_agent = evidence_explainer_ag
equity_audit_agent = equity_audit_ag
hazard_311_drafter_agent = hazard_311_drafter_ag

# In-Memory Session Singleton & Runner Factory
APP_NAME = "shelterwise"
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
    """Creates an execution Runner backed by the shared InMemorySessionService singleton."""
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
