import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LIBS_DIR = os.path.join(PROJECT_ROOT, ".libs")

for p in [LIBS_DIR, BASE_DIR, PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from shelterwise_agent.agent import (
    shelterwise_navigator_ag,
    case_triage_pipeline_ag,
    intake_structurer_ag,
    corroboration_fanout_ag,
    habitability_vector_ag,
    statute_and_bulletin_ag,
    tract_displacement_ag,
    eligibility_and_brief_ag,
    evidence_explainer_ag,
    equity_audit_ag,
    hazard_311_drafter_ag,
    execute_full_triage,
    handle_chat_message
)
from shelterwise_agent.tools.intake import structure_intake
from shelterwise_agent.tools.evidence import search_public_evidence
from shelterwise_agent.tools.policy import fetch_statutes_and_bulletins
from shelterwise_agent.tools.tract import get_tract_displacement_baseline
from shelterwise_agent.tools.logistics import claim_or_update_case_task, estimate_courthouse_transit
from shelterwise_agent.tools.drafter_311 import draft_311_inspection_request
from shelterwise_agent.tools.equity_audit import run_metro_equity_audit
from shelterwise_agent.db.firestore_store import FirestoreStore

class TestShelterWise(unittest.TestCase):

    def test_all_agent_names_end_with_ag(self):
        """STRICT REQUIREMENT: All agent names must end with _ag."""
        agents = [
            shelterwise_navigator_ag,
            case_triage_pipeline_ag,
            intake_structurer_ag,
            corroboration_fanout_ag,
            habitability_vector_ag,
            statute_and_bulletin_ag,
            tract_displacement_ag,
            eligibility_and_brief_ag,
            evidence_explainer_ag,
            equity_audit_ag,
            hazard_311_drafter_ag
        ]
        for ag in agents:
            self.assertTrue(ag.name.endswith("_ag"), f"Agent '{ag.name}' does not end with '_ag'!")

    def test_intake_hazard_and_geoid(self):
        """Tests acute life safety hazard detection and 11-digit GEOID normalization."""
        narrative = "Tenant has no heat and water is dripping from ceiling into the kitchen fuse box. Hearing Monday at 9am."
        facts = structure_intake(narrative, geoid="6075016300", block_address="1000 Block Fillmore St")
        
        self.assertTrue(facts["immediate_life_safety_hazard"])
        self.assertIn("IMMEDIATE LIFE-SAFETY ALERT", facts["safety_alert_message"])
        self.assertEqual(facts["census_tract_geoid_11"], "06075016300", "Must zero-pad to 11 digits preserving leading 06")
        self.assertTrue(facts["hearing_within_72h"])
        self.assertIn("no heat", facts["semantic_search_query"])

    def test_decoy_rejection_rules(self):
        """
        Tests that commercial, abated, and zero-violation decoy records are filtered
        out by legitimate business predicates (never matching on 'DECOY').
        """
        evidence = search_public_evidence("no heat dwelling radiator cold leak", top_k=25)
        
        valid = evidence["corroborating_records"]
        excluded = evidence["excluded_candidates"]

        self.assertGreater(len(valid), 0, "Must have valid open residential records")
        for v in valid:
            self.assertEqual(v["property_type"], "Residential")
            self.assertIsNone(v["closed_date"])
            self.assertNotIn("no violation", v["inspection_status"].lower())

        commercial_caught = any("commercial" in ex["exclusion_reason"].lower() for ex in excluded)
        abated_caught = any("abated" in ex["exclusion_reason"].lower() for ex in excluded)
        zero_violation_caught = any("no violation" in ex["exclusion_reason"].lower() for ex in excluded)

        self.assertTrue(commercial_caught, "Failed to catch commercial property decoy")
        self.assertTrue(abated_caught, "Failed to catch closed/abated decoy")
        self.assertTrue(zero_violation_caught, "Failed to catch zero-violation decoy")

    def test_demographic_firewall_in_tract(self):
        """Verifies that no audit_* columns are ever present in case triage."""
        tract = get_tract_displacement_baseline("06075016300")
        for key in tract.keys():
            self.assertFalse(key.startswith("audit_"), f"Demographic firewall breached by column: {key}")
        self.assertEqual(tract["census_tract_geoid"], "06075016300")
        self.assertGreater(tract["severe_rent_burden_pct"], 0)
        self.assertGreater(tract["annual_filings_total"], 0)

    def test_statute_clocks_and_relief(self):
        """Verifies that statutes and relief programs evaluate habitability prerequisites."""
        policy = fetch_statutes_and_bulletins()
        statutes = policy["applicable_statutes"]
        funds = policy["applicable_relief_funds"]

        citations = [s["citation"] for s in statutes]
        self.assertTrue(any("Prop F" in c or "37" in c or "701" in c for c in citations), "Missing SF Rent Ordinance / Prop F")
        self.assertTrue(any("1942.4" in c for c in citations), "Missing CA Civil Code § 1942.4")
        self.assertTrue(any("1942.5" in c for c in citations), "Missing CA Civil Code § 1942.5")

        prop_f = next((f for f in funds if "Prop F" in f["title"] or "Right to Counsel" in f["title"]), None)
        self.assertIsNotNone(prop_f)
        self.assertTrue(prop_f["requires_open_habitability_case"])

    def test_firestore_transactional_lock(self):
        """Verifies optimistic concurrency locking via FirestoreStore."""
        store = FirestoreStore()
        case_id = "TEST-LOCK-CASE-01"
        
        r1 = store.claim_or_update_case_lock(case_id, "Paralegal Maria", expected_version=None, new_status="drafting")
        self.assertTrue(r1["success"])
        curr_v = r1["lock"]["lock_version"]
        
        r2 = store.claim_or_update_case_lock(case_id, "Attorney Chen", expected_version=curr_v, new_status="attorney_review")
        self.assertTrue(r2["success"])
        self.assertEqual(r2["lock"]["lock_version"], curr_v + 1)

        r3 = store.claim_or_update_case_lock(case_id, "Paralegal Bob", expected_version=curr_v, new_status="overwrite")
        self.assertFalse(r3["success"])
        self.assertIn("Conflict", r3["error"])

    def test_full_triage_pipeline_execution(self):
        """Executes the full triage pipeline and checks brief synthesis."""
        narrative = "Tenant at 1000 Block Fillmore St. No heat for weeks, 50 degrees inside. Nonpayment hearing Monday at 9am. Behind two months."
        res = execute_full_triage(narrative, geoid="06075016300", block_address="1000 Block Fillmore St, SF")
        
        self.assertIn("brief", res)
        brief = res["brief"]
        self.assertIn("case_id", brief)
        self.assertGreater(len(brief["verified_evidence"]), 0)
        self.assertGreater(len(brief["excluded_lookalikes"]), 0)
        self.assertEqual(len(brief["evidence_gaps"]), 3)
        self.assertEqual(len(brief["reviewer_checklist"]), 6)
        self.assertIn("TENANT STABILIZATION & HABITABILITY DEFENSE BRIEF", brief["brief_markdown"])

    def test_chat_routing(self):
        """Tests multi-turn follow-up routing for specialist queries."""
        rep1 = handle_chat_message("Why did you drop the warehouse boiler one?")
        self.assertEqual(rep1["agent"], "evidence_explainer_ag")
        self.assertIn("Commercial", rep1["response"])

        rep2 = handle_chat_message("Tenant is Black, can that raise priority?")
        self.assertEqual(rep2["agent"], "equity_audit_ag")
        self.assertIn("Guardrail", rep2["response"])

        rep3 = handle_chat_message("Can she reach the courthouse by bus before 9am Monday?")
        self.assertIn("Courthouse Transit Analysis", rep3["response"])
        self.assertIn("Civic Center Courthouse", rep3["response"])

    def test_equity_audit_aggregate(self):
        """Tests Responsible AI aggregate equity audit."""
        audit = run_metro_equity_audit()
        self.assertIn("cohorts", audit)
        self.assertGreater(len(audit["cohorts"]), 0)

if __name__ == "__main__":
    unittest.main()
