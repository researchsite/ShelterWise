"""Deterministic (non-LLM) pipeline steps.

Each step reads session state and yields ONE event whose `state_delta` carries its
result. Writing state through events (never by mutating ctx.session.state) is what
lets AgentTool copy the results back to the navigator's session.
"""

from __future__ import annotations

from datetime import date
from typing import Any, AsyncGenerator, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from . import config
from .tools.brief import assemble_brief, render_markdown, verify_draft
from .tools.evidence import search_corroborating_complaints
from .tools.geocode import locate
from .tools.legal import check_statutes
from .tools.pii import scrub
from .tools.relief import check_relief_eligibility
from .tools.safety import check_safety
from .tools.tract import tract_context

MAX_VERIFY_ATTEMPTS = 2


def _user_text(ctx: InvocationContext) -> str:
    content = ctx.user_content
    if not content or not content.parts:
        return ""
    return "\n".join(p.text for p in content.parts if getattr(p, "text", None))


class CodeStep(BaseAgent):
    """Base class: subclasses implement compute(state, ctx) -> (state_delta, text, escalate)."""

    def compute(self, state: dict, ctx: InvocationContext) -> tuple[dict, Optional[str], bool]:
        raise NotImplementedError

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        delta, text, escalate = self.compute(dict(ctx.session.state), ctx)
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta=delta, escalate=escalate or None),
            content=types.Content(role="model", parts=[types.Part(text=text)]) if text else None,
        )


class IntakePrep(CodeStep):
    """Step 2: safety check, scrub personal info, find the block, count days to hearing."""

    def compute(self, state, ctx):
        intake: dict[str, Any] = dict(state.get("intake") or {})
        raw = _user_text(ctx)
        today = config.today()
        safety = check_safety(f"{raw}\n{intake.get('hazard_summary', '')}", intake.get("hazards"))
        loc = locate(intake.get("address_text", ""))
        days = None
        if intake.get("hearing_date"):
            try:
                days = (date.fromisoformat(intake["hearing_date"]) - today).days
            except ValueError:
                intake["hearing_date"] = None
        query = scrub(intake.get("search_query") or intake.get("hazard_summary") or raw)
        case = {**intake, **loc, "intake_date": today.isoformat(), "days_to_hearing": days,
                "search_query": query}
        delta = {"case": case, "safety": safety, "verify_attempts": 0, "verifier_feedback": "",
                 "brief_draft": None, "best_draft": None, "brief": None}
        return delta, None, False


class EvidenceStep(CodeStep):
    """Step 3a: vector search + eligibility rules (the custom tool)."""

    def compute(self, state, ctx):
        case = state["case"]
        result = search_corroborating_complaints(case["search_query"], case.get("lat"), case.get("lng"))
        return {"evidence": result}, None, False


class ContextStep(CodeStep):
    """Step 3b: tract rent burden + modeled filings (4 quarters summed first)."""

    def compute(self, state, ctx):
        return {"tract": tract_context(state["case"].get("census_tract_geoid"))}, None, False


class LegalStep(CodeStep):
    """Step 4a: which laws apply, including statute clocks."""

    def compute(self, state, ctx):
        return {"statutes": check_statutes(state["case"], state["evidence"])}, None, False


class ReliefStep(CodeStep):
    """Step 4b: fund verdicts with what is still to confirm."""

    def compute(self, state, ctx):
        return {"relief": check_relief_eligibility(state["case"], state["evidence"])}, None, False


class Verifier(CodeStep):
    """Step 6: check the LLM draft; pass -> assemble final brief and exit the loop."""

    def compute(self, state, ctx):
        draft = state.get("brief_draft") or {}
        attempts = int(state.get("verify_attempts") or 0) + 1
        issues = verify_draft(draft, evidence=state["evidence"], statutes=state["statutes"],
                              relief=state["relief"])
        best = state.get("best_draft")
        if best is None or len(issues) < len(best["issues"]):
            best = {"draft": draft, "issues": issues}
        if issues and attempts < MAX_VERIFY_ATTEMPTS:
            feedback = "Your previous draft failed these checks. Fix every one:\n- " + "\n- ".join(issues)
            return {"verify_attempts": attempts, "verifier_feedback": feedback, "best_draft": best}, None, False
        draft, issues = best["draft"], best["issues"]  # last try failed too: keep the draft with fewer issues
        brief = assemble_brief(case=state["case"], safety=state["safety"], evidence=state["evidence"],
                               tract=state["tract"], statutes=state["statutes"], relief=state["relief"],
                               draft=draft, issues=issues, attempts=attempts)
        return {"verify_attempts": attempts, "brief": brief}, render_markdown(brief), True
