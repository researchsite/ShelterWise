"""Which of the 3 SF / CA laws apply. Clocks are checked in code, never guessed."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from .. import config
from ..data import Repo, get_repo
from ..schemas import StatuteFinding

RULES_PATH = Path(__file__).resolve().parents[1] / "rules" / "statutes_sf.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text())


def _citation_clock(spec: dict, case: dict, evidence: dict, today: date) -> tuple[str, str, str | None]:
    covered, have = set(spec["hazards"]), set(case.get("hazards") or [])
    clock = int(spec["clock_days"])
    if have and not (covered & have):
        return "NOT_APPLICABLE", f"Reported conditions are not covered ({', '.join(sorted(covered))}).", None
    dated = [h for h in evidence.get("kept", []) if h.get("created_date")]
    if dated:
        first = min(dated, key=lambda h: h["created_date"])
        opened = date.fromisoformat(first["created_date"])
        days_open = (today - opened).days
        if days_open <= clock:
            recheck = opened + timedelta(days=clock + 1)
            return ("NOT_YET",
                    f"Block-level case {first['request_id']} opened {opened.isoformat()} ({days_open} days ago). "
                    f"This bar applies only after a citation stays unabated more than {clock} days.",
                    recheck.isoformat())
        return ("APPLIES_IF",
                f"Block-level case {first['request_id']} has been open {days_open} days (> {clock}). "
                f"Applies if that citation covers her unit.", None)
    if case.get("tenant_has_own_dbi_case"):
        return ("APPLIES_IF", f"Applies if her own citation has stayed unabated more than {clock} days "
                              f"(confirm the citation date).", None)
    return ("NOT_YET", f"Needs an official citation unabated for more than {clock} days; none found nearby. "
                       f"Filing a 311 / DBI request now starts the clock.", None)


def _tenant_complained(spec: dict, case: dict, evidence: dict, today: date):
    window = spec["window_days"]
    if case.get("tenant_complained_to_city") is True:
        return "APPLIES", f"She complained to the city; protected for {window} days after the complaint.", None
    if case.get("tenant_complained_to_city") is False:
        return "NOT_YET", "Protection starts once she files a complaint (e.g. the 311 / DBI request).", None
    return "APPLIES_IF", f"Applies if she herself complained to the city within the last {window} days.", None


def _facing_eviction(spec: dict, case: dict, evidence: dict, today: date):
    if case.get("case_type") in ("nonpayment", "no_fault") or case.get("hearing_date"):
        return "APPLIES", "Residential eviction case pending: just-cause rules and a city-funded lawyer.", None
    return "APPLIES_IF", "Applies once an eviction (unlawful detainer) case is filed.", None


_RULES = {"citation_clock": _citation_clock, "tenant_complained": _tenant_complained,
          "facing_eviction": _facing_eviction}


def check_statutes(case: dict, evidence: dict, repo: Repo | None = None, today: date | None = None) -> list[dict]:
    repo = repo or get_repo()
    today = today or config.today()
    rules = load_rules()["statutes"]
    out = []
    for s in repo.statutes():
        spec = rules.get(s["statute_section_id"])
        if not spec:
            continue
        verdict, why, recheck = _RULES[spec["rule"]](spec, case, evidence, today)
        out.append(StatuteFinding(
            statute_section_id=s["statute_section_id"], code_citation=s["code_citation"],
            ordinance_title=s["ordinance_title"], verdict=verdict, why=why,
            key_protection=s["raw_statute_text"], recheck_on=recheck,
        ).model_dump(mode="json"))
    order = {"APPLIES": 0, "APPLIES_IF": 1, "NOT_YET": 2, "NOT_APPLICABLE": 3}
    out.sort(key=lambda f: order[f["verdict"]])
    return out
