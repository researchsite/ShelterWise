# Team plan and ownership

Scale this plan to the actual team. One person may own more than one workstream.

| Role | Responsibility | Deliverable |
|---|---|---|
| Product / architecture lead | Scope, contracts, integration, risk decisions | End-to-end flow and acceptance |
| Data engineer | Ingest, normalize, validate, model data | Reproducible BigQuery tables |
| Agent engineer | ADK/Gemini orchestration and tool contracts | Working agent flow |
| Retrieval/evidence engineer | Filters, embeddings, vector search, citations | Tested evidence retrieval |
| Frontend engineer | Case workspace and brief UI | Demo-ready interface |
| Legal/resources researcher | Official legal/program sources | Curated, cited reference set |
| QA / red-team | Decoys, edge cases, safety, claim checks | Test report and fixes |
| Demo storyteller | Scenario, script, slides, timing | Clear 3–4 minute demo |

## Integration contract

Agree on these shared objects early:

- `IntakeFacts`
- `EvidenceQuery`
- `EvidenceRecord`
- `LegalResource`
- `EvidenceGap`
- `StabilizationBrief`

Keep field names and status enums in one shared schema file in the implementation repo. Do not let frontend and backend independently invent payload shapes.

## Team lead responsibilities

- Lock the metro and scenario.
- Confirm challenge requirements from the source repository.
- Keep scope to one end-to-end path.
- Run integration checkpoints.
- Protect time for validation and demo rehearsal.
