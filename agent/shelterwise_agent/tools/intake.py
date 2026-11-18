"""Tool 1 (`structure_intake`): Life-safety gate, PII scrubbing, SF GEOID hygiene & urgency clock."""

from datetime import date, datetime
import hashlib
import re
from typing import Any

from ..config import (
    ToolContext,
    get_metro_metadata,
    normalize_geoid_11,
)
from ..schemas import (
    IntakeFacts,
    SafetyAlert,
    UrgencyTier,
    assert_no_audit_columns,
)

# Exact idempotent PII scrubbing patterns aligned with Section 6 of c_housing_01_load_explore.ipynb
_RE_NAME = re.compile(
    r"(?i)\b(my\s+name\s+is\s+|i\s+am\s+|tenant\s+name\s*[:\-]?\s*|property\s+manager,?\s+)"
    r"[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,2}"
)
_RE_PLATE = re.compile(r"(?i)(license\s+plate\s*#?\s*)[A-Z0-9\-]+")
_RE_UNIT = re.compile(
    r"(?i)\b(dwelling\s+unit|apt\.?|apartment|unit|room|rm\.?|suite|ste\.?)\s*[:#]?\s*"
    r"\d+[A-Za-z]?(?:\s*(?:,|and)\s*\d+[A-Za-z]?)*"
)
_RE_BLOCK_GUARD = re.compile(r"(?i)\b(\d{2,5})\s+Block\b")
_RE_EXACT_ADDR = re.compile(
    r"(?i)\b(\d{2,5})(?:\s*[/\-]\s*\d{2,5})?\s+"
    r"([A-Za-z0-9.\-]+(?:\s+[A-Za-z0-9.\-]+){0,2}\s+"
    r"(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Ln|Lane|Ct|Court|Way|Pl|Place)\b)"
)
_RE_SVC_ADDR = re.compile(r"(?i)(service\s+address:\s*)\d{2,5}\b")
_RE_PHONE = re.compile(r"\b(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b")
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

_BLOCK_EXTRACT_RE = re.compile(
    r"(?i)\b(\d{2,5})\s+block(?:\s+of)?(?:\s+([A-Za-z0-9.\-]+(?:\s+[A-Za-z0-9.\-]+){0,2}))?"
)
_GEOID_IN_TEXT_RE = re.compile(r"\b(0?\d{10})\b")


def scrub_pii_narrative(text: str) -> str:
    """Scrub caller names, apartment numbers, exact street numbers, phones, emails, and plates."""
    if not text:
        return ""
    cleaned = str(text).replace("\ufffd", "'")
    cleaned = _RE_NAME.sub(r"\1[REDACTED NAME]", cleaned)
    cleaned = _RE_PLATE.sub(r"\1[REDACTED PLATE]", cleaned)
    cleaned = _RE_UNIT.sub(r"\1 [REDACTED UNIT]", cleaned)
    cleaned = _RE_BLOCK_GUARD.sub(r"\1__A4I_BLOCK__", cleaned)
    cleaned = _RE_EXACT_ADDR.sub(r"[REDACTED STREET NUMBER] \2", cleaned)
    cleaned = cleaned.replace("__A4I_BLOCK__", " Block")
    cleaned = _RE_SVC_ADDR.sub(r"\1[REDACTED STREET NUMBER]", cleaned)
    cleaned = _RE_PHONE.sub("[REDACTED PHONE]", cleaned)
    cleaned = _RE_EMAIL.sub("[REDACTED EMAIL]", cleaned)
    cleaned = _RE_SSN.sub("[REDACTED ID]", cleaned)
    return cleaned.strip()


def detect_immediate_safety(narrative: str, metro: str) -> SafetyAlert:
    """Detect acute life-safety signals requiring immediate emergency guidance before triage."""
    lower = narrative.lower()
    signals: list[str] = []

    has_water = any(
        w in lower for w in ("leak", "leaking", "dripping", "water", "flooding", "soaked", "wet")
    )
    has_elec = any(
        w in lower
        for w in (
            "fuse",
            "breaker",
            "electrical",
            "wiring",
            "outlet",
            "socket",
            "panel",
            "subpanel",
            "spark",
            "arcing",
        )
    )
    if (has_water and has_elec) or any(
        w in lower for w in ("sparking", "live wire", "exposed wire", "electrical fire", "arcing")
    ):
        signals.append("electrical_water_or_shock_hazard")

    if any(w in lower for w in ("gas leak", "smell gas", "natural gas", "carbon monoxide", "co alarm")):
        signals.append("gas_or_carbon_monoxide_hazard")

    if any(w in lower for w in ("active fire", "smoke filling", "ceiling collapsed", "roof caving")):
        signals.append("fire_or_structural_collapse_hazard")

    if any(w in lower for w in ("raw sewage", "sewage backup", "feces", "sewer overflow")):
        signals.append("raw_sewage_biohazard")

    if not signals:
        return SafetyAlert(immediate_danger=False)

    contacts = ["911 (Immediate fire, gas, or electrocution danger)"]
    if metro == "San Francisco":
        contacts.extend(
            [
                "SF 311 / Dept. of Building Inspection (DBI) Emergency Line: 311 or (415) 558-6088",
                "PG&E 24-Hour Gas/Electrical Emergency: 1-800-743-5000",
            ]
        )
    else:
        contacts.append(f"{metro} Municipal 311 / Emergency Code Enforcement")

    guidance = (
        "URGENT LIFE-SAFETY ALERT: Active hazard detected ("
        + ", ".join(signals)
        + "). Prioritize physical safety before paperwork: do NOT touch wet fuse/breaker boxes, "
        "exposed wiring, or standing water near outlets; evacuate immediately if smelling gas, "
        "seeing smoke/sparks, or facing structural collapse, and contact emergency services now."
    )
    return SafetyAlert(
        immediate_danger=True,
        triggered_signals=signals,
        emergency_guidance=guidance,
        local_emergency_contacts=contacts,
    )


