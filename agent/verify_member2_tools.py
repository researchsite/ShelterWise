#!/usr/bin/env python3
"""Smoke & guardrail verification for Member 2 (Shiva) Schemas + 5 Core Custom Tools.

Run in Cloud Shell:
  1) Offline SF fixture smoke test (works before BigQuery tables are loaded):
       SHELTERWISE_BACKEND=fixture python3 agent/verify_member2_tools.py

  2) Live BigQuery VECTOR_SEARCH verification (once `a4i_housing.complaints_embedded` is ready):
       export GOOGLE_CLOUD_PROJECT="$(gcloud config get-value project)"
       SHELTERWISE_BACKEND=bigquery python3 agent/verify_member2_tools.py
"""

import inspect
import os
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from shelterwise_agent.config import ToolContext, get_settings, normalize_geoid_11  # noqa: E402
from shelterwise_agent.schemas import assert_no_audit_columns  # noqa: E402
from shelterwise_agent.tools import (  # noqa: E402
    CORE_TRIAGE_TOOLS,
    fetch_statutes_and_bulletins,
    get_tract_displacement_baseline,
    reconcile_gaps_and_generate_brief,
    search_public_evidence,
    structure_intake,
)


def main() -> None:
    cfg = get_settings()
    print(f"=== ShelterWise Member 2 Verification (backend_mode={cfg.backend_mode!r}) ===")

    # 1. ADK FunctionTool signature checks
    for fn in CORE_TRIAGE_TOOLS:
        sig = inspect.signature(fn)
        assert "tool_context" in sig.parameters, f"{fn.__name__} missing tool_context"
        assert sig.parameters["tool_context"].annotation is ToolContext, (
            f"{fn.__name__} bad ToolContext annotation"
        )
        for pname, param in sig.parameters.items():
            if pname == "tool_context":
                continue
            assert param.annotation in (str, int, float, bool), (
                f"{fn.__name__}.{pname} has non-primitive annotation {param.annotation}"
            )
    print("  [PASS 1/5] All ADK FunctionTool signatures verified")

    # 2. Leading-zero SF GEOID preservation ('06075...')
    assert normalize_geoid_11("6075012401") == "06075012401"
    assert normalize_geoid_11(6075012401) == "06075012401"
    print("  [PASS 2/5] San Francisco 11-char leading-zero GEOID ('06075...') verified")

    # 3. Tool 1: structure_intake (Safety Gate + PII Scrub + <72h Clock)
    ctx = ToolContext(state={})
    r1 = structure_intake(
        narrative=(
            "My name is Maria Lopez in Apt 4B at 418 Ellis St on the 400 Block Ellis St. "
            "Radiators have been ice cold for two weeks and water from upstairs is dripping "
            "near the kitchen fuse box. Got a 3-day nonpayment notice, court is Monday at 9am."
        ),
        metro="San Francisco",
        tool_context=ctx,
    )
    assert r1["status"] == "success", r1
    assert r1["immediate_safety_flag"] is True
    scrubbed = r1["intake_facts"]["scrubbed_narrative"]
    assert "Maria Lopez" not in scrubbed and "4B" not in scrubbed and "418 Ellis" not in scrubbed
    assert "400 Block" in scrubbed
    assert r1["intake_facts"]["urgency_tier"] == "immediate_72h"
    print("  [PASS 3/5] structure_intake: Safety Alert + PII Scrub + <72h Urgency verified")

    # 4. Tool 2 + Tool 3 + Tool 4 (Parallel Corroboration Fan-Out)
    r2 = search_public_evidence(top_k=25, tool_context=ctx)
    assert r2["status"] == "success", r2
    valid_ids = [r["request_id"] for r in r2["corroborating_records"]]
    assert not any(rid.startswith("DECOY-") for rid in valid_ids), (
        f"Planted DECOY leaked into corroborating_records: {valid_ids}"
    )
    if r2["backend_mode"] == "offline_sf_fixture":
        assert r2["exclusion_summary_counts"] == {
            "non_residential_property": 3,
            "closed_or_abated_case": 3,
            "no_violation_inspection": 3,
        }, r2["exclusion_summary_counts"]
    print(
        f"  [PASS 4/5] search_public_evidence ({r2['backend_mode']}): "
        f"{len(valid_ids)} valid open residential 311s, "
        f"{len(r2['excluded_candidates'])} excluded near-misses ({r2['exclusion_summary_counts']})"
    )

    r3 = fetch_statutes_and_bulletins(tool_context=ctx)
    r4 = get_tract_displacement_baseline(tool_context=ctx)
    assert r3["status"] == "success" and len(r3["statutes"]) >= 3 and len(r3["relief_bulletins"]) == 4
    assert r4["status"] == "success" and len(r4["tract_context"]["census_tract_geoid"]) == 11
    assert r4["tract_context"]["census_tract_geoid"].startswith("06")
    assert_no_audit_columns(r4)

    # 5. Tool 5: reconcile_gaps_and_generate_brief
    r5 = reconcile_gaps_and_generate_brief(
        reviewer_notes="Thursday 3:40pm walk-in intake", tool_context=ctx
    )
    assert r5["status"] == "success", r5
    assert "## 1. Case snapshot" in r5["brief_markdown"]
    assert "## 9. Reviewer checklist" in r5["brief_markdown"]
    assert_no_audit_columns(r5)
    print(
        f"  [PASS 5/5] Statutes ({len(r3['statutes'])}), Relief Bulletins ({len(r3['relief_bulletins'])}), "
        f"Tract ({r4['tract_context']['census_tract_geoid']}), & 9-Section Stabilization Brief verified!"
    )
    print("\nAll Member 2 checks passed cleanly.")


if __name__ == "__main__":
    os.environ.setdefault("SHELTERWISE_BACKEND", "auto")
    main()
