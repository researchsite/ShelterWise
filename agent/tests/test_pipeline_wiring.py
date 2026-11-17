"""Runs the real ADK agents for steps 2-4 + the verifier (no LLM needed) and checks session state."""

import asyncio

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from shelterwise.code_agents import Verifier
from shelterwise.pipeline import build_gather_and_decide

INTAKE_TEXT = ("Tenant at the 1000 block of Fillmore St. No heat for weeks, about 50 degrees inside, her kid "
               "keeps getting sick. Water dripping near the fuse box. Nonpayment hearing Monday Nov 23.")
PARSED = {"address_text": "1000 block of Fillmore St", "hazards": ["heat", "water_leak", "electrical"],
          "hazard_summary": "No heat for weeks and water dripping near the fuse box.",
          "search_query": "no heat in residential dwelling unit, temperature below code minimum",
          "hearing_date": "2026-11-23", "case_type": "nonpayment", "is_residential_tenant": True}
DRAFT = {"summary": "Open DBI case SF-202665182 on her block supports her no-heat account.",
         "memo_markdown": "City records are block-level, not proof about her unit. § 1942.4 does not apply yet.",
         "questions_for_tenant": ["Do you have your own DBI case number?"]}


async def _run(agents, seed_state):
    agent = SequentialAgent(name="test_pipeline", sub_agents=agents)
    runner = InMemoryRunner(agent=agent, app_name="t")
    session = await runner.session_service.create_session(app_name="t", user_id="u", state=seed_state)
    msg = types.Content(role="user", parts=[types.Part(text=INTAKE_TEXT)])
    texts = []
    async for ev in runner.run_async(user_id="u", session_id=session.id, new_message=msg):
        if ev.content and ev.content.parts:
            texts += [p.text for p in ev.content.parts if p.text]
    final = await runner.session_service.get_session(app_name="t", user_id="u", session_id=session.id)
    return final.state, "\n".join(texts)


def _steps_2_to_4_then_verify():
    state, _ = asyncio.run(_run([*build_gather_and_decide(), Verifier(name="verifier")], {"intake": PARSED}))
    return state


def test_code_steps_write_state_through_events():
    state = _steps_2_to_4_then_verify()
    case = state["case"]
    assert case["census_tract_geoid"] == "06075016300" and case["days_to_hearing"] == 4
    assert "water_near_electrical" in {a["id"] for a in state["safety"]["alerts"]}
    assert "SF-202665182" in {h["request_id"] for h in state["evidence"]["kept"]}
    assert state["tract"]["annual_filings_modeled"] == 65
    assert {s["statute_section_id"]: s["verdict"] for s in state["statutes"]}["STAT-CA-01"] == "NOT_YET"
    assert state["relief"][0]["bulletin_id"] == "BUL-CA-02"
    # No draft yet -> first verification fails and asks for a rewrite instead of finishing.
    assert state["brief"] is None and state["verify_attempts"] == 1
    assert "block-level" in state["verifier_feedback"]


def test_verifier_passes_good_draft_and_renders_brief():
    state = _steps_2_to_4_then_verify()
    seeded = {**state, "brief_draft": DRAFT, "verify_attempts": 0}
    state2, text = asyncio.run(_run([Verifier(name="verifier")], seeded))
    brief = state2["brief"]
    assert brief["verification"]["passed"] is True
    assert text.startswith("> 🚨 **SAFETY FIRST:**")
    assert "SF-202665182" in text and "Not yet" in text and "MODELED" in text


def test_verifier_gives_up_after_two_attempts_and_flags_memo():
    state = _steps_2_to_4_then_verify()  # verify_attempts == 1 already
    bad = {**DRAFT, "memo_markdown": "She is eligible for SF ERAP."}
    state2, _ = asyncio.run(_run([Verifier(name="verifier")], {**state, "brief_draft": bad}))
    brief = state2["brief"]
    assert brief["verification"]["passed"] is False and brief["verification"]["attempts"] == 2
    assert brief["memo_markdown"].startswith("> ⚠ The drafted memo failed automatic checks")
