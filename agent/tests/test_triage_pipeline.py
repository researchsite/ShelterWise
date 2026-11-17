import pytest
from shelterwise_agent.agent import case_triage_pipeline

def test_pipeline_structure():
    assert case_triage_pipeline is not None
    assert len(case_triage_pipeline.sub_agents) == 3
    assert case_triage_pipeline.sub_agents[0].name == "intake_structurer_agent"
    assert case_triage_pipeline.sub_agents[1].name == "corroboration_fanout"
    assert case_triage_pipeline.sub_agents[2].name == "eligibility_and_brief_agent"
    assert len(case_triage_pipeline.sub_agents[1].sub_agents) == 3
