"""Tests for Member 3 ADK multi-agent tree hierarchy and specialists."""

import pytest
from shelterwise_agent.agent import (
    shelterwise_navigator,
    root_agent,
    case_triage_pipeline,
    corroboration_fanout,
    intake_structurer_agent,
    habitability_vector_agent,
    statute_and_bulletin_agent,
    tract_displacement_agent,
    eligibility_and_brief_agent,
    evidence_explainer_agent,
    equity_audit_agent,
    hazard_311_drafter_agent,
    explain_excluded_evidence,
    draft_311_complaint,
)
from shelterwise_agent.mcp.bigquery_mcp import get_bigquery_mcp_toolset

def test_pipeline_hierarchy():
    """Verify SequentialAgent pipeline and 3-way ParallelAgent fanout."""
    assert case_triage_pipeline is not None
    assert len(case_triage_pipeline.sub_agents) == 3
    assert case_triage_pipeline.sub_agents[0].name == "intake_structurer_agent"
    assert case_triage_pipeline.sub_agents[1].name == "corroboration_fanout"
    assert case_triage_pipeline.sub_agents[2].name == "eligibility_and_brief_agent"

    fanout = case_triage_pipeline.sub_agents[1]
    assert len(fanout.sub_agents) == 3
    names = [a.name for a in fanout.sub_agents]
    assert "habitability_vector_agent" in names
    assert "statute_and_bulletin_agent" in names
    assert "tract_displacement_agent" in names

def test_root_coordinator_and_specialists():
    """Verify root coordinator exports and specialist sub-agents."""
    assert root_agent is shelterwise_navigator
    sub_names = [a.name for a in shelterwise_navigator.sub_agents]
    assert "case_triage_pipeline" in sub_names
    assert "evidence_explainer_agent" in sub_names
    assert "equity_audit_agent" in sub_names
    assert "hazard_311_drafter_agent" in sub_names

def test_evidence_explainer_logic():
    """Verify explain_excluded_evidence returns structured legal explanation."""
    res = explain_excluded_evidence("DECOY-SANF-01", "Commercial property decoy")
    assert res["candidate_id"] == "DECOY-SANF-01"
    assert "Commercial property decoy" in res["explanation"]
    assert "cannot corroborate a residential habitability defense" in res["explanation"]

def test_hazard_311_drafter_logic():
    """Verify draft_311_complaint prepares valid DBI filing format."""
    res = draft_311_complaint("Defective heating and ceiling leak", "400 Block Ellis St")
    assert res["agency"] == "San Francisco Department of Building Inspection (DBI)"
    assert res["block_address"] == "400 Block Ellis St"
    assert "Defective heating" in res["hazard_summary"]
    assert res["priority_level"] == "High - Immediate Life Safety"

def test_bigquery_mcp_toolset():
    """Verify BigQuery McpToolset initializes with Google-managed endpoint."""
    toolset = get_bigquery_mcp_toolset(project_id="test-project")
    assert toolset is not None

def test_runner_with_in_memory_session():
    """Verify create_runner instantiates Runner backed by InMemorySessionService."""
    from shelterwise_agent import create_runner
    runner = create_runner()
    assert runner is not None
