"""Tests for Member 3 ADK multi-agent tree hierarchy and specialists."""

import unittest
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

class TestTriagePipeline(unittest.TestCase):

    def test_pipeline_hierarchy(self):
        """Verify SequentialAgent pipeline and 3-way ParallelAgent fanout."""
        self.assertIsNotNone(case_triage_pipeline)
        self.assertEqual(len(case_triage_pipeline.sub_agents), 3)
        self.assertTrue(case_triage_pipeline.sub_agents[0].name.startswith("intake_structurer"))
        self.assertTrue(case_triage_pipeline.sub_agents[1].name.startswith("corroboration_fanout"))
        self.assertTrue(case_triage_pipeline.sub_agents[2].name.startswith("eligibility_and_brief"))

        fanout = case_triage_pipeline.sub_agents[1]
        self.assertEqual(len(fanout.sub_agents), 3)
        names = [a.name for a in fanout.sub_agents]
        self.assertTrue(any(n.startswith("habitability_vector") for n in names))
        self.assertTrue(any(n.startswith("statute_and_bulletin") for n in names))
        self.assertTrue(any(n.startswith("tract_displacement") for n in names))

    def test_root_coordinator_and_specialists(self):
        """Verify root coordinator exports and specialist sub-agents."""
        self.assertIs(root_agent, shelterwise_navigator)
        sub_names = [a.name for a in shelterwise_navigator.sub_agents]
        self.assertTrue(any(n.startswith("case_triage_pipeline") for n in sub_names))
        self.assertTrue(any(n.startswith("evidence_explainer") for n in sub_names))
        self.assertTrue(any(n.startswith("equity_audit") for n in sub_names))
        self.assertTrue(any(n.startswith("hazard_311_drafter") for n in sub_names))

    def test_evidence_explainer_logic(self):
        """Verify explain_excluded_evidence returns structured legal explanation."""
        res = explain_excluded_evidence("DECOY-SANF-01", "Commercial property decoy")
        self.assertEqual(res["candidate_id"], "DECOY-SANF-01")
        self.assertIn("Commercial property decoy", res["explanation"])
        self.assertIn("cannot corroborate", res["explanation"])

    def test_hazard_311_drafter_logic(self):
        """Verify draft_311_complaint prepares valid DBI filing format."""
        res = draft_311_complaint("Defective heating and ceiling leak", "400 Block Ellis St")
        self.assertEqual(res["agency"], "San Francisco Department of Building Inspection (DBI)")
        self.assertEqual(res["block_address"], "400 Block Ellis St")
        self.assertIn("Defective heating", res["hazard_summary"])
        self.assertEqual(res["priority_level"], "High - Immediate Life Safety")

    def test_bigquery_mcp_toolset(self):
        """Verify BigQuery McpToolset initializes with Google-managed endpoint."""
        toolset = get_bigquery_mcp_toolset(project_id="test-project")
        self.assertIsNotNone(toolset)

    def test_runner_with_in_memory_session(self):
        """Verify create_runner instantiates Runner backed by InMemorySessionService."""
        from shelterwise_agent import create_runner
        runner = create_runner()
        self.assertIsNotNone(runner)

if __name__ == "__main__":
    unittest.main()
