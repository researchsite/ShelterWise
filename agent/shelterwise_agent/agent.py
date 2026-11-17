from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline
from shelterwise_agent.tools.brief import reconcile_gaps_and_generate_brief

# --- 1. Intake Agent ---
intake_structurer_agent = LlmAgent(
    name="intake_structurer_agent",
    model="gemini-2.5-flash",
    instruction="Extract facts, detect safety hazards, and normalize GEOIDs from intake narrative.",
    tools=[structure_intake],
    output_key="intake_facts"
)

# --- 2. Parallel Corroboration Fan-out ---
habitability_vector_agent = LlmAgent(
    name="habitability_vector_agent",
    model="gemini-2.5-flash",
    instruction="Vector search 311 complaints and filter decoys using search_public_evidence.",
    tools=[search_public_evidence],
    output_key="evidence_pack"
)

statute_and_bulletin_agent = LlmAgent(
    name="statute_and_bulletin_agent",
    model="gemini-2.5-flash",
    instruction="Fetch local statutes and rental relief bulletins.",
    tools=[fetch_statutes_and_bulletins],
    output_key="policy_pack"
)

tract_displacement_agent = LlmAgent(
    name="tract_displacement_agent",
    model="gemini-2.5-flash",
    instruction="Get tract displacement context.",
    tools=[get_tract_displacement_baseline],
    output_key="tract_context"
)

corroboration_fanout = ParallelAgent(
    name="corroboration_fanout",
    sub_agents=[habitability_vector_agent, statute_and_bulletin_agent, tract_displacement_agent]
)

# --- 3. Brief Generation Agent ---
eligibility_and_brief_agent = LlmAgent(
    name="eligibility_and_brief_agent",
    model="gemini-2.5-flash",
    instruction="Synthesize intake, evidence, policy, and tract context into a StabilizationBrief.",
    tools=[reconcile_gaps_and_generate_brief],
    output_key="stabilization_brief"
)

# --- The Pipeline ---
case_triage_pipeline = SequentialAgent(
    name="case_triage_pipeline",
    sub_agents=[
        intake_structurer_agent,
        corroboration_fanout,
        eligibility_and_brief_agent
    ]
)

root_coordinator = LlmAgent(
    name="shelterwise_navigator",
    model="gemini-2.5-pro",
    instruction="You are the ShelterWise root coordinator. For new intakes, delegate to case_triage_pipeline.",
    sub_agents=[case_triage_pipeline]
)
