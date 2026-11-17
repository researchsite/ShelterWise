# Member 3 (Rohith) Implementation & Rebase Notes

## 1. Scope & Role
* **Role**: Member 3 — ADK Multi-Agent Tree & Managed MCP
* **Branch**: `rohith`
* **Pull Request**: [#3](https://github.com/researchsite/ShelterWise/pull/3) (targeting `main`)

---

## 2. Rebase on Merged PR #4 (Member 2 Tools)
PR #4 (`researchsite/shiva_stuff`) was merged into `main` (commit `2f28ebd`), delivering:
* `agent/shelterwise_agent/tools/` (`intake.py`, `evidence.py`, `policy.py`, `tract.py`, `brief.py`)
* `agent/shelterwise_agent/schemas.py`
* `agent/shelterwise_agent/config.py`
* `agent/shelterwise_agent/db/` (`bigquery_client.py`)
* `agent/requirements.txt`

### Clean Rebase Strategy:
1. Rebased `rohith` cleanly on top of `origin/main` (`2f28ebd`).
2. Strictly preserved all files in `agent/shelterwise_agent/tools/`, `schemas.py`, `config.py`, and `db/` without overrides or conflicts.
3. Member 3's changes are strictly limited to Member 3 assigned deliverables.

---

## 3. Changes Made by Member 3

### A. Google-managed BigQuery `McpToolset` (`agent/shelterwise_agent/mcp/bigquery_mcp.py`)
* Implemented `get_bigquery_mcp_toolset(project_id=None)` using ADK `McpToolset` and `StreamableHTTPConnectionParams`.
* Targets `https://bigquery.googleapis.com/mcp` with `X-Goog-User-Project` header, integrating with `ShelterWiseSettings`.

### B. ADK Multi-Agent Tree Hierarchy (`agent/shelterwise_agent/agent.py`)
* **Root Coordinator**: `shelterwise_navigator` (`LlmAgent`, `gemini-2.5-pro`) orchestrates incoming requests, triage pipeline, and specialist routing.
* **Core Pipeline**: `case_triage_pipeline` (`SequentialAgent`):
  1. `intake_structurer_agent` (`LlmAgent`): Life-safety hazard check and 11-digit GEOID normalization. Binds `tools.intake.structure_intake`.
  2. `corroboration_fanout` (3-way `ParallelAgent`):
     - `habitability_vector_agent`: BigQuery vector search and decoy trap filtering. Binds `tools.evidence.search_public_evidence`.
     - `statute_and_bulletin_agent`: Municipal ordinances and relief programs. Binds `tools.policy.fetch_statutes_and_bulletins`.
     - `tract_displacement_agent`: Displacement baseline with demographic firewall protection. Binds `tools.tract.get_tract_displacement_baseline`.
  3. `eligibility_and_brief_agent` (`LlmAgent`): Synthesizes facts, corroboration, and programs into the 9-section brief. Binds `tools.brief.reconcile_gaps_and_generate_brief`.
* **Specialist Sub-Agents**:
  1. `evidence_explainer_agent`: Explains why decoy candidates were excluded based on municipal business rules without mentioning benchmark labels.
  2. `equity_audit_agent`: Conducts metro-level Responsible AI cohort audits over `v_metro_equity_audit` protecting tenant demographic privacy.
  3. `hazard_311_drafter_agent`: Drafts official San Francisco Department of Building Inspection (DBI) emergency complaint memos.

### C. Package Exports (`agent/shelterwise_agent/__init__.py`)
* Exports `shelterwise_navigator`, `root_agent`, `case_triage_pipeline`, `corroboration_fanout`, and all sub-agents.

### D. Automated Unit Tests (`agent/tests/test_triage_pipeline.py`)
* 5 automated test cases validating pipeline structure, root coordinator routing, evidence explainer logic, 311 drafter formatting, and BigQuery MCP toolset initialization.

---

## 4. Verification Summary
* `pytest agent/tests/test_triage_pipeline.py`: **5 / 5 tests passed**.
* Zero merge conflicts with `main`.

### E. Session Management & Runner Factory (`create_runner`)
* **Agent Architecture Clarification**: In Google ADK, agents (`LlmAgent`, `SequentialAgent`, `ParallelAgent`) are declarative blueprints and do **not** take session parameters directly in their constructors.
* **Session Lifecycle**: State sharing across pipeline steps (`tool_context.state['intake_facts']`, `tool_context.state['evidence_pack']`, etc.) and multi-turn conversations are managed by the execution **`Runner`**.
* **`create_runner()`**: Implemented factory function in `agent.py` defaulting to `InMemorySessionService()`. This enables local testing, CLI execution, and FastAPI integration (Member 4) out-of-the-box, with the flexibility to swap in `VertexAiSessionService` or `DatabaseSessionService` for production Cloud Run deployments.
