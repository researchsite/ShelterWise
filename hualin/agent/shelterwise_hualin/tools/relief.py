"""Fund verdicts: ELIGIBLE only when every condition is confirmed.

any condition not_met -> INELIGIBLE
all conditions met    -> ELIGIBLE
otherwise             -> CONDITIONAL, with the list of what to confirm
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from .. import config
from ..data import Repo, get_repo
from ..schemas import ConditionCheck, ReliefVerdict

RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "funds_sf.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text())


def _bool_check(value, name: str, yes: str, no: str, ask: str) -> ConditionCheck:
    if value is True:
        return ConditionCheck(condition=name, status="met", detail=yes)
    if value is False:
        return ConditionCheck(condition=name, status="not_met", detail=no)
    return ConditionCheck(condition=name, status="unknown", detail=ask)


def _income_limit(limits: dict, pct: float, size) -> float | None:
    """Published MOHCD limit for this AMI tier and household size, or None if not in the chart."""
    tier = (limits or {}).get(int(pct)) or (limits or {}).get(str(int(pct)))
    if not tier or size is None:
        return None
    return tier.get(int(size)) or tier.get(str(int(size)))


def check_condition(cond: dict, case: dict, evidence: dict, limits: dict) -> ConditionCheck:
    t = cond["type"]
    if t == "residential_tenant":
        return _bool_check(case.get("is_residential_tenant"), t, "Residential tenant.",
                           "Not a residential tenant.", "Confirm she rents a residential unit.")
    if t == "own_open_dbi_case":
        if case.get("tenant_has_own_dbi_case") is True:
            return ConditionCheck(condition=t, status="met", detail="Tenant has her own open DBI case number.")
        if case.get("tenant_has_own_dbi_case") is False:
            return ConditionCheck(condition=t, status="not_met",
                                  detail="No DBI case on her unit yet. File a 311 / DBI inspection request first.")
        if evidence.get("has_open_residential_nearby"):
            ids = ", ".join(h["request_id"] for h in evidence.get("kept", []))
            return ConditionCheck(condition=t, status="unknown",
                                  detail=f"Open DBI case(s) on her block ({ids}); confirm one covers HER unit, "
                                         f"or get her own case number. Block evidence alone is not enough.")
        return ConditionCheck(condition=t, status="unknown",
                              detail="No open case found nearby. Ask if she has her own DBI case number; "
                                     "if not, file a 311 inspection request.")
    if t == "income_max_pct_ami":
        limit_pct = float(cond["value"])
        if case.get("income_pct_ami") is not None:
            pct = float(case["income_pct_ami"])
            return ConditionCheck(condition=t, status="met" if pct <= limit_pct else "not_met",
                                  detail=f"Household income about {pct:.0f}% AMI vs limit {limit_pct:.0f}%.")
        income, size = case.get("annual_income_usd"), case.get("household_size")
        cap = _income_limit(limits, limit_pct, size)
        if income is not None and cap:
            status = "met" if float(income) <= cap else "not_met"
            return ConditionCheck(condition=t, status=status,
                                  detail=f"Income ${float(income):,.0f} vs {limit_pct:.0f}% AMI limit ${cap:,.0f} "
                                         f"for a household of {size}.")
        hint = f" (household of {size} is not in the chart)" if income is not None and size else ""
        return ConditionCheck(condition=t, status="unknown",
                              detail=f"Confirm household income is at or below {limit_pct:.0f}% AMI "
                                     f"(MOHCD chart){hint}.")
    if t == "medical_or_wage_loss":
        return _bool_check(case.get("medical_or_wage_loss"), t, "Medical leave or wage loss reported.",
                           "No medical leave or wage loss.", "Ask about acute medical leave or wage loss.")
    if t == "facing_eviction":
        facing = case.get("case_type") in ("nonpayment", "no_fault") or bool(case.get("hearing_date"))
        return ConditionCheck(condition=t, status="met" if facing else "unknown",
                              detail="Eviction case pending." if facing else "Confirm an eviction case is filed.")
    if t == "hazard_in":
        wanted, have = set(cond["value"]), set(case.get("hazards") or [])
        if wanted & have:
            return ConditionCheck(condition=t, status="met", detail=f"Reported: {', '.join(sorted(wanted & have))}.")
        if have:
            return ConditionCheck(condition=t, status="not_met",
                                  detail=f"Covers only {', '.join(sorted(wanted))}.")
        return ConditionCheck(condition=t, status="unknown", detail=f"Covers {', '.join(sorted(wanted))}.")
    raise ValueError(f"Unknown condition type: {t}")


def check_relief_eligibility(case: dict, evidence: dict, repo: Repo | None = None) -> list[dict]:
    repo = repo or get_repo()
    rules = load_rules()
    limits = rules.get("income_limits_usd") or {}
    days = case.get("days_to_hearing")
    verdicts = []
    for b in repo.bulletins():
        spec = rules["programs"].get(b["bulletin_id"])
        if not spec:
            continue
        checks = [check_condition(c, case, evidence, limits) for c in spec["conditions"]]
        if any(c.status == "not_met" for c in checks):
            verdict = "INELIGIBLE"
        elif all(c.status == "met" for c in checks):
            verdict = "ELIGIBLE"
        else:
            verdict = "CONDITIONAL"
        urgent = spec["category"] == "legal_defense" and days is not None and days <= config.URGENT_HEARING_DAYS
        verdicts.append(ReliefVerdict(
            bulletin_id=b["bulletin_id"], program_name=b["program_name"],
            administering_agency=b["administering_agency"], amount=spec["amount"],
            intake_url=b["intake_url"], verdict=verdict, urgent=urgent, checks=checks,
            to_confirm=[c.detail for c in checks if c.status == "unknown"],
        ).model_dump(mode="json"))
    order = {"ELIGIBLE": 0, "CONDITIONAL": 1, "INELIGIBLE": 2}
    verdicts.sort(key=lambda v: (not v["urgent"], order[v["verdict"]]))
    return verdicts
