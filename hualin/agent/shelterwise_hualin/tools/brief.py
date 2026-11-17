"""Verify the LLM-written memo against code-computed facts, then assemble the final brief.

Facts (records, verdicts, laws, numbers) come from code. The LLM only writes the
summary, memo and questions; these checks stop it from over-claiming.
"""

from __future__ import annotations

import re

from .relief import load_rules as load_fund_rules

_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_ID = re.compile(r"\b[A-Z]{2,6}-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
_SECTION = re.compile(r"\b\d{4}\.\d\b")
_DEMOGRAPHIC = re.compile(r"\b(race|racial|ethnicity|ethnic|black|hispanic|latin[oax]|asian|indigenous|"
                          r"white|caucasian|audit_\w*)\b", re.I)
_HEDGE_STATUTE = ("not yet", "does not", "doesn't", "not apply", "not applicable", "once", "after",
                  "recheck", "until", "35")
_HEDGE_FUND = ("conditional", "if ", "once", "pending", "confirm", "may ", "might", "could", "not ",
               "ineligible", "verify", "need")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text or "") if s.strip()]


def verify_draft(draft: dict, *, evidence: dict, statutes: list[dict], relief: list[dict]) -> list[str]:
    text = "\n".join([draft.get("summary", ""), draft.get("memo_markdown", ""),
                      *draft.get("questions_for_tenant", [])])
    low_sents = [s.lower() for s in _sentences(text)]
    issues: list[str] = []

    kept_ids = {h["request_id"] for h in evidence.get("kept", [])}
    excluded_ids = {h["request_id"] for h in evidence.get("excluded", [])}
    known_other = {s["statute_section_id"] for s in statutes} | {r["bulletin_id"] for r in relief}
    record_prefixes = {i.split("-")[0] for i in kept_ids | excluded_ids}  # e.g. {"SF", ...} from this run
    for rid in sorted(set(_ID.findall(text))):
        if rid in kept_ids or rid in known_other:
            continue
        if rid in excluded_ids:
            issues.append(f"Cites {rid}, which was EXCLUDED by the rules. Only cite kept records.")
        elif rid.split("-")[0] in record_prefixes:
            issues.append(f"Cites {rid}, which is not in the evidence. Do not invent record IDs.")

    for s in statutes:
        if s["verdict"] not in ("NOT_YET", "NOT_APPLICABLE"):
            continue
        for sec in _SECTION.findall(s["code_citation"]):
            for sent in low_sents:
                if sec in sent and not any(h in sent for h in _HEDGE_STATUTE):
                    issues.append(f"Mentions § {sec} without saying it does not apply yet ({s['verdict']}).")
                    break

    names = {p_id: spec["short_name"].lower() for p_id, spec in load_fund_rules()["programs"].items()}
    for r in relief:
        if r["verdict"] == "ELIGIBLE":
            continue
        name = names.get(r["bulletin_id"], r["program_name"].lower())
        for sent in low_sents:
            if (name in sent or r["program_name"].lower() in sent) and re.search(r"\beligible\b", sent) \
                    and not any(h in sent for h in _HEDGE_FUND):
                issues.append(f"Calls {name} eligible, but it is {r['verdict']}; say what must be confirmed.")
                break

    for sent in low_sents:
        if "filing" in sent and re.search(r"\d", sent) and not re.search(r"model|estimat", sent):
            issues.append("Gives eviction filing numbers without saying they are modeled estimates.")
            break

    if "block" not in text.lower():
        issues.append("Must state that 311 evidence is block-level, not proof about her unit.")
    m = _DEMOGRAPHIC.search(text)
    if m:
        issues.append(f"Mentions demographic term '{m.group(0)}'. Demographics are never part of a case brief.")
    return issues


def _boundaries(evidence: dict, tract: dict) -> list[str]:
    out = ["311 records describe conditions on the 100-block, not her specific unit. Unit-level proof "
           "(her own DBI case, lease, photos) is still needed."]
    if tract.get("available"):
        out.append("Eviction filing counts are MODELED from county court baselines, not her court docket.")
    if not evidence.get("location_known"):
        out.append("Her block could not be located, so no record can be called 'nearby'.")
    if "local-keyword-standin" in evidence.get("retrieval_mode", ""):
        out.append("OFFLINE MODE: matches come from a keyword stand-in, not BigQuery vector search.")
    return out


def assemble_brief(*, case: dict, safety: dict, evidence: dict, tract: dict, statutes: list[dict],
                   relief: list[dict], draft: dict, issues: list[str], attempts: int) -> dict:
    lookalikes = [h for h in evidence.get("excluded", []) if set(h["reasons"]) - {"outside_radius"}]
    lookalikes.sort(key=lambda h: h["similarity_rank"])
    reason_counts: dict[str, int] = {}
    for h in evidence.get("excluded", []):
        for r in h["reasons"]:
            reason_counts[r] = reason_counts.get(r, 0) + 1

    to_confirm: list[str] = []
    for item in [*(t for r in relief for t in r["to_confirm"]),
                 *(s["why"] for s in statutes if s["verdict"] == "APPLIES_IF")]:
        if item not in to_confirm:
            to_confirm.append(item)

    passed = not issues
    memo = draft.get("memo_markdown", "")
    if not passed:
        memo = ("> ⚠ The drafted memo failed automatic checks and must be rewritten by staff:\n"
                + "\n".join(f"> - {i}" for i in issues) + "\n\n" + memo)
    next_steps = []
    if not evidence.get("has_open_residential_nearby"):
        next_steps.append("No open residential case near her block: draft a 311 / DBI inspection request "
                          "(ask me to help document the hazard).")
    return {
        "title": f"Tenant Stabilization Brief: {case.get('matched_block') or case.get('address_text') or 'location unknown'}",
        "intake_date": case.get("intake_date"),
        "hearing_date": case.get("hearing_date"),
        "days_to_hearing": case.get("days_to_hearing"),
        "safety_alerts": safety.get("alerts", []),
        "location": {k: case.get(k) for k in ("address_text", "matched_block", "lat", "lng",
                                               "location_source", "census_tract_geoid", "tract_source")},
        "evidence": {
            "retrieval_mode": evidence.get("retrieval_mode"),
            "radius_m": evidence.get("radius_m"),
            "has_open_residential_nearby": evidence.get("has_open_residential_nearby", False),
            "corroborating_records": evidence.get("kept", []),
            "excluded_lookalikes": lookalikes[:5],
            "excluded_count_by_reason": reason_counts,
        },
        "statutes": statutes,
        "relief": relief,
        "tract": tract,
        "evidentiary_boundary": _boundaries(evidence, tract),
        "to_confirm": to_confirm,
        "summary": draft.get("summary", ""),
        "memo_markdown": memo,
        "questions_for_tenant": draft.get("questions_for_tenant", []),
        "next_steps": next_steps,
        "verification": {"passed": passed, "issues": issues, "attempts": attempts},
    }


