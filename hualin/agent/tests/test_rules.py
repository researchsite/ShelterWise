from datetime import date

from shelterwise_hualin.tools.legal import check_statutes
from shelterwise_hualin.tools.relief import check_relief_eligibility
from shelterwise_hualin.tools.tract import tract_context

BLOCK_EVIDENCE = {"has_open_residential_nearby": True,
                  "kept": [{"request_id": "SF-202665182", "created_date": "2026-11-03"}]}
NO_EVIDENCE = {"has_open_residential_nearby": False, "kept": []}


# ---- tract: no 4x fan-out, GEOID stays text ---------------------------------
def test_filings_summed_once_per_tract(repo):
    t = tract_context("06075016300", repo=repo)
    assert t["quarters_summed"] == 4
    assert t["annual_filings_modeled"] == 65          # not 260
    assert t["metro_annual_filings_modeled"] == 2359  # README's SF total
    assert t["filings_are_modeled"] is True


def test_geoids_keep_leading_zero(repo):
    assert all(isinstance(t["census_tract_geoid"], str) and len(t["census_tract_geoid"]) == 11
               and t["census_tract_geoid"].startswith("06") for t in repo.acs())


def test_severe_rent_burden(repo):
    t = tract_context("06075016300", repo=repo)
    assert t["severe_rent_burden_households"] == 265 and t["renter_households"] == 1653
    assert t["severe_rent_burden_pct"] == 16.0


def test_no_audit_columns_reach_the_agent(repo):
    for row in repo.acs():
        assert not any(k.startswith("audit_") for k in row)
    import shelterwise_hualin.data as data
    assert "audit_" not in " ".join(data.ACS_COLS)


# ---- statutes: clocks --------------------------------------------------------
def _verdict(findings, sid):
    return next(f for f in findings if f["statute_section_id"] == sid)


def test_rent_demand_bar_not_yet_at_16_days(repo, fillmore_case):
    f = _verdict(check_statutes(fillmore_case, BLOCK_EVIDENCE, repo=repo, today=date(2026, 11, 19)), "STAT-CA-01")
    assert f["verdict"] == "NOT_YET"
    assert f["recheck_on"] == "2026-12-09"


def test_rent_demand_bar_applies_if_after_35_days(repo, fillmore_case):
    f = _verdict(check_statutes(fillmore_case, BLOCK_EVIDENCE, repo=repo, today=date(2026, 12, 9)), "STAT-CA-01")
    assert f["verdict"] == "APPLIES_IF"


def test_prop_f_and_retaliation(repo, fillmore_case):
    out = check_statutes(fillmore_case, BLOCK_EVIDENCE, repo=repo, today=date(2026, 11, 19))
    assert _verdict(out, "STAT-CA-02")["verdict"] == "APPLIES"
    assert _verdict(out, "STAT-CA-03")["verdict"] == "APPLIES_IF"


# ---- relief: ELIGIBLE only when every condition is confirmed ---------------
def _fund(verdicts, bid):
    return next(v for v in verdicts if v["bulletin_id"] == bid)


def test_block_evidence_alone_never_makes_open_case_funds_eligible(repo, fillmore_case):
    v = check_relief_eligibility(fillmore_case, BLOCK_EVIDENCE, repo=repo)
    assert _fund(v, "BUL-CA-02")["verdict"] == "CONDITIONAL"
    assert _fund(v, "BUL-CA-04")["verdict"] == "CONDITIONAL"
    assert v[0]["bulletin_id"] == "BUL-CA-02" and v[0]["urgent"]  # lawyer first, hearing in 4 days


def test_unknown_income_stays_conditional(repo, fillmore_case):
    v = check_relief_eligibility(fillmore_case, NO_EVIDENCE, repo=repo)
    assert _fund(v, "BUL-CA-01")["verdict"] == "CONDITIONAL"
    assert any("80% AMI" in t for t in _fund(v, "BUL-CA-01")["to_confirm"])


def test_own_case_number_flips_prop_f_and_dbi_bridge(repo, fillmore_case):
    case = {**fillmore_case, "tenant_has_own_dbi_case": True}
    v = check_relief_eligibility(case, BLOCK_EVIDENCE, repo=repo)
    assert _fund(v, "BUL-CA-02")["verdict"] == "ELIGIBLE"
    assert _fund(v, "BUL-CA-04")["verdict"] == "ELIGIBLE"


def test_income_vs_ami(repo, fillmore_case):
    low = check_relief_eligibility({**fillmore_case, "income_pct_ami": 45}, NO_EVIDENCE, repo=repo)
    high = check_relief_eligibility({**fillmore_case, "income_pct_ami": 95}, NO_EVIDENCE, repo=repo)
    assert _fund(low, "BUL-CA-01")["verdict"] == "ELIGIBLE"
    assert _fund(high, "BUL-CA-01")["verdict"] == "INELIGIBLE"
    assert _fund(low, "BUL-CA-03")["verdict"] == "CONDITIONAL"  # still needs medical / wage loss


def test_no_case_means_ineligible_until_filed(repo, fillmore_case):
    v = check_relief_eligibility({**fillmore_case, "tenant_has_own_dbi_case": False}, NO_EVIDENCE, repo=repo)
    assert _fund(v, "BUL-CA-04")["verdict"] == "INELIGIBLE"


def test_income_vs_published_mohcd_limits(repo, fillmore_case):
    # 2 people, $45k: under 80% ($103,750) and 60% ($77,800) limits
    v = check_relief_eligibility({**fillmore_case, "household_size": 2, "annual_income_usd": 45000},
                                 NO_EVIDENCE, repo=repo)
    assert _fund(v, "BUL-CA-01")["verdict"] == "ELIGIBLE"
    assert _fund(v, "BUL-CA-03")["verdict"] == "CONDITIONAL"  # still needs medical / wage loss
    # 1 person, $90,760: $10 over the published 80% limit ($90,750), not the scaled 80% x $113,450
    over = check_relief_eligibility({**fillmore_case, "household_size": 1, "annual_income_usd": 90760},
                                    NO_EVIDENCE, repo=repo)
    assert _fund(over, "BUL-CA-01")["verdict"] == "INELIGIBLE"
    # household of 6 is not in the chart: never guessed
    big = check_relief_eligibility({**fillmore_case, "household_size": 6, "annual_income_usd": 50000},
                                   NO_EVIDENCE, repo=repo)
    assert _fund(big, "BUL-CA-01")["verdict"] == "CONDITIONAL"
    assert any("not in the chart" in t for t in _fund(big, "BUL-CA-01")["to_confirm"])
