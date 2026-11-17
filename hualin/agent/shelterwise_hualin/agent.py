"""ShelterWise root agent (`adk web agent/` picks up `root_agent`)."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import config
from .llm_agents import NO_DEMOGRAPHICS, build_inspection_request_drafter
from .pipeline import build_brief_pipeline
from .tools.explain import explain_exclusion
from .tools.mcp import build_bigquery_mcp_toolset, mcp_firewall_callback

NAVIGATOR_INSTRUCTION = f"""You are ShelterWise, an assistant for legal-aid paralegals in {config.METRO}.
One session = one tenant intake.

How to work:
1. New intake, or new facts about the same tenant: call `brief_pipeline` with the paralegal's FULL intake
   text verbatim, plus every new fact from later turns (e.g. "Update: she has her own DBI case number").
2. When it returns, reply with the brief EXACTLY and COMPLETELY as returned, including the final "Checks:"
   line (it was checked by code). Safety alerts stay at the top. Do not add records, laws, funds or
   numbers of your own.
3. "Why did you exclude / keep X?": call `explain_exclusion` with the request ID.
4. If the brief says no open residential case was found near her block, or the paralegal wants to document
   a new hazard: transfer to `inspection_request_drafter`.
5. Ad-hoc data questions (counts, tables): use the BigQuery tools if available, read-only, and ONLY on
   projectId="{config.PROJECT}" (pass it on every call). The data:
   - `{config.DATASET}.municipal_311_housing_complaints`: request_id, block_address, census_tract_geoid (STRING),
     property_type, inspection_status, created_date, closed_date (NULL = open), complaint_narrative, metro_area
   - `{config.DATASET}.court_eviction_filings`: 4 rows (quarters) per tract, MODELED counts; SUM per tract first
   - `{config.DATASET}.acs_tract_housing_tenure`: Census rent burden per tract (list columns explicitly)
   - `{config.DATASET}.rental_relief_program_bulletins`, `{config.DATASET}.municipal_housing_ordinance_statutes`
   - `{config.OWN_DATASET}.v_tract_stability_context`: per-tract summary, quarters already summed
   Exact values (case-sensitive): property_type IN ('Residential', 'Commercial'); metro_area = '{config.METRO}';
   inspection_status e.g. 'Open - Active DBI Case', 'Closed - Abated', 'Closed - No Violation'.
   "Open" = closed_date IS NULL. If a count comes back 0, double-check the filter values before answering.
   Never select audit_* columns; never SELECT * from acs_tract_housing_tenure.
6. If the paralegal starts a different tenant, ask them to start a new session.

Always: you support the attorney, you do not give final legal advice. 311 records are block-level, not
proof about her unit. Eviction filing counts are modeled estimates. {NO_DEMOGRAPHICS}
"""


def build_root_agent() -> LlmAgent:
    tools = [AgentTool(agent=build_brief_pipeline()), explain_exclusion]
    mcp = build_bigquery_mcp_toolset()
    if mcp is not None:
        tools.append(mcp)
    return LlmAgent(
        name="shelterwise_navigator",
        model=config.MODEL_FAST,
        description="Housing-stability intake navigator for legal-aid paralegals.",
        instruction=NAVIGATOR_INSTRUCTION,
        tools=tools,
        sub_agents=[build_inspection_request_drafter()],
        before_tool_callback=mcp_firewall_callback,
    )


root_agent = build_root_agent()