_REASON_LABEL = {"not_residential": "commercial / non-residential", "closed_abated": "closed: fixed",
                 "closed_no_violation": "closed: no violation", "closed_other": "closed",
                 "outside_radius": "too far away", "other_metro": "other city"}


def render_markdown(b: dict) -> str:
    L = []
    for a in b["safety_alerts"]:
        L.append(f"> 🚨 **SAFETY FIRST:** {a['message']}")
    if b["safety_alerts"]:
        L.append("")
    days = b.get("days_to_hearing")
    L.append(f"## {b['title']}" + (f" (hearing in {days} days)" if days is not None else ""))
    if b["summary"]:
        L += ["", b["summary"]]

    ev = b["evidence"]
    L += ["", "### 1. City records that support the tenant"]
    if ev["corroborating_records"]:
        L.append("| Request ID | Block | Status | Opened | Distance |")
        L.append("|---|---|---|---|---|")
        for h in ev["corroborating_records"]:
            dist = f"{h['meters_away']:.0f} m" if h.get("meters_away") is not None else "?"
            L.append(f"| {h['request_id']} | {h['block_address'].split(',')[0]} | {h['inspection_status']} "
                     f"| {h['created_date'] or '?'} | {dist} |")
        for h in ev["corroborating_records"][:2]:
            L.append(f"> \"{h['narrative'][:220]}\"")
    else:
        L.append("_No open residential complaint found near her block._")
    if ev["excluded_lookalikes"]:
        L += ["", "**Excluded look-alikes (similar text, but they don't count):**"]
        for h in ev["excluded_lookalikes"]:
            why = ", ".join(_REASON_LABEL.get(r, r) for r in h["reasons"] if r != "outside_radius") or "too far"
            L.append(f"- {h['request_id']} (similarity rank #{h['similarity_rank']}): "
                     f"\"{h['narrative'][:90]}…\" → *{why}*")

    L += ["", "### 2. Laws", "| Citation | Applies? | Why |", "|---|---|---|"]
    label = {"APPLIES": "**Yes**", "APPLIES_IF": "**Yes, if**", "NOT_YET": "**Not yet**",
             "NOT_APPLICABLE": "No"}
    for s in b["statutes"]:
        why = s["why"] + (f" Recheck on {s['recheck_on']}." if s.get("recheck_on") else "")
        L.append(f"| {s['code_citation']} | {label[s['verdict']]} | {why} |")

    L += ["", "### 3. Emergency help", "| Program | Verdict | Still to confirm |", "|---|---|---|"]
    for r in b["relief"]:
        flag = ", call first" if r["urgent"] else ""
        confirm = " · ".join(t.rstrip(".") for t in r["to_confirm"]) or "nothing"
        if r["verdict"] == "INELIGIBLE":
            confirm = " · ".join(c["detail"].rstrip(".") for c in r["checks"] if c["status"] == "not_met")
        L.append(f"| {r['program_name']}: {r['amount']} ({r['intake_url']}) | **{r['verdict']}**{flag} | {confirm} |")

    t = b["tract"]
    L += ["", "### 4. Neighborhood context"]
    if t.get("available"):
        L.append(f"- Tract {t['census_tract_geoid']}: severe rent burden {t['severe_rent_burden_households']} of "
                 f"{t['renter_households']} renter households ({t['severe_rent_burden_pct']}%), vs "
                 f"{t['metro_severe_rent_burden_pct']}% metro-wide")
        L.append(f"- Eviction filings: about {t['annual_filings_modeled']} per year *(MODELED estimate, "
                 f"{t['filings_percentile_in_metro']}th percentile in the metro)*")
    else:
        L.append(f"- {t.get('reason', 'Not available.')}")

    L += ["", "### 5. What this does NOT prove"] + [f"- {x}" for x in b["evidentiary_boundary"]]
    asks = b["to_confirm"] + [q for q in b["questions_for_tenant"] if q not in b["to_confirm"]]
    if asks:
        L += ["", "### 6. Ask the tenant / confirm"] + [f"- {x}" for x in asks]
    if b["next_steps"]:
        L += ["", "### Next steps"] + [f"- {x}" for x in b["next_steps"]]
    L += ["", "### 7. Draft intake memo (for attorney review)", "", b["memo_markdown"]]
    v = b["verification"]
    L += ["", f"_Checks: {'passed' if v['passed'] else 'FAILED'} after {v['attempts']} attempt(s) · "
              f"retrieval: {ev['retrieval_mode']}_"]
    return "\n".join(L)
