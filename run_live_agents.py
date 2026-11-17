import json
import os
import sys

sys.path.insert(0, '/config/Desktop/AgentsForImpact/agent')

from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline
from shelterwise_agent.tools.brief import reconcile_gaps_and_generate_brief
from shelterwise_agent.agent import explain_excluded_evidence, run_equity_audit_query, draft_311_complaint

benchmark_raw = (
    "Mother of 2, 400 block Ellis St, San Francisco, cold radiators for 2 weeks in winter, "
    "water dripping from ceiling directly near kitchen electrical fuse box, nonpayment eviction hearing scheduled for Monday 9:00 AM. "
    "Census tract 06075030201."
)

print("Running Step 1: Intake Structuring...")
intake_res = structure_intake(benchmark_raw)

print("Running Step 2: Evidence Vector Search...")
evidence_res = search_public_evidence("cold radiators heating water leak electrical fuse box")

print("Running Step 3: Statutes and Relief Bulletins...")
policy_res = fetch_statutes_and_bulletins()

print("Running Step 4: Tract Displacement Baseline...")
geoid = intake_res.get("census_tract_geoid_11") or "06075030201"
tract_res = get_tract_displacement_baseline(geoid)

print("Running Step 5: Brief Synthesis & Gap Reconciliation...")
brief_res = reconcile_gaps_and_generate_brief(
    intake=intake_res,
    evidence=evidence_res,
    policy=policy_res,
    tract=tract_res
)

print("Running Step 6: Evidence Explainer Sub-Agent...")
first_excluded = evidence_res["excluded_candidates"][0] if evidence_res.get("excluded_candidates") else {
    "request_id": "DECOY-SANF-01",
    "exclusion_reason": "Commercial property decoy"
}
explainer_res = explain_excluded_evidence(
    candidate_id=first_excluded.get("request_id"),
    reason=first_excluded.get("exclusion_reason")
)

print("Running Step 7: Isolated Metro Equity Audit Sub-Agent...")
equity_res = run_equity_audit_query()

print("Running Step 8: 311 Hazard Drafter Sub-Agent...")
drafter_res = draft_311_complaint(
    hazard_description=intake_res.get("primary_hazard") + " and " + intake_res.get("secondary_hazard"),
    block_address=intake_res.get("block_address")
)

full_data = {
    "benchmark_case": {
        "tenant": "Elena Vance (Mother of 2)",
        "address": "400 Block Ellis St, Apt 3B, San Francisco, CA 94102",
        "intake_timestamp": "Thursday 3:40 PM",
        "hearing_date": "Monday 9:00 AM",
        "tract_geoid": geoid,
        "raw_narrative": benchmark_raw
    },
    "step_1_intake": intake_res,
    "step_2_evidence": evidence_res,
    "step_3_policy": policy_res,
    "step_4_tract": tract_res,
    "step_5_brief": brief_res,
    "specialist_agents": {
        "evidence_explainer": explainer_res,
        "equity_audit": equity_res,
        "hazard_311_drafter": drafter_res
    }
}

with open("live_agent_output.json", "w") as f:
    json.dump(full_data, f, indent=2)

print("\nSUCCESS! Saved full agent output to live_agent_output.json")
