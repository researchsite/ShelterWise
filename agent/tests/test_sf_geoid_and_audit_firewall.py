import pytest
from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.tract import get_tract_displacement_baseline

def test_sf_geoid_normalization():
    # Pass an SF geoid missing the leading zero
    result = structure_intake("Cold apartment", geoid="6075030201")
    assert result["census_tract_geoid_11"] == "06075030201", "Failed to pad leading zero for SF GEOID"

def test_audit_columns_firewalled():
    # Use a known SF GEOID
    result = get_tract_displacement_baseline("06075030201")
    
    # Assert none of the restricted audit columns leak into the agent
    keys = result.keys()
    assert "audit_black_share" not in keys
    assert "audit_hispanic_share" not in keys
    assert "audit_asian_share" not in keys
    assert "audit_white_share" not in keys
