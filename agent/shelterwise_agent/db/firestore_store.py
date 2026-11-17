import os
import sys
import datetime
import logging
from typing import Dict, Any, Optional

# Ensure local libs are importable
libs_path = "/config/Desktop/AgentsForImpact/.libs"
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from shelterwise_agent.config import PROJECT_ID, FIRESTORE_DATABASE

logger = logging.getLogger(__name__)

# In-memory mock store for test environments or offline mode
_IN_MEMORY_CASES: Dict[str, Dict[str, Any]] = {}

class FirestoreStore:
    def __init__(self, project_id: str = PROJECT_ID, database: str = FIRESTORE_DATABASE):
        self.project_id = project_id
        self.database = database
        self.client = None
        try:
            from google.cloud import firestore
            self.client = firestore.Client(project=self.project_id, database=self.database)
            logger.info("Connected to Cloud Firestore (Native Mode).")
        except Exception as e:
            logger.warning(f"Could not connect to Cloud Firestore ({e}). Using in-memory store.")

    def save_case(self, case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves or updates case state in Firestore."""
        case_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "lock_version" not in case_data:
            case_data["lock_version"] = 1
        if "assigned_paralegal" not in case_data:
            case_data["assigned_paralegal"] = "Intake Desk"
        if "status" not in case_data:
            case_data["status"] = "triage_completed"

        if self.client:
            try:
                doc_ref = self.client.collection("cases").document(case_id)
                doc_ref.set(case_data, merge=True)
                return case_data
            except Exception as e:
                logger.error(f"Firestore save_case error: {e}")

        _IN_MEMORY_CASES[case_id] = case_data
        return case_data

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves case state by case_id."""
        if self.client:
            try:
                doc = self.client.collection("cases").document(case_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.error(f"Firestore get_case error: {e}")

        return _IN_MEMORY_CASES.get(case_id)

    def claim_or_update_case_lock(
        self, 
        case_id: str, 
        paralegal_name: str, 
        expected_version: Optional[int] = None,
        new_status: str = "in_review"
    ) -> Dict[str, Any]:
        """
        Implements @firestore.transactional optimistic concurrency locking so multiple
        paralegals don't overwrite each other's intake notes or attorney preparations.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if self.client:
            from google.cloud import firestore

            transaction = self.client.transaction()
            doc_ref = self.client.collection("cases").document(case_id)

            @firestore.transactional
            def update_in_transaction(txn, ref):
                snapshot = ref.get(transaction=txn)
                if not snapshot.exists:
                    # Create new lock
                    new_doc = {
                        "case_id": case_id,
                        "assigned_paralegal": paralegal_name,
                        "lock_version": 1,
                        "status": new_status,
                        "updated_at": now_iso
                    }
                    txn.set(ref, new_doc)
                    return {"success": True, "lock": new_doc, "action": "created"}

                current = snapshot.to_dict()
                curr_version = current.get("lock_version", 1)

                if expected_version is not None and expected_version != curr_version:
                    return {
                        "success": False,
                        "error": f"Conflict: Case was modified by {current.get('assigned_paralegal')} (v{curr_version}). Reload required.",
                        "current_version": curr_version,
                        "current_paralegal": current.get("assigned_paralegal")
                    }

                new_version = curr_version + 1
                updated = {
                    "assigned_paralegal": paralegal_name,
                    "lock_version": new_version,
                    "status": new_status,
                    "updated_at": now_iso
                }
                txn.update(ref, updated)
                current.update(updated)
                return {"success": True, "lock": current, "action": "updated"}

            try:
                return update_in_transaction(transaction, doc_ref)
            except Exception as e:
                logger.error(f"Transaction failed: {e}")

        # In-memory transactional fallback
        curr = _IN_MEMORY_CASES.get(case_id, {})
        curr_version = curr.get("lock_version", 1)
        if expected_version is not None and expected_version != curr_version:
            return {
                "success": False,
                "error": f"Conflict: Case modified by {curr.get('assigned_paralegal')} (v{curr_version}).",
                "current_version": curr_version
            }
        
        new_version = curr_version + 1
        curr.update({
            "case_id": case_id,
            "assigned_paralegal": paralegal_name,
            "lock_version": new_version,
            "status": new_status,
            "updated_at": now_iso
        })
        _IN_MEMORY_CASES[case_id] = curr
        return {"success": True, "lock": curr, "action": "in_memory_lock"}

    def update_checklist_item(self, case_id: str, item_index: int, checked: bool, verified_by: str) -> Dict[str, Any]:
        """Toggles an item in the 6-item Attorney Review Checklist."""
        case = self.get_case(case_id) or {"case_id": case_id, "checklist": {}}
        checklist = case.get("checklist", {})
        checklist[str(item_index)] = {
            "checked": checked,
            "verified_by": verified_by,
            "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        case["checklist"] = checklist
        return self.save_case(case_id, case)
