from shelterwise_hualin.tools.brief import verify_draft
from shelterwise_hualin.tools.mcp import firewall_reason
from shelterwise_hualin.tools.pii import scrub
from shelterwise_hualin.tools.safety import check_safety

EVIDENCE = {"kept": [{"request_id": "SF-202665182"}],
            "excluded": [{"request_id": "DECOY-SANF-01", "reasons": ["not_residential"]}]}
STATUTES = [{"statute_section_id": "STAT-CA-01", "code_citation": "Cal. Civ. Code § 1941.1 & § 1942.4",
             "verdict": "NOT_YET"}]
RELIEF = [{"bulletin_id": "BUL-CA-01", "program_name": "San Francisco Emergency Rental Assistance Program (SF ERAP)",
           "verdict": "CONDITIONAL"}]
GOOD = {"summary": "Open DBI case SF-202665182 on her block supports her account; the hearing is in 4 days "
                   "and income is still unknown.",
        "memo_markdown": ("## Client situation\nTenant on the 1000 block faces a nonpayment hearing in 4 days.\n"
                         "## Corroborating city records\nOpen DBI case SF-202665182 on her block reports no heat. "
                         "Records are block-level, not proof about her unit.\n"
                         "## Legal analysis\n### § 1942.4\nThis does not apply yet; recheck after 35 days.\n"
                         "## Relief referrals\nSF ERAP may help if income is confirmed.\n"
                         "## Open questions\nDoes she have her own DBI case number?\n"
                         "## Evidentiary limits\nFilings are about 65 a year (modeled estimate)."),
        "questions_for_tenant": ["Do you have your own DBI case number?"]}


def _issues(**overrides):
    return verify_draft({**GOOD, **overrides}, evidence=EVIDENCE, statutes=STATUTES, relief=RELIEF)


def test_good_draft_passes():
    assert _issues() == []


def test_catches_excluded_id_invented_id_and_overclaims():
    assert any("EXCLUDED" in i for i in _issues(summary="See DECOY-SANF-01 on the block."))
    assert any("not in the evidence" in i for i in _issues(summary="See SF-999999999 on the block."))
    assert any("1942.4" in i for i in _issues(memo_markdown="Under § 1942.4 the landlord is barred. block"))
    assert any("eligible" in i for i in _issues(memo_markdown="She is eligible for SF ERAP. block"))
    assert any("modeled" in i for i in _issues(memo_markdown="There are 65 filings a year. block"))
    assert any("block-level" in i for i in _issues(memo_markdown=GOOD["memo_markdown"].replace("block", "street"),
                                                   summary=GOOD["summary"].replace("block", "street")))
    assert any("demographic" in i for i in _issues(summary="Mostly Hispanic tract, block-level."))


def test_safety_water_near_fuse_box():
    s = check_safety("water from upstairs is dripping near the kitchen fuse box", [])
    assert "water_near_electrical" in {a["id"] for a in s["alerts"]}
    assert not check_safety("radiators are cold", ["heat"])["has_alerts"]


def test_pii_scrub():
    out = scrub("My name is Maria Lopez, apt 4B, call 415-555-0134 or maria@x.com. The unit is cold.")
    assert "Maria" not in out and "4B" not in out and "555" not in out and "@" not in out
    assert "The unit is cold" in out


def test_mcp_firewall():
    assert firewall_reason("execute_sql_readonly", {"sql": "SELECT audit_black_share FROM t"})
    assert firewall_reason("execute_sql_readonly", {"sql": "select * from a4i_housing.acs_tract_housing_tenure"})
    assert firewall_reason("execute_sql", {"sql": "DELETE FROM t"})
    assert firewall_reason("execute_sql_readonly", {"sql": "SELECT COUNT(*) FROM a4i_housing.court_eviction_filings"}) is None


def test_off_task_draft_fails_quality_floor():
    issues = _issues(summary="Processing complete.", memo_markdown="# Task Complete\nNo further inputs.")
    assert any("too short" in i for i in issues)
    assert any("missing sections" in i for i in issues)
    assert any("must cite" in i for i in issues)


def test_heading_then_explanation_is_not_flagged():
    assert _issues() == []  # GOOD has "### § 1942.4" followed by "does not apply yet"


def test_mcp_firewall_blocks_other_projects(monkeypatch):
    import shelterwise_hualin.tools.mcp as mcp
    monkeypatch.setattr(mcp.config, "PROJECT", "my-proj")
    assert firewall_reason("list_table_ids", {"projectId": "bigquery-public-data", "datasetId": "x"})
    assert firewall_reason("execute_sql_readonly", {"projectId": "my-proj",
                                                    "query": "SELECT 1 FROM `bigquery-public-data.a.b`"})
    assert firewall_reason("list_table_ids", {"projectId": "my-proj", "datasetId": "a4i_housing"}) is None
