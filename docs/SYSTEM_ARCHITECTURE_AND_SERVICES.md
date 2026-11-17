# 🏛️ ShelterWise: Agent Architecture, Service Map & CLI Reference

This document provides a complete technical reference of the **11 autonomous Google ADK agents**, their **source code file paths**, the **Google Cloud services and APIs** leveraged, and every **CLI command** required to initialize, verify, run, and deploy ShelterWise.

---

## 1. Complete Agent Registry (`*_ag`)

Every agent in ShelterWise is implemented using the **Google Agent Development Kit (ADK)** and strictly follows the `*_ag` naming standard.

| Agent Name | Framework Class | Source File & Function | Model / Engine | Tools & Callables | Primary Mission & Responsibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`shelterwise_navigator_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `estimate_courthouse_transit`, `claim_or_update_case_task`, `query_bigquery_mcp` | **Root Coordinator**: Dispatches intakes to `case_triage_pipeline_ag`, handles conversational chat, manages Firestore optimistic concurrency locks, and provides court transit routing. |
| **`case_triage_pipeline_ag`** | `SequentialAgent` | `agent/shelterwise_agent/agent.py` | Deterministic Sequential | Sub-agents: `intake_structurer_ag` ➔ `corroboration_fanout_ag` ➔ `eligibility_and_brief_ag` | **Sequential Pipeline Orchestrator**: Executes the core 3-stage triage workflow in deterministic sequence. |
| **`intake_structurer_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `structure_intake`, `scrub_pii_narrative` (`tools/intake.py`) | **Intake & Life-Safety Guard**: Extracts claims verbatim, strips PII, normalizes 11-digit Census Tract GEOID (`06075...`), and triggers acute life-safety warnings for water/electrical hazards. |
| **`corroboration_fanout_ag`** | `ParallelAgent` | `agent/shelterwise_agent/agent.py` | Concurrent Fan-Out | Sub-agents: `habitability_vector_ag`, `statute_and_bulletin_ag`, `tract_displacement_ag` | **Parallel Fan-Out Orchestrator**: Executes municipal vector search, legal statute evaluation, and neighborhood displacement context simultaneously. |
| **`habitability_vector_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `search_public_evidence` (`tools/evidence.py`), `BQClient` (`db/bigquery_client.py`) | **Evidentiary Corroborator**: Queries BigQuery `AI.EMBED` + `VECTOR_SEARCH` and strictly filters out commercial, abated, and zero-violation decoy records using municipal rules. |
| **`statute_and_bulletin_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `fetch_statutes_and_bulletins` (`tools/policy.py`) | **Legal & Policy Specialist**: Identifies affirmative defenses (SF Housing Code § 701, Prop F Counsel) and monitors 35-day repair deadlines under Cal. Civ. Code § 1942.4. |
| **`tract_displacement_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `get_tract_displacement_baseline` (`tools/tract.py`) | **Neighborhood Context Specialist**: Queries 4-quarter modeled eviction baselines from `v_tract_stability_context` with a strict demographic firewall. |
| **`eligibility_and_brief_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `reconcile_gaps_and_generate_brief` (`tools/brief.py`) | **Brief Synthesizer & Gap Reconciler**: Synthesizes verified facts, open 311 records, and relief grants into the 9-section Tenant Stabilization Brief and generates the 8-item Attorney Review Checklist. |
| **`evidence_explainer_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `explain_excluded_evidence` (`agent.py`) | **Evidence Auditor**: Explains to advocates exactly why lookalike candidate records (e.g., commercial storefronts) were disqualified from court filings. |
| **`equity_audit_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `run_metro_equity_audit` (`db/bigquery_client.py`) | **Responsible AI Auditor**: Operates exclusively across aggregated census tract cohorts (`v_metro_equity_audit`) to identify "silent distress" tracts without individual demographic scoring. |
| **`hazard_311_drafter_ag`** | `LlmAgent` | `agent/shelterwise_agent/agent.py` | `gemini-2.5-flash` | `draft_311_inspection_request` (`tools/drafter_311.py`), `draft_311_complaint` | **Proactive Complaint Drafter**: Prepares formal SF DBI emergency inspection requests when zero public records exist on a block, unlocking relief fund prerequisites. |

---

## 2. Multi-Agent Hierarchy & Orchestration Flow

```
                      [ USER / PARALEGAL / ADVOCATE ]
                                     |
                                     v
                       +-----------------------------+
                       |  shelterwise_navigator_ag   |  <--- Root Coordinator
                       +-----------------------------+       (Firestore Lock & Chat)
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
+--------------------------+                   +--------------------------+
| case_triage_pipeline_ag  |                   | Follow-up Specialists    |
| (Sequential Execution)   |                   | - evidence_explainer_ag  |
+--------------------------+                   | - equity_audit_ag        |
             |                                 | - hazard_311_drafter_ag  |
             |                                 +--------------------------+
             +---> 1. intake_structurer_ag
             |        (PII Redaction, Safety Gate, 11-Digit GEOID)
             |
             +---> 2. corroboration_fanout_ag (Parallel Execution)
             |        |
             |        +---> habitability_vector_ag (BigQuery AI.EMBED + VECTOR_SEARCH)
             |        +---> statute_and_bulletin_ag (SF Housing § 701, Prop F, 1942.4)
             |        +---> tract_displacement_ag (v_tract_stability_context Firewall)
             |
             +---> 3. eligibility_and_brief_ag
                      (9-Section Defense Brief + 8-Item Attorney Review Checklist)
```

---

## 3. Google Cloud Services & Product Stack

ShelterWise deeply integrates 9 native Google Cloud technologies:

