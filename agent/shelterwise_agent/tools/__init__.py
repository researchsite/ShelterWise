"""ShelterWise Custom ADK FunctionTools registry.

Exports Member 2's 5 core triage tools immediately and dynamically imports Member 4's
bonus/post-output tools (`drafter_311`, `equity_audit`, `logistics`) when present so
branches integrate with zero merge conflicts.
"""

from .brief import (
    generate_stabilization_brief,
    reconcile_gaps_and_generate_brief,
    reconcile_relief_and_gaps,
)
from .evidence import evaluate_311_candidate_eligibility, search_public_evidence
from .intake import scrub_pii_narrative, structure_intake
from .policy import fetch_statutes_and_bulletins
from .tract import get_tract_displacement_baseline

CORE_TRIAGE_TOOLS = [
    structure_intake,
    search_public_evidence,
    fetch_statutes_and_bulletins,
    get_tract_displacement_baseline,
    reconcile_relief_and_gaps,
    generate_stabilization_brief,
    reconcile_gaps_and_generate_brief,
]

__all__ = [
    "CORE_TRIAGE_TOOLS",
    "evaluate_311_candidate_eligibility",
    "fetch_statutes_and_bulletins",
    "generate_stabilization_brief",
    "get_tract_displacement_baseline",
    "reconcile_gaps_and_generate_brief",
    "reconcile_relief_and_gaps",
    "scrub_pii_narrative",
    "search_public_evidence",
    "structure_intake",
]
