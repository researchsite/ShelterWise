"""Talk to the deployed Agent Runtime instance (Hualin's version).

    hualin/agent/.venv/bin/python hualin/query_remote.py "intake text" ["follow-up" ...]

One session per run (one intake per session). Prints tool calls, the reply, and the brief's
verification status from session state.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import agentplatform

PROJECT = os.getenv("PROJECT", "qwiklabs-gcp-04-99fa355171e1")
REGION = os.getenv("REGION", "us-central1")
ENGINE_ID = os.getenv("AGENT_RUNTIME_ID") or (Path(__file__).parent / ".agent_runtime_id").read_text().strip()
NAME = f"projects/{PROJECT}/locations/{REGION}/reasoningEngines/{ENGINE_ID}"

DEFAULT = ("Tenant at the 1000 block of Fillmore St. No heat for weeks, she says it's about 50 degrees inside and "
           "her kid keeps getting sick. Water from upstairs is dripping near the kitchen fuse box. Nonpayment "
           "hearing Monday Nov 23 at 9am. Single mom, behind about two months on rent. What do we have?")


async def main(turns: list[str]) -> None:
    client = agentplatform.Client(project=PROJECT, location=REGION)
    app = client.runtimes.get(name=NAME)
    session = await app.async_create_session(user_id="paralegal-demo")
    sid = session["id"] if isinstance(session, dict) else session.id
    print(f"engine: {NAME}\nsession: {sid}")
    for turn in turns:
        print(f"\n######## USER: {turn[:110]}")
        t = time.time()
        async for ev in app.async_stream_query(user_id="paralegal-demo", session_id=sid, message=turn):
            author = ev.get("author")
            for part in (ev.get("content") or {}).get("parts") or []:
                if part.get("function_call"):
                    fc = part["function_call"]
                    print(f"  [{author}] CALL {fc['name']}({json.dumps(fc.get('args'))[:140]})")
                elif part.get("text") and author not in ("user",) and not ev.get("partial"):
                    if author in ("shelterwise_navigator", "inspection_request_drafter"):
                        print(f"---- [{author}] reply:\n{part['text']}")
        print(f"  ({time.time() - t:.1f}s)")
    full = await app.async_get_session(user_id="paralegal-demo", session_id=sid)
    state = (full.get("state") if isinstance(full, dict) else full.state) or {}
    brief = state.get("brief") or {}
    print("\n==== verification:", brief.get("verification"))
    print("==== relief:", [(r["bulletin_id"], r["verdict"]) for r in brief.get("relief", [])])
    print("==== retrieval:", (brief.get("evidence") or {}).get("retrieval_mode"))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or [DEFAULT]))