### 1. Google Cloud Run (Serverless Application Hosting)
- **Service Name**: `shelterwise`
- **Region**: `us-central1`
- **Active Revision**: `shelterwise-00006-r9h`
- **Live URL**: `https://shelterwise-335751565476.us-central1.run.app`
- **Configuration**: Containerized FastAPI server, min-instances 1 (zero cold starts), `--allow-unauthenticated`, multi-worker asynchronous Uvicorn event loop.

### 2. Google BigQuery (AI.EMBED & Vector Search)
- **Dataset**: `a4i_housing` in region `US`
- **Vector Search Engine**: `VECTOR_SEARCH` with brute-force cosine distance comparison over 768-dimensional embeddings.
- **Multimodal AI Embedding**: `AI.EMBED(..., connection_id => 'us.a4i-vertex', endpoint => 'gemini-embedding-2')`.
- **Views**:
  - `v_tract_stability_context`: Anonymized neighborhood stability indices firewalled against demographic fields.
  - `v_metro_equity_audit`: Aggregated tract-level cohort analysis identifying silent distress under-reporting.

### 3. Google Cloud Firestore (Optimistic Concurrency & Persistence)
- **Database**: `(default)` in region `nam5` (Firestore Native Mode).
- **Concurrency Mechanism**: `@firestore.transactional` atomic mutations utilizing an incrementing `lock_version` integer.
- **State Stored**: Case intake facts, corroborating evidence packs, legal briefs, and human-in-the-loop attorney review checklists.

### 4. Google Vertex AI (Foundation Models)
- **`gemini-2.5-flash`**: Drives all 11 LLM agents for low-latency reasoning, evidence synthesis, and conversational Q&A.
- **`gemini-embedding-2`**: Powers 768-dimensional vector representation of municipal 311 complaints and tenant narratives.

### 5. Google reCAPTCHA Enterprise (Abuse & Bot Prevention)
- **Endpoint**: `/api/recaptcha/verify`
- **Assessment**: Risk score evaluation (`score: 0.94`, human confidence high) protecting legal aid infrastructure from automated form submission attacks.

### 6. Google Maps & Places
- **Geospatial Proximity**: Interactive Leaflet/Google Maps visualization rendering a 400-meter legal evidentiary buffer.
- **Address Standardization**: Coarsens freeform tenant inputs into 100-block intervals and 11-digit Census Tract GEOIDs.
- **Transit Logistics**: MUNI Route 31/5 transit calculation to SF Superior Courthouse (400 McAllister St).

### 7. Google Cloud Speech-to-Text (Voice Intake)
- **Modality**: Acoustic transcription simulation for low-literacy tenants and advocates conducting phone intakes.

### 8. Google Cloud Storage (GCS Evidence Dropzone)
- **Dropzone**: Photo uploads (e.g. freezing thermometer, ceiling water intrusion) and legal PDF notices.

### 9. Google BigQuery Model Connection
- **Connection Resource**: `projects/335751565476/locations/us/connections/a4i-vertex`
- **Role**: Enables SQL-native Vertex AI `AI.EMBED` calls directly inside BigQuery queries.

---

## 4. Complete CLI Commands Reference

### A. Environment Setup & Dependencies
```bash
# Clone the repository
git clone https://github.com/researchsite/ShelterWise.git
cd ShelterWise

# Create and activate python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r agent/requirements.txt
```

### B. BigQuery Dataset & View Initialization
```bash
# Set project environment variables
export PROJECT_ID="qwiklabs-gcp-04-99fa355171e1"
export BIGQUERY_DATASET="a4i_housing"
export METRO_AREA="San Francisco"

# Execute BigQuery setup script
bash scripts/setup_bigquery.sh

# Or apply SQL DDL and analytical views directly via bq CLI:
bq query --use_legacy_sql=false \
  --project_id=$PROJECT_ID \
  < sql/setup_vector_and_views.sql
```

### C. Automated Test Suite Execution
```bash
# Run all unit tests (15 tests covering all 11 agents, decoy filters, and locks)
PYTHONPATH=".libs:agent:$PYTHONPATH" /opt/venv/bin/python3 -m unittest discover -s agent/tests -v
```

### D. Local Development Server
```bash
# Start local FastAPI server on port 8080
export PROJECT_ID="qwiklabs-gcp-04-99fa355171e1"
export BIGQUERY_DATASET="a4i_housing"
export METRO_AREA="San Francisco"
python3 agent/server.py
```

### E. Google Cloud Run Deployment
```bash
# Build and deploy container directly to Cloud Run
gcloud run deploy shelterwise \
  --source agent/ \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --set-env-vars "PROJECT_ID=qwiklabs-gcp-04-99fa355171e1,BIGQUERY_DATASET=a4i_housing,METRO_AREA=San Francisco,VERTEX_AI_LOCATION=us-central1" \
  --quiet
```

### F. Health Checks & Endpoint Probes
```bash
# Verify API Health
curl -s https://shelterwise-335751565476.us-central1.run.app/api/health

# Verify Hero Graphic Asset
curl -s -o /dev/null -w "%{http_code}\n" https://shelterwise-335751565476.us-central1.run.app/hero.png

# Verify App UI Snapshot Asset
curl -s -o /dev/null -w "%{http_code}\n" https://shelterwise-335751565476.us-central1.run.app/app_ui_snapshot.png

# Execute End-to-End Triage via REST API
curl -X POST https://shelterwise-335751565476.us-central1.run.app/api/triage \
  -H "Content-Type: application/json" \
  -d '{
    "narrative": "No heat for 3 weeks, radiators cold, child sick, landlord sent 3-day notice, hearing Monday 9am",
    "geoid": "06075016300",
    "block_address": "1000 Block Fillmore St, San Francisco, CA"
  }'
```
