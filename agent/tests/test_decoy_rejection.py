import pytest
from shelterwise_agent.tools.evidence import search_public_evidence

def test_decoy_rejection():
    # Query that should hit the planted decoys
    result = search_public_evidence("Scheduled multifamily habitability walkthrough confirmed weatherproof windows")
    
    # Ensure the tool returns a dict
    assert isinstance(result, dict)
    
    # Check that decoys are caught
    excluded = result.get("excluded_candidates", [])
    assert len(excluded) > 0, "Failed to catch any decoys"
    
    # Verify specific decoy reasons are present
    reasons = [e.get("exclusion_reason", "") for e in excluded]
    assert any("Zero violation" in r for r in reasons), "Failed to catch Zero Violation decoy"