_ISSUE_RULES: list[tuple[str, tuple[str, ...], str]] = [
    (
        "heating_loss",
        ("no heat", "cold radiator", "radiators", "ice cold", "stone cold", "boiler", "freezing", "heater"),
        "residential heating failure cold radiators inadequate heat below code minimum",
    ),
    (
        "electrical_water_hazard",
        ("fuse", "breaker", "electrical", "wiring", "outlet", "spark", "arcing"),
        "water leak ceiling intrusion onto electrical breaker fuse panel wiring hazard",
    ),
    (
        "water_intrusion_leak",
        ("leak", "leaking", "dripping", "roof leak", "ceiling", "water intrusion"),
        "active ceiling roof plumbing water leak intrusion residential apartment",
    ),
    (
        "mold_dampness",
        ("mold", "mildew", "black mold", "damp", "moisture", "fungus"),
        "severe indoor mold dampness chronic moisture residential habitability",
    ),
    (
        "plumbing_sewage",
        ("sewage", "sewer", "toilet", "backed up", "no hot water", "plumbing", "greywater"),
        "raw sewage backup plumbing overflow lack of hot water sanitary hazard",
    ),
    (
        "pest_infestation",
        ("rodent", "rat", "mice", "roach", "cockroach", "bedbug", "vermin"),
        "severe rodent vermin cockroach infestation unsanitary residential condition",
    ),
    (
        "nonpayment_eviction_notice",
        ("nonpayment", "3-day", "three-day", "pay or quit", "unlawful detainer", "eviction", "hearing", "arrears", "summons"),
        "",
    ),
    (
        "retaliation_or_lockout",
        ("retaliat", "lockout", "locked out", "shut off utilities", "threatened to call"),
        "",
    ),
]


def _extract_categories_and_search_query(scrubbed_text: str) -> tuple[list[str], str]:
    lower = scrubbed_text.lower()
    categories: list[str] = []
    search_clauses: list[str] = []
    for cat, keywords, expansion in _ISSUE_RULES:
        if any(kw in lower for kw in keywords):
            categories.append(cat)
            if expansion:
                search_clauses.append(expansion)
    if not categories:
        categories.append("general_habitability_or_housing_distress")
    if not search_clauses:
        search_clauses.append(scrubbed_text[:240])
    else:
        search_clauses.append(scrubbed_text[:180])
    return categories, " ".join(search_clauses).strip()


def _extract_block_hint(narrative: str, explicit_hint: str) -> str:
    if explicit_hint and explicit_hint.strip():
        return explicit_hint.strip()
    m = _BLOCK_EXTRACT_RE.search(narrative)
    if not m:
        return ""
    num = m.group(1)
    street = (m.group(2) or "").strip()
    # Trim trailing stopwords if regex captured "in her" etc.
    if street.lower() in {"in", "of", "near", "on", "at", "and"} or street.lower().startswith("in "):
        street = ""
    return f"{num} Block {street}".strip()


def _compute_urgency_tier(narrative: str, hearing_or_deadline_date: str) -> UrgencyTier:
    combined = f"{narrative} {hearing_or_deadline_date}".lower()
    if hearing_or_deadline_date.strip():
        try:
            target = date.fromisoformat(hearing_or_deadline_date.strip()[:10])
            delta = (target - date.today()).days
            if delta <= 4:
                return "immediate_72h"
            if delta <= 10:
                return "urgent_7d"
            return "standard_30d"
        except ValueError:
            pass

    if any(
        p in combined
        for p in (
            "monday",
            "tomorrow",
            "tonight",
            "72 hour",
            "48 hour",
            "24 hour",
            "3-day",
            "three-day",
            "in 2 days",
            "in 3 days",
            "this week",
        )
    ):
        return "immediate_72h"
    if any(p in combined for p in ("next week", "5-day", "7 days", "10 days")):
        return "urgent_7d"
    if any(p in combined for p in ("30-day", "60-day", "next month")):
        return "standard_30d"
    return "unspecified"


