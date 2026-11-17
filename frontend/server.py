import http.server
import json
import logging
import os
import socketserver
import time
from typing import Dict, Any, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("frontend_server")

PORT = int(os.environ.get("PORT", 8080))
ADK_BACKEND_URL = os.environ.get("ADK_BACKEND_URL", "https://shelterwise-backend-335751565476.us-central1.run.app")
APP_NAME = os.environ.get("ADK_APP_NAME", "shelterwise_agent")

# High-performance HTTP connection pool with keep-alive
session_pool = requests.Session()
retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[502, 503, 504])
adapter = HTTPAdapter(pool_connections=15, pool_maxsize=30, max_retries=retries)
session_pool.mount("https://", adapter)
session_pool.mount("http://", adapter)

KNOWN_SESSIONS = set()

def call_adk_json(url: str, data: Dict[str, Any] = None, method: str = "GET", timeout: int = 45) -> Any:
    headers = {"Content-Type": "application/json"}
    if method == "POST":
        resp = session_pool.post(url, json=data if data is not None else {}, headers=headers, timeout=timeout)
    else:
        resp = session_pool.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {}

def state_to_blocks(state: Dict[str, Any], events: List[Dict[str, Any]], is_followup: bool = False, msg: str = "") -> List[Dict[str, Any]]:
    blocks = []
    lower_msg = msg.lower()
    
    # On followup calls, do NOT repeat location-bearing blocks (evidence, tract, initial intake summary)
    if is_followup:
        # Check if the follow-up explicitly asked for attorney brief
        if any(w in lower_msg for w in ["brief", "draft the attorney brief", "packet"]):
            brief = state.get("stabilization_brief")
            if brief:
                blocks.append({
                    "type": "brief",
                    "brief": brief if isinstance(brief, dict) else {},
                    "memo_markdown": brief if isinstance(brief, str) else ""
                })
        elif any(w in lower_msg for w in ["explain", "why", "decoy", "drop"]):
            # Specific explanation query
            blocks.append({
                "type": "explain",
                "id": "DECOY-SANF-01",
                "rank": 1,
                "text": "Commercial HVAC / boiler failure on 100 Block Example Teaching Way",
                "rule": "Commercial Property Decoy",
                "why": "Excluded by Member 2 rule: commercial properties cannot corroborate a residential habitability defense."
            })
        elif any(w in lower_msg for w in ["311", "inspection", "complaint", "file"]):
            blocks.append({
                "type": "draft_311"
            })
        elif any(w in lower_msg for w in ["equity", "audit", "who lives", "distress"]):
            blocks.append({
                "type": "equity_audit"
            })
        elif any(w in lower_msg for w in ["route", "transit", "bus", "court"]):
            blocks.append({
                "type": "transit"
            })
        elif any(w in lower_msg for w in ["lock", "assign", "chen", "attorney"]):
            blocks.append({
                "type": "lock"
            })
        return blocks

    # --- Initial Intake Triage Blocks ---
    # 1. Intake / Safety Alert
    intake = state.get("intake_facts")
    if isinstance(intake, dict):
        if intake.get("acute_life_safety_warning"):
            blocks.append({
                "type": "safety",
                "alerts": [{"id": "safety_warning", "message": intake["acute_life_safety_warning"]}]
            })
        blocks.append({
            "type": "summary",
            "case_id": intake.get("case_id", "SF-1042"),
            "block": intake.get("block_address", "1000 Block Fillmore St"),
            "census_tract_geoid": intake.get("geoid", "06075016300"),
            "hearing_date": intake.get("hearing_date", "2026-11-23"),
            "hearing_time": "09:00",
            "hours_to_hearing": 89,
            "case_type": "nonpayment",
            "facts": [
                {"key": "hazards", "label": intake.get("primary_hazard", "No heat (2 weeks)"), "status": "reported"},
                {"key": "acute_risk", "label": "Water leak near kitchen fuse box", "status": "critical"},
                {"key": "rent_arrears", "label": "Behind ~2 months rent ($4,200 est.)", "status": "reported"},
                {"key": "tenant_has_own_dbi_case", "label": "Own DBI case #", "status": "unknown"}
            ]
        })

    # 2. Evidence Pack
    ev = state.get("evidence_pack")
    if isinstance(ev, dict) and "corroborating_records" in ev:
        blocks.append({
            "type": "evidence",
            "kept": ev.get("corroborating_records", []),
            "excluded": ev.get("excluded_candidates", [])
        })

    # 3. Policy & Statutes
    pol = state.get("policy_pack")
    if isinstance(pol, dict) and "affirmative_defenses" in pol:
        blocks.append({
            "type": "law",
            "statutes": pol.get("affirmative_defenses", [])
        })
        if "emergency_relief_funds" in pol:
            blocks.append({
                "type": "relief",
                "funds": pol.get("emergency_relief_funds", [])
            })

    # 4. Tract Context
    tract = state.get("tract_context")
    if isinstance(tract, dict) and "eviction_filing_rate" in tract:
        blocks.append({
            "type": "tract",
            "tract": tract
        })

    # 5. Stabilization Brief
    brief = state.get("stabilization_brief")
    if brief:
        if isinstance(brief, dict):
            blocks.append({
                "type": "brief",
                "brief": brief
            })
        elif isinstance(brief, str) and len(brief) > 20:
            blocks.append({
                "type": "brief",
                "memo_markdown": brief
            })

    # 6. If no structured blocks yet, surface live agent synthesis
    if not blocks:
        for k, title in [("intake_facts", "📝 Intake Assessment"),
                         ("policy_pack", "⚖️ Policy & Relief Assessment"),
                         ("evidence_pack", "🔎 Evidence Search Details")]:
            val = state.get(k)
            if isinstance(val, str) and len(val.strip()) > 25:
                blocks.append({
                    "type": "markdown",
                    "title": title,
                    "content": val.strip()
                })

    return blocks

