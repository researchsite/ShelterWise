"""LLM agents: they read and write language. They never make yes/no decisions."""

from __future__ import annotations

import json

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from . import config
from .schemas import BriefDraft, IntakeFacts

NO_DEMOGRAPHICS = ("Never use or mention race, ethnicity, national origin or immigration status, even if the "
                   "intake mentions them.")


def _intake_parser_instruction(ctx: ReadonlyContext) -> str:
    return f"""You extract structured facts from a legal-aid intake note written by a paralegal.
Today is {config.today().isoformat()} ({config.today():%A}). The metro is {config.METRO}.

Rules:
- address_text: the street BLOCK only, e.g. "1000 block of Fillmore St". Never include unit numbers.
- hazards: pick from the allowed list only. "No heat / cold radiators" -> heat. "Leak / dripping" -> water_leak.
- search_query: rewrite ONLY the housing conditions the way a city building inspector would log them,
  e.g. "no heat in residential dwelling unit, indoor temperature below code minimum; water leaking from
  ceiling onto electrical panel". No names, no personal details.
- hearing_date: resolve relative dates ("Monday", "next Tuesday") against today, as YYYY-MM-DD.
- case_type: nonpayment if behind on rent / pay-or-quit; no_fault for owner move-in, Ellis Act, etc.
- Use null whenever a fact is not stated. Never guess income, case numbers or dates.
- tenant_has_own_dbi_case: true only if the note says the tenant has her own DBI / inspection case number.
- Never copy names, phone numbers, emails or unit numbers into any field.
- {NO_DEMOGRAPHICS}
"""


def build_intake_parser() -> LlmAgent:
    return LlmAgent(
        name="intake_parser",
        model=config.MODEL_FAST,
        description="Turns a plain-language intake into structured facts.",
        instruction=_intake_parser_instruction,
        output_schema=IntakeFacts,
        output_key="intake",
    )


def _facts_for_writer(state) -> dict:
    ev = state.get("evidence") or {}
    lookalikes = [h for h in ev.get("excluded", []) if set(h["reasons"]) - {"outside_radius"}][:5]
    case = {k: v for k, v in (state.get("case") or {}).items() if k not in ("lat", "lng")}
    return {
        "case": case,
        "safety_alerts": (state.get("safety") or {}).get("alerts", []),
        "kept_records": ev.get("kept", []),
        "excluded_lookalikes": [{k: h[k] for k in ("request_id", "reasons", "narrative")} for h in lookalikes],
        "has_open_residential_nearby": ev.get("has_open_residential_nearby"),
        "statutes": state.get("statutes"),
        "relief": state.get("relief"),
        "tract": state.get("tract"),
    }


def _brief_writer_instruction(ctx: ReadonlyContext) -> str:
    facts = json.dumps(_facts_for_writer(ctx.state), indent=1, default=str)
    feedback = ctx.state.get("verifier_feedback") or ""
    return f"""You write the narrative part of a Tenant Stabilization Brief for a supervising attorney.
All facts were computed by code and are below. Use ONLY these facts.

FACTS (JSON):
{facts}

Write:
1. summary: 3-5 plain sentences for the paralegal: what the city record shows, the most urgent action,
   and what is still unknown.
2. memo_markdown: an intake corroboration memo with sections: Client situation; Corroborating city records;
   Legal analysis; Relief referrals; Open questions; Evidentiary limits.
3. questions_for_tenant: short questions that would resolve the "to_confirm" items.

Hard rules:
- Cite 311 request IDs ONLY from kept_records. Never cite excluded_lookalikes IDs; you may describe them
  generally ("a commercial warehouse complaint was excluded").
- Use each statute's verdict exactly: APPLIES = applies; APPLIES_IF = state the condition; NOT_YET = say
  "not yet" and the recheck date; NOT_APPLICABLE = does not apply.
- Use each fund's verdict exactly. Never call a CONDITIONAL fund "eligible"; say what must be confirmed.
- Any eviction filing number must be described as a modeled estimate.
- Say clearly that 311 records show block-level conditions, not proof about her unit.
- No legal conclusions beyond the verdicts; the attorney decides.
- {NO_DEMOGRAPHICS}
{feedback}
"""


def build_brief_writer() -> LlmAgent:
    return LlmAgent(
        name="brief_writer",
        model=config.MODEL_STRONG,
        description="Writes the memo and summary from code-computed facts.",
        instruction=_brief_writer_instruction,
        include_contents="none",
        output_schema=BriefDraft,
        output_key="brief_draft",
    )


def _drafter_instruction(ctx: ReadonlyContext) -> str:
    case = json.dumps(ctx.state.get("case") or {}, default=str)
    return f"""You help a paralegal document a housing hazard that has NO open city inspection case yet,
so the tenant can file a San Francisco 311 / Department of Building Inspection (DBI) request.

Known case facts (may be empty): {case}

1. Ask at most 3 short questions if needed: what the hazard is, where in the unit, since when, and whether
   the landlord was told in writing (and when).
2. Then produce:
   - A ready-to-file 311 / DBI inspection request: category, block-level location (the tenant adds her
     unit number herself when filing), plain description, start date, landlord notice.
   - A safe photo checklist (date-stamped photos, thermometer reading for no-heat, never touch wet
     electrical equipment).
   - Interim help: funds that do NOT require an open case (SF ERAP, MEDA), with "confirm income" caveats.
   - Note: filing the request starts the clock for code-citation defenses and anti-retaliation protection.
3. Do not invent case numbers or promise outcomes. {NO_DEMOGRAPHICS}
When done, hand control back to the navigator.
"""


def build_inspection_request_drafter() -> LlmAgent:
    return LlmAgent(
        name="inspection_request_drafter",
        model=config.MODEL_FAST,
        description="Drafts a 311 / DBI inspection request when no open city case exists near the tenant.",
        instruction=_drafter_instruction,
    )
