"""The decoy guarantee: all 9 planted traps fail the REAL rules, never a name match."""

from pathlib import Path

from shelterwise.tools.evidence import apply_rules, search_corroborating_complaints
from shelterwise.tools.geocode import locate, normalize_block

EXPECTED_DECOY_REASONS = {
    **{f"DECOY-SANF-0{i}": "not_residential" for i in (1, 2, 3)},
    **{f"DECOY-SANF-0{i}": "closed_abated" for i in (4, 5, 6)},
    **{f"DECOY-SANF-0{i}": "closed_no_violation" for i in (7, 8, 9)},
}


def _all_rows_as_candidates(repo):
    return [{**r, "cosine_distance": 0.1} for r in repo.complaints()]


def test_all_nine_decoys_excluded_with_the_right_reason_radius_off(repo):
    # Radius OFF: distance must not be what hides the decoys.
    out = apply_rules(_all_rows_as_candidates(repo), search_query="x", retrieval_mode="test",
                      origin=None, radius_m=None, keep_max=1000)
    excluded = {h["request_id"]: h["reasons"] for h in out["excluded"]}
    kept = {h["request_id"] for h in out["kept"]}
    for rid, reason in EXPECTED_DECOY_REASONS.items():
        assert rid in excluded, f"{rid} was not excluded"
        assert reason in excluded[rid], f"{rid}: expected {reason}, got {excluded[rid]}"
    assert not any(r.startswith("DECOY") for r in kept)
    assert len(kept) == 140  # every real open residential SF complaint survives


def test_rules_never_look_at_decoy_markers():
    src = (Path(__file__).resolve().parents[1] / "shelterwise").rglob("*.py")
    for f in src:
        code = f.read_text()
        assert "DECOY" not in code and "Planted" not in code, f"{f.name} references decoy markers"


def test_block_normalization():
    assert normalize_block("1000 block of Fillmore St") == (1000, "fillmore st")
    assert normalize_block("1032 Fillmore Street, San Francisco") == (1000, "fillmore st")
    assert normalize_block("1200 Block 35th Avenue") == (1200, "35th av")


def test_fillmore_located_from_block_centroid(repo):
    loc = locate("1000 block of Fillmore St", repo=repo)
    assert loc["location_source"] == "block_centroid_311"
    assert loc["census_tract_geoid"] == "06075016300"


def test_fillmore_no_heat_case_is_corroborated(repo):
    loc = locate("1000 block of Fillmore St", repo=repo)
    out = search_corroborating_complaints("no heat in residential dwelling unit, temperature below code",
                                          loc["lat"], loc["lng"], repo=repo)
    assert out["has_open_residential_nearby"]
    assert "SF-202665182" in {h["request_id"] for h in out["kept"]}
    assert all(h["meters_away"] <= 400 for h in out["kept"])
    assert "local-keyword-standin" in out["retrieval_mode"]  # offline results are labeled


def test_unknown_location_never_claims_nearby(repo):
    out = search_corroborating_complaints("no heat", None, None, repo=repo)
    assert out["location_known"] is False
    assert out["has_open_residential_nearby"] is False
