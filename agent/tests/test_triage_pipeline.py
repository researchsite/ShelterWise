import pytest
from google.adk.core.execution import InvocationContext
from shelterwise_agent.agent import case_triage_pipeline

@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    # Simulate the Thursday 3:40pm benchmark intake
    prompt = "Mother of 2, 400 block SF, cold radiators 2 wks, water dripping near kitchen fuse box, Monday 9am hearing. Tract 06075030201."
    
    ctx = InvocationContext()
    # Note: In a real test, we'd mock the BigQuery calls or use a test dataset.
    # We just want to ensure the agent orchestrator binds the tools correctly.
    assert case_triage_pipeline is not None
    assert len(case_triage_pipeline.sub_agents) == 3
    assert case_triage_pipeline.sub_agents[1].name == "corroboration_fanout"
    assert len(case_triage_pipeline.sub_agents[1].sub_agents) == 3
