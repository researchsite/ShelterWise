"""The 6-step brief pipeline.

1 understand (LLM) -> 2 prepare (code) -> 3 gather (code, parallel)
-> 4 decide (code, parallel) -> 5 write (LLM) <-> 6 verify (code), max 2 rounds
"""

from __future__ import annotations

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from .code_agents import (MAX_VERIFY_ATTEMPTS, ContextStep, EvidenceStep, IntakePrep, LegalStep, ReliefStep,
                          Verifier)
from .llm_agents import build_brief_writer, build_intake_parser


def build_gather_and_decide() -> list:
    """Steps 2-4 (all code). Exposed separately so tests can run them without an LLM."""
    return [
        IntakePrep(name="intake_prep", description="Safety check, scrub personal info, locate block."),
        ParallelAgent(name="gather", description="311 evidence + tract context.", sub_agents=[
            EvidenceStep(name="evidence_agent", description="Vector search + eligibility rules."),
            ContextStep(name="context_agent", description="Tract rent burden + modeled filings."),
        ]),
        ParallelAgent(name="decide", description="Laws + fund verdicts.", sub_agents=[
            LegalStep(name="legal_agent", description="Which SF/CA laws apply, with clocks."),
            ReliefStep(name="relief_agent", description="Fund verdicts with what to confirm."),
        ]),
    ]


def build_brief_pipeline() -> SequentialAgent:
    return SequentialAgent(
        name="brief_pipeline",
        description=("Builds a verified Tenant Stabilization Brief from an intake. Pass the paralegal's full "
                     "intake text (plus any new facts) as the request."),
        sub_agents=[
            build_intake_parser(),
            *build_gather_and_decide(),
            LoopAgent(name="draft_and_verify", max_iterations=MAX_VERIFY_ATTEMPTS, sub_agents=[
                build_brief_writer(),
                Verifier(name="verifier", description="Checks the memo; assembles the final brief."),
            ]),
        ],
    )