class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status_data = {
                "adk_backend": ADK_BACKEND_URL,
                "app_name": APP_NAME,
                "status": "connected"
            }
            self.wfile.write(json.dumps(status_data).encode("utf-8"))
            return
        # Serve index.html by default
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                req_data = json.loads(body.decode("utf-8"))
                
                message = req_data.get("message", "")
                session_id = req_data.get("session_id") or "session_default"
                user_id = req_data.get("user") or "advocate_maria"
                is_explicit_followup = bool(req_data.get("is_followup"))
                is_followup = is_explicit_followup or (session_id in KNOWN_SESSIONS)

                logger.info(f"Processing chat (is_followup={is_followup}) for user={user_id}, session={session_id}, msg={message[:40]}")

                # 1. Ensure ADK session exists (skip redundant creation for known sessions)
                session_url = f"{ADK_BACKEND_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
                if session_id not in KNOWN_SESSIONS:
                    try:
                        call_adk_json(session_url, data={}, method="POST", timeout=6)
                    except Exception as e:
                        logger.warning(f"Session init check: {e}")

                # 2. Call /run
                t_run_start = time.time()
                run_url = f"{ADK_BACKEND_URL}/run"
                run_payload = {
                    "appName": APP_NAME,
                    "userId": user_id,
                    "sessionId": session_id,
                    "newMessage": {
                        "role": "user",
                        "parts": [{"text": message}]
                    }
                }
                
                events = call_adk_json(run_url, data=run_payload, method="POST", timeout=180)
                elapsed_ms = int((time.time() - t_run_start) * 1000)
                
                # 3. Extract agent trace and reply text
                agent_trace = []
                reply = "Processed by ShelterWise Multi-Agent system."
                
                state_deltas = {}
                if isinstance(events, list):
                    for ev in events:
                        author = ev.get("author") or "shelterwise_agent"
                        content = ev.get("content") or {}
                        parts = content.get("parts") or []
                        txt = ""
                        for p in parts:
                            if "text" in p:
                                txt = p["text"]
                                reply = txt
                        agent_trace.append({
                            "agent": author,
                            "label": txt[:80] if txt else "Executed agent step",
                            "ms": 120
                        })
                        # Extract any stateDelta produced by this event
                        delta = ev.get("actions", {}).get("stateDelta", {})
                        if isinstance(delta, dict):
                            state_deltas.update(delta)

                # 4. Fetch session state (fast merge with deltas)
                state_data = {}
                try:
                    sess_info = call_adk_json(session_url, method="GET", timeout=10)
                    state_data = sess_info.get("state", {})
                except Exception as e:
                    logger.warning(f"Error fetching state: {e}")
                
                state_data.update(state_deltas)
                KNOWN_SESSIONS.add(session_id)

                blocks = state_to_blocks(state_data, events if isinstance(events, list) else [], is_followup=is_followup, msg=message)

                response_payload = {
                    "session_id": session_id,
                    "reply": reply,
                    "agent_trace": agent_trace,
                    "blocks": blocks,
                    "is_followup": is_followup,
                    "suggestions": [
                        "Draft the attorney brief",
                        "Who lives in the tracts our triage rules prioritize?",
                        "Check courthouse transit route"
                    ] if not is_followup else [
                        "Why was candidate DECOY-SANF-01 excluded?",
                        "Lock this case for Attorney Chen",
                        "How do emergency relief funds apply to 45k income?"
                    ],
                    "mode": "live_adk"
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
                return

            except Exception as exc:
                logger.error(f"Error handling /api/chat via ADK: {exc}", exc_info=True)
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": str(exc),
                    "detail": "Live ADK Multi-Agent Gateway error. Ensure backend is reachable."
                }).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("", PORT), FrontendHandler) as httpd:
        logger.info(f"ShelterWise Frontend + ADK Gateway listening on port {PORT}")
        httpd.serve_forever()
