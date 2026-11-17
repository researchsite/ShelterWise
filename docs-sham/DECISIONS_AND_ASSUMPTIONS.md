# Decisions and assumptions

This file separates current working choices from items the team must verify.

## Working choices

- Project name: **ShelterWise**.
- Product: AI-assisted Housing Stability Navigator.
- Output: Tenant Stabilization Brief for qualified human review.
- UX: guided case workspace, not a generic chatbot.
- Architecture: one ADK orchestrator with focused tools.
- Proposed stack: Gemini + Google ADK, MCP, BigQuery, vector search, Cloud Run/approved runtime.

## Verify against the official challenge repository

- Exact required framework/runtime versions.
- Required metros and datasets.
- Challenge data schema and hidden/planted decoy structure.
- Required BigQuery embedding/vector-search syntax and model availability.
- MCP requirements and expected server/tool interfaces.
- Deployment and submission requirements.
- Judging rubric and any bonus criteria.
- Whether public datasets are preloaded or must be ingested.

## Metro selection

Initial recommendation: Chicago for a compelling public-record evidence path and meaningful renter context. Treat all prior volume figures as planning notes only; validate them against the actual challenge datasets. Do not select a metro solely because of a headline count. Evaluate:
- source completeness and refresh;
- ability to demonstrate relevant evidence;
- geographic precision;
- quality of legal/resource sources;
- ability to test planted decoys.

## Open questions to resolve in first 20 minutes

1. Which metro offers the strongest complete end-to-end data path?
2. What is the smallest supported user scenario?
3. What are the canonical schemas for intake, evidence, legal resources, and brief?
4. Which tools are live versus mocked for the demo?
5. What exact challenge requirements must be demonstrated?
6. Who owns final integration and demo narration?

## Claims discipline

Do not present prior planning estimates as verified facts. Do not claim ShelterWise has prevented evictions, improved outcomes, or achieved measured impact during the hackathon unless supported by valid evaluation.
