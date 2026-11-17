# ShelterWise

**From housing distress to a path toward stability.**

ShelterWise is an AI-assisted housing stability navigator that turns a tenant's account of a housing problem into an evidence-backed **Tenant Stabilization Brief** for review by a qualified housing advocate, paralegal, or attorney.

> This repository is a hackathon starter kit. It is a planning baseline, not legal advice and not a determination of legal rights or program eligibility.

## What we are building

A guided case workspace that helps a tenant or advocate:
1. Capture the tenant's situation in plain language.
2. Find relevant public evidence, such as municipal 311 complaints and neighborhood housing context.
3. Identify potentially relevant statutes, procedures, and rental-assistance resources.
4. Surface missing evidence and practical next steps.
5. Generate a cited, reviewable brief.

**Core product principle:** public records can corroborate context; they do not prove what happened inside a tenant's unit.

## Start here

1. Read [`docs/PRODUCT_BRIEF.md`](docs/PRODUCT_BRIEF.md).
2. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
3. Agree on the initial metro, scenario, and data sources using [`docs/DECISIONS_AND_ASSUMPTIONS.md`](docs/DECISIONS_AND_ASSUMPTIONS.md).
4. Assign owners using [`docs/TEAM_PLAN.md`](docs/TEAM_PLAN.md).
5. Each owner starts with the matching prompt in [`prompts/`](prompts/).
6. Follow [`docs/SPRINT_PLAN.md`](docs/SPRINT_PLAN.md) and validate against [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md).

## Suggested first demo

A tenant reports no heat, water near an electrical outlet, and a notice to pay or leave. ShelterWise:
- structures the narrative and identifies urgent safety signals;
- searches for relevant, open, residential 311 records near the supplied location;
- explicitly distinguishes corroborating public records from proof of the tenant's own conditions;
- shows potentially relevant legal and assistance resources with citations and review flags;
- identifies missing evidence and suggests safe, practical documentation steps;
- generates a Tenant Stabilization Brief for a human reviewer.

## Repository map

```text
ShelterWise/
├── README.md
├── docs/
│   ├── PRODUCT_BRIEF.md
│   ├── USER_JOURNEY.md
│   ├── ARCHITECTURE.md
│   ├── DATA_AND_SOURCES.md
│   ├── RETRIEVAL_AND_EVIDENCE.md
│   ├── LEGAL_AND_SAFETY_GUARDRAILS.md
│   ├── TENANT_STABILIZATION_BRIEF.md
│   ├── UI_SPEC.md
│   ├── TEAM_PLAN.md
│   ├── SPRINT_PLAN.md
│   ├── DEMO_SCRIPT.md
│   ├── ACCEPTANCE_CRITERIA.md
│   └── DECISIONS_AND_ASSUMPTIONS.md
├── prompts/
│   ├── 00_team_lead.md
│   ├── 01_data_engineer.md
│   ├── 02_agent_engineer.md
│   ├── 03_frontend_engineer.md
│   ├── 04_retrieval_evidence_engineer.md
│   ├── 05_legal_resources_researcher.md
│   ├── 06_qa_red_team.md
│   └── 07_demo_storyteller.md
└── slides/
    └── ShelterWise_Team_Pitch.pptx
```

## Technology direction

The challenge brief should be treated as the source of truth for required frameworks and deployment. The current proposed direction is Google ADK + Gemini, MCP for tool access, BigQuery for structured data and vector search, and Cloud Run or the challenge-approved agent runtime. Confirm exact APIs, dataset names, credentials, and deployment requirements from the challenge repository before implementation.

## Working agreements

- Keep the MVP narrow: one orchestrating agent and a small number of focused tools.
- Use real public data where possible; label mock/demo data clearly.
- Preserve source identifiers and citations end-to-end.
- Never treat semantic similarity as proof of legal eligibility.
- Never rank individual tenants by race, ethnicity, or other protected traits.
- Do not use audit/decoy fields in retrieval or ranking.
- Every generated brief is a draft for human review, never an automated legal conclusion.
