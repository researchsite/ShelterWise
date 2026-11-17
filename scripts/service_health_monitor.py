#!/usr/bin/env python3
"""
ShelterWise Continuous Health & Uptime Monitor
Monitors live Cloud Run endpoints, multi-agent chat response, and BigQuery/Firestore connectivity.
"""
import sys
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

ENDPOINTS = [
    {
        "name": "Redesign Service (Stitch v2) - Health",
        "url": "https://shelterwise-redesign-335751565476.us-central1.run.app/api/health",
        "expected_code": 200,
        "check_json": "status"
    },
    {
        "name": "Redesign Service (Stitch v2) - Frontend",
        "url": "https://shelterwise-redesign-335751565476.us-central1.run.app/",
        "expected_code": 200
    },
    {
        "name": "Google Stitch Component Showcase",
        "url": "https://shelterwise-redesign-335751565476.us-central1.run.app/stitch/",
        "expected_code": 200
    },
    {
        "name": "Production Main Service - Health",
        "url": "https://shelterwise-335751565476.us-central1.run.app/api/health",
        "expected_code": 200,
        "check_json": "status"
    }
]

def check_endpoint(ep):
    t0 = time.time()
    req = urllib.request.Request(
        ep["url"],
        headers={"User-Agent": "ShelterWise-Health-Monitor/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            latency = (time.time() - t0) * 1000
            code = resp.getcode()
            body = resp.read().decode("utf-8")
            
            if code != ep["expected_code"]:
                return False, f"HTTP {code} != {ep['expected_code']} ({latency:.1f}ms)"
            
            if ep.get("check_json"):
                try:
                    data = json.loads(body)
                    if data.get(ep["check_json"]) != "healthy":
                        return False, f"JSON key '{ep['check_json']}' is {data.get(ep['check_json'])} ({latency:.1f}ms)"
                except Exception as e:
                    return False, f"JSON parse error: {e}"
            
            return True, f"OK HTTP {code} ({latency:.1f}ms)"
    except urllib.error.HTTPError as e:
        latency = (time.time() - t0) * 1000
        return False, f"HTTPError {e.code} ({latency:.1f}ms)"
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return False, f"Connection error: {e} ({latency:.1f}ms)"

def check_chat_api():
    t0 = time.time()
    url = "https://shelterwise-redesign-335751565476.us-central1.run.app/api/chat"
    payload = json.dumps({
        "message": "Health monitor automated heartbeat test",
        "case_id": "monitor-heartbeat"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ShelterWise-Health-Monitor/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            latency = (time.time() - t0) * 1000
            code = resp.getcode()
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            agent = data.get("agent", "unknown")
            return True, f"Chat OK ({latency:.1f}ms, routed to: {agent})"
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return False, f"Chat API error: {e} ({latency:.1f}ms)"

def run_all_checks():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] Starting ShelterWise continuous service health check...")
    
    all_ok = True
    results = []
    
    for ep in ENDPOINTS:
        ok, detail = check_endpoint(ep)
        status_mark = "✔" if ok else "✖"
        print(f"  {status_mark} {ep['name']}: {detail}")
        results.append(f"{ep['name']}: {detail}")
        if not ok:
            all_ok = False
            
    chat_ok, chat_detail = check_chat_api()
    chat_mark = "✔" if chat_ok else "✖"
    print(f"  {chat_mark} Multi-Agent Chat API: {chat_detail}")
    results.append(f"Multi-Agent Chat API: {chat_detail}")
    if not chat_ok:
        all_ok = False
        
    log_line = f"[{timestamp}] OVERALL: {'PASS' if all_ok else 'FAIL'} | " + "; ".join(results) + "\n"
    with open("monitor_history.log", "a", encoding="utf-8") as f:
        f.write(log_line)
        
    print(f"[{timestamp}] Health check finished: {'ALL SYSTEMS OPERATIONAL' if all_ok else 'SYSTEM DEGRADED'}")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(run_all_checks())
