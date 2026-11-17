import os
import sys
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure local libs and agent package are on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LIBS_DIR = os.path.join(PROJECT_ROOT, ".libs")

for p in [LIBS_DIR, BASE_DIR, PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from shelterwise_agent.agent import execute_full_triage, handle_chat_message
from shelterwise_agent.db.firestore_store import FirestoreStore
from shelterwise_agent.db.bigquery_client import BQClient
from shelterwise_agent.tools.drafter_311 import draft_311_inspection_request
from shelterwise_agent.tools.equity_audit import run_metro_equity_audit
from shelterwise_agent.tools.logistics import estimate_courthouse_transit, claim_or_update_case_task
from shelterwise_agent.config import PROJECT_ID, METRO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shelterwise_server")

app = FastAPI(
    title="ShelterWise - Housing Stability & Eviction Defense Navigator",
    description="Multi-Agent AI for Legal-Aid Paralegals in San Francisco (Google ADK & BigQuery Vector Search)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class TriageRequest(BaseModel):
    narrative: str
    geoid: Optional[str] = "06075016300"
    block_address: Optional[str] = "1000 Block Fillmore St, San Francisco, CA"
    case_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    case_id: Optional[str] = None

class LockRequest(BaseModel):
    paralegal_name: str
    expected_version: Optional[int] = None
    new_status: str = "in_review"

class ChecklistRequest(BaseModel):
    item_index: int
    checked: bool
    verified_by: str = "Paralegal Advocate"

class Draft311Request(BaseModel):
    hazard_description: str
    block_address: Optional[str] = "1000 Block Fillmore St, San Francisco, CA"

# API Endpoints
@app.get("/api/health")
def health_check():
    bq = BQClient()
    store = FirestoreStore()
    return {
        "status": "healthy",
        "app": "ShelterWise",
        "project_id": PROJECT_ID,
        "metro": METRO,
        "bigquery_connected": bq.client is not None,
        "firestore_connected": store.client is not None,
        "version": "1.0.0"
    }

@app.post("/api/triage")
def run_triage(req: TriageRequest):
    try:
        result = execute_full_triage(
            narrative=req.narrative,
            geoid=req.geoid or "06075016300",
            block_address=req.block_address or "1000 Block Fillmore St, San Francisco, CA",
            case_id=req.case_id
        )
        return result
    except Exception as e:
        logger.error(f"Triage error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    try:
        reply = handle_chat_message(req.message, case_id=req.case_id)
        return reply
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    store = FirestoreStore()
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@app.post("/api/cases/{case_id}/lock")
def acquire_lock(case_id: str, req: LockRequest):
    store = FirestoreStore()
    res = store.claim_or_update_case_lock(
        case_id=case_id,
        paralegal_name=req.paralegal_name,
        expected_version=req.expected_version,
        new_status=req.new_status
    )
    return res

@app.post("/api/cases/{case_id}/checklist")
def update_checklist(case_id: str, req: ChecklistRequest):
    store = FirestoreStore()
    res = store.update_checklist_item(
        case_id=case_id,
        item_index=req.item_index,
        checked=req.checked,
        verified_by=req.verified_by
    )
    return res

@app.get("/api/equity-audit")
def equity_audit_endpoint():
    return run_metro_equity_audit()

@app.post("/api/draft-311")
def draft_311_endpoint(req: Draft311Request):
    return draft_311_inspection_request(
        hazard_description=req.hazard_description,
        block_address=req.block_address or "1000 Block Fillmore St, San Francisco, CA"
    )

@app.get("/api/transit-estimate")
def transit_estimate_endpoint(origin: Optional[str] = "1000 Block Fillmore St"):
    return estimate_courthouse_transit(origin_block=origin)

# Serve Web UI
candidate_paths = [
    os.path.join(BASE_DIR, "frontend", "index.html"),
    os.path.join(PROJECT_ROOT, "frontend", "index.html"),
    os.path.join(PROJECT_ROOT, "mockup", "index.html"),
]

@app.get("/", response_class=HTMLResponse)
def serve_index():
    for p in candidate_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>ShelterWise API Online</h1><p>Visit /docs for API documentation.</p>"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