def _build_reported_facts(scrubbed_narrative: str) -> list[str]:
    parts = [
        p.strip(" .;")
        for p in re.split(r"(?<=[.!?])\s+|\s*;\s*", scrubbed_narrative)
        if p and len(p.strip()) >= 6
    ]
    if not parts:
        return [f"Tenant reports: {scrubbed_narrative} [Tenant-Reported — Unverified]"]
    return [f"{p}. [Tenant-Reported — Unverified]" for p in parts[:6]]


def structure_intake(
    narrative: str,
    metro: str = "San Francisco",
    block_address_hint: str = "",
    census_tract_geoid: str = "",
    hearing_or_deadline_date: str = "",
    has_written_notice: bool = False,
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Structures a messy tenant or paralegal crisis narrative into typed IntakeFacts.

    Runs an immediate life-safety check, scrubs PII before downstream embedding,
    preserves 11-character string census tract GEOIDs (including San Francisco's '06'
    leading zero), classifies habitability & eviction urgency, and preserves original
    allegations strictly as tenant-reported facts.

    Args:
        narrative: Plain-language description of the tenant's housing conditions and notice.
        metro: Target metropolitan corridor (defaults to 'San Francisco').
        block_address_hint: Optional 100-block location (e.g., '400 Block Ellis St').
        census_tract_geoid: Optional 11-digit string census tract GEOID (e.g., '06075012401').
        hearing_or_deadline_date: Optional court hearing or notice expiration date/day.
        has_written_notice: Whether a physical/written eviction or nonpayment notice was confirmed.

    Returns:
        Dictionary with 'status': 'success', 'immediate_safety_flag', 'intake_facts',
        and 'semantic_search_query'.
    """
    if not narrative or not narrative.strip():
        return {
            "status": "error",
            "error_message": "Tenant intake narrative cannot be empty.",
        }

    try:
        meta = get_metro_metadata(metro)
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}

    metro_name = meta["metro"]
    clean_geoid = ""
    if census_tract_geoid.strip():
        try:
            clean_geoid = normalize_geoid_11(census_tract_geoid)
        except ValueError as exc:
            return {"status": "error", "error_message": str(exc)}
    else:
        m_geo = _GEOID_IN_TEXT_RE.search(narrative)
        if m_geo:
            clean_geoid = normalize_geoid_11(m_geo.group(1))

    scrubbed = scrub_pii_narrative(narrative)
    safety = detect_immediate_safety(narrative, metro_name)
    categories, semantic_query = _extract_categories_and_search_query(scrubbed)
    resolved_block = _extract_block_hint(scrubbed, block_address_hint)
    urgency = _compute_urgency_tier(narrative, hearing_or_deadline_date)

    notice_mentioned = has_written_notice or ("nonpayment_eviction_notice" in categories)
    short_hash = hashlib.sha256(f"{metro_name}:{scrubbed}".encode("utf-8")).hexdigest()[:6].upper()
    today_str = datetime.now().strftime("%Y-%m-%d")
    case_ref = f"SW-{meta['state_code']}-{today_str.replace('-', '')}-{short_hash}"

    unknowns: list[str] = []
    questions: list[str] = []
    if not resolved_block and not clean_geoid:
        unknowns.append("100-block street address or 11-digit census tract GEOID")
        questions.append(
            "What 100-block street address is the building on (do not include apartment number)?"
        )
    if notice_mentioned and not hearing_or_deadline_date.strip():
        unknowns.append("Exact court hearing date or notice expiration date")
        questions.append(
            "What exact date and time is listed on the notice or court summons?"
        )
    unknowns.extend(
        [
            "Whether landlord/management received dated written repair notice (text, email, letter)",
            "Unit-level dated photos/videos and current lease / rent ledger",
            "Household gross income / Area Median Income (AMI) documentation for relief screening",
        ]
    )
    questions.append(
        "Did the tenant text, email, or message the landlord about these conditions, and do they have screenshots?"
    )

    facts_model = IntakeFacts(
        case_ref=case_ref,
        metro=metro_name,
        state_code=meta["state_code"],
        state_fips=meta["state_fips"],
        prepared_date=today_str,
        raw_tenant_narrative=narrative.strip(),
        scrubbed_narrative=scrubbed,
        semantic_search_query=semantic_query,
        reported_facts=_build_reported_facts(scrubbed),
        issue_categories=categories,
        block_address_hint=resolved_block,
        census_tract_geoid=clean_geoid,
        has_written_notice=notice_mentioned,
        hearing_or_deadline_date=hearing_or_deadline_date.strip(),
        urgency_tier=urgency,
        safety_alert=safety,
        unknowns=unknowns,
        clarification_questions=questions,
    )

    facts_dict = facts_model.model_dump()
    assert_no_audit_columns(facts_dict)

    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["intake_facts"] = facts_dict

    return {
        "status": "success",
        "immediate_safety_flag": safety.immediate_danger,
        "immediate_safety_guidance": safety.emergency_guidance,
        "semantic_search_query": semantic_query,
        "intake_facts": facts_dict,
    }
