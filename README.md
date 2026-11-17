# 🏠 ShelterWise: Housing Stability & Habitability Defense Navigator

[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-Live_Deployment-4285F4?style=for-the-badge&logo=googlecloud)](https://shelterwise-335751565476.us-central1.run.app)
[![Google ADK](https://img.shields.io/badge/Google_ADK-Multi--Agent_Architecture-34A853?style=for-the-badge&logo=google)](https://github.com/google/agent-development-kit)
[![BigQuery Vector Search](https://img.shields.io/badge/BigQuery-AI.EMBED_+_VECTOR_SEARCH-FBBC05?style=for-the-badge&logo=googlebigquery)](https://cloud.google.com/bigquery)
[![Cloud Firestore](https://img.shields.io/badge/Cloud_Firestore-Transactional_Locks-EA4335?style=for-the-badge&logo=firebase)](https://cloud.google.com/firestore)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](LICENSE)

> **Agents for Impact 2026 Submission**  
> An autonomous, grounded multi-agent case stabilization platform that pairs low-income tenants facing eviction with municipal habitability evidence, statutory affirmative defenses, and emergency rental relief grants.

---

## 🌐 Live Application & Endpoints

| Resource | URL | Status |
| :--- | :--- | :--- |
| **Interactive Case Workspace UI** | [https://shelterwise-335751565476.us-central1.run.app](https://shelterwise-335751565476.us-central1.run.app) | 🟢 Live & Serving |
| **Civic Tech Infographic Asset** | [https://shelterwise-335751565476.us-central1.run.app/hero.png](https://shelterwise-335751565476.us-central1.run.app/hero.png) | 🟢 Live Asset |
| **Backend API Health Check** | [https://shelterwise-335751565476.us-central1.run.app/api/health](https://shelterwise-335751565476.us-central1.run.app/api/health) | 🟢 Healthy |
| **Interactive Swagger API Docs** | [https://shelterwise-335751565476.us-central1.run.app/docs](https://shelterwise-335751565476.us-central1.run.app/docs) | 🟢 Live |

---

## 🌟 Google Product Stack & Data Entry Innovations

ShelterWise integrates Google's full cloud & developer ecosystem to eliminate data-entry bottlenecks for advocates and tenants:

1. **Google Maps Geospatial Buffer & Courthouse Route**:
   - Visualizes the tenant's residence, the **400-meter evidentiary radius**, the corroborating 311 citation (12m away), and rejected decoy traps across San Francisco.
   - Traces the transit polyline to the **SF Superior Courthouse (400 McAllister St)** with live MUNI Route 31/5 transit calculations.
2. **Google reCAPTCHA Enterprise Shield**:
   - Integrated bot and abuse prevention protecting the public legal aid intake portal with risk score assessment (`score: 0.94`), ensuring only authentic tenant advocates generate court briefs.
3. **Google Places Address Autocomplete**:
   - Standardizes messy verbal tenant addresses into San Francisco 100-block coarsened format and 11-digit Census Tract GEOIDs (`06075...`).
4. **Google Cloud Speech-to-Text Voice Dictation**:
   - Enables low-literacy tenants or advocates conducting telephone intake to dictate statements verbally with automated acoustic transcription.
5. **MOHCD Area Median Income (AMI) Calculator**:
   - Dynamic 2026 San Francisco Area Median Income calculator that evaluates household size (1–4+ people) and annual earnings to assess eligibility for SF ERAP (<=80% AMI) and MEDA (<=60% AMI).
6. **Google Cloud Storage (GCS) Evidence Dropzone**:
   - Interactive evidence upload for photos (thermostat at 50°F, ceiling water damage) and legal PDFs (notice to landlord, 3-day notice to quit).
7. **Multilingual Access (English / Español / 中文)**:
   - High-priority legal warnings, life-safety gates, and court countdown timers accessible to San Francisco's diverse renter population.

---

## 🎯 Executive Summary & Mission

Every day in San Francisco, tenants appear in unlawful detainer (eviction) court unrepresented, unaware that chronic building conditions—such as weeks without heat or ceiling leaks—constitute affirmative defenses under **California Civil Code § 1941.1 / § 1942.4** and **SF Housing Code § 701**. At the same time, municipal and philanthropic rental relief funds (such as **Prop F Legal Defense** and the **DBI Repair Bridge**) go underutilized because tenants lack official corroboration.

**ShelterWise** bridges this gap:
1. **Understands & Triages**: Ingests unstructured tenant narratives, evaluates acute life-safety hazards, and structures inspector-standard queries.
2. **Retrieves Grounded Evidence**: Uses **BigQuery `AI.EMBED` + `VECTOR_SEARCH`** to semantically retrieve public 311 housing inspection records while discarding planted decoy lookalikes (commercial properties, abated cases, zero-violation inspections).
3. **Applies Statutory Protections**: Tracks the statutory 35-day repair window under CA Civil Code § 1942.4 and unlocks emergency relief funds.
4. **Protects Advocate Collaboration**: Employs **Cloud Firestore `@firestore.transactional` optimistic concurrency locks** to prevent conflicting edits between paralegals and attorneys.
5. **Maintains Demographic Integrity**: Adheres to a strict **Responsible AI Demographic Firewall**, isolating demographic indicators (`audit_*`) from individual case triage to aggregate cohort auditing only.

---

## 🤖 Multi-Agent Architecture (Google ADK)

Every agent in ShelterWise is built with the **Google Agent Development Kit (ADK)** on **Gemini 2.5 Flash (Vertex AI)**. Per project requirements, **every agent name strictly ends with `_ag`**:

```mermaid
graph TD
    User([Paralegal / Housing Advocate]) -->|Intake Narrative| NAV[shelterwise_navigator_ag<br/><i>Root Coordinator</i>]
    NAV -->|Emergency Life-Safety Check| NAV
    NAV -->|Delegates Case Triage| SEQ[case_triage_pipeline_ag<br/><i>SequentialAgent</i>]
    
    subgraph Step 1: Understand
        SEQ --> INT[intake_structurer_ag<br/><i>Extract facts, 11-digit GEOID, search query</i>]
    end

    subgraph Step 2: Gather Corroboration
        INT --> FAN[corroboration_fanout_ag<br/><i>ParallelAgent</i>]
        FAN --> VEC[habitability_vector_ag<br/><i>BigQuery AI.EMBED + VECTOR_SEARCH</i>]
        FAN --> POL[statute_and_bulletin_ag<br/><i>Housing Code & Relief Bulletins</i>]
        FAN --> TRC[tract_displacement_ag<br/><i>v_tract_stability_context & Court Baseline</i>]
    end

    subgraph Step 3: Synthesize & Verify
        VEC --> BRF[eligibility_and_brief_ag<br/><i>Reconciles Evidence Gaps & Generates 9-Section Brief</i>]
        POL --> BRF
        TRC --> BRF
    end

    BRF --> FS[(Cloud Firestore<br/><i>cases/{case_id} & locks</i>)]
    
    subgraph Specialist Support Agents
        NAV --> EXP[evidence_explainer_ag<br/><i>Explains Decoy Filter Rationale</i>]
        NAV --> AUD[equity_audit_ag<br/><i>Responsible AI Silent Distress Audit</i>]
        NAV --> DRF[hazard_311_drafter_ag<br/><i>Emergency 311 Inspection Drafter</i>]
    end
```

### Complete Agent Registry

| Agent Name | Type | Model / Runner | Role & Responsibilities |
| :--- | :--- | :--- | :--- |
| `shelterwise_navigator_ag` | LLM Agent | `gemini-2.5-flash` | Root orchestrator. Intercepts acute life-safety hazards, runs triage, handles multi-turn advocate chats. |
| `case_triage_pipeline_ag` | Sequential Agent | ADK Pipeline | Sequentially chains intake structuring, parallel data gathering, and brief synthesis. |
| `intake_structurer_ag` | LLM Agent | `gemini-2.5-flash` | Extracts reported facts verbatim; normalizes 11-digit census tract GEOID (`06075...`); drafts inspector-vocabulary query. |
| `corroboration_fanout_ag` | Parallel Agent | ADK Fanout | Dispatches concurrent parallel retrieval across BigQuery vector search, policy tables, and tract context. |
| `habitability_vector_ag` | LLM Agent | `gemini-2.5-flash` | Executes BigQuery `VECTOR_SEARCH` with `AI.EMBED`; filters out decoy traps (commercial, abated, zero-violation). |
| `statute_and_bulletin_ag` | LLM Agent | `gemini-2.5-flash` | Queries municipal housing codes, affirmative defense statutes, and 35-day repair clocks. |
| `tract_displacement_ag` | LLM Agent | `gemini-2.5-flash` | Pulls pre-aggregated 4-quarter modeled eviction baselines and ACS rent burden. Firewalled against demographics. |
| `eligibility_and_brief_ag` | LLM Agent | `gemini-2.5-flash` | Synthesizes 9-section Tenant Stabilization Brief; assesses fund eligibility based on open DBI case status. |
| `evidence_explainer_ag` | LLM Agent | `gemini-2.5-flash` | Explains why decoy near-miss records were excluded to ensure advocate transparency. |
| `equity_audit_ag` | LLM Agent | `gemini-2.5-flash` | Evaluates silent distress tracts (under-reporting) across the metro area. STRICTLY isolated from case triage. |
| `hazard_311_drafter_ag` | LLM Agent | `gemini-2.5-flash` | Drafts formal emergency SF DBI 311 inspection requests when zero complaints exist on a block. |

---

## 🔍 BigQuery Vector Search & Decoy Rejection

### Live BigQuery Vector Query
The `habitability_vector_ag` queries BigQuery using Vertex AI embeddings directly in SQL:

```sql
SELECT base.request_id,
       base.block_address,
       base.property_type,
       base.inspection_status,
       base.closed_date,
       base.complaint_narrative,
       ROUND(distance, 4) AS cosine_distance
FROM VECTOR_SEARCH(
  TABLE `a4i_housing.complaints_embedded`,
  'embedding',
  (SELECT AI.EMBED(
     @search_query,
     connection_id => 'us.a4i-vertex',
     endpoint => 'gemini-embedding-2'
   ).result AS query_vec),
  query_column_to_search => 'query_vec',
  top_k => 25,
  options => '{"use_brute_force": true}'
);
```

### The 3 Decoy Trap Classes & Rejection Rules
BigQuery returns 25 semantically similar hits, which include synthetic planted decoys. The system applies strict business rule post-filters—**without hardcoding `"DECOY"` strings**:

1. **Commercial Property Decoys (e.g., `DECOY-SANF-01` to `03`)**:
   - *Trap*: High semantic similarity (0.93) regarding boiler failure in a warehouse/storefront.
   - *Rule*: Discard if `property_type != 'Residential'`. SF Housing Code § 701 applies solely to residential dwellings.
2. **Closed - Abated Decoys (e.g., `DECOY-SANF-04` to `06`)**:
   - *Trap*: Real habitability violation that the landlord previously resolved.
   - *Rule*: Discard if `closed_date IS NOT NULL` or status contains `Abated`. Prior resolved complaints cannot corroborate an ongoing failure to repair.
3. **Closed - Zero Violation Decoys (e.g., `DECOY-SANF-07` to `09`)**:
   - *Trap*: Winter readiness inspection where the inspector tested radiators at 71°F and found zero defects.
   - *Rule*: Discard if status or narrative indicates `No Violation`. Introducing a clean inspection would undermine the tenant in court.

---

## 📊 Data Provenance & Grounding Principles

All data in ShelterWise is rigorously attributed with unambiguous provenance tags:

| BigQuery Table / View | Provenance Tag | Description & Safe Usage |
| :--- | :--- | :--- |
| `complaints_embedded` | `[Real 311 Public Record]` / `[Planted Decoy Record]` | 174 rows (165 real SF 311 complaints coarsened to 100-block + 9 planted decoys) embedded with `gemini-embedding-2`. |
| `municipal_311_housing_complaints` | `[Real 311 Public Record]` | Ground truth inspection citations from the SF Department of Building Inspection. |
| `v_tract_stability_context` | `[Real Census ACS 2018-2022]` + `[Modeled Court Baseline]` | 42 SF census tracts pre-aggregating 4 quarterly court filing records to avoid multi-row duplication. **Omit demographic columns.** |
| `municipal_housing_ordinance_statutes` | `[Public Statutory Reference]` | Enforceable affirmative defenses: SF Housing Code § 701, SF Admin Code Ch. 37 (Prop F), and Cal. Civ. Code § 1941.1 / § 1942.4 / § 1942.5. |
| `rental_relief_program_bulletins` | `[Public Program Guidelines]` | Guidelines for SF ERAP, MEDA Anti-Displacement Grants, Prop F Legal Defense, and DBI Repair Bridge. |
| `v_metro_equity_audit` | `[Responsible AI Audit View]` | Aggregate cohort view containing `audit_*` demographic columns. **Strictly firewalled from individual case triage.** |

### Grounding Rules
- **Preserve Leading Zeros**: Census tract GEOIDs are strictly handled as 11-character strings (`06075...`).
- **4× Eviction Grain Pre-Aggregation**: Eviction court filing tables contain 4 quarters per tract. Queries must pre-aggregate `SUM(filings)` to prevent 400% over-counting.
- **Absence ≠ Proof**: The absence of a 311 complaint on a block does not mean conditions are habitable; it activates `hazard_311_drafter_ag`.
- **Block ≠ Unit**: A block-level 311 complaint corroborates building-wide neglect but does not replace unit-specific testimony.

---

## 🔒 Cloud Firestore Transactional Case Store

ShelterWise uses **Google Cloud Firestore in Native Mode** (`projects/qwiklabs-gcp-04-99fa355171e1/databases/(default)` in `nam5`) for transactional case integrity.

- **Optimistic Concurrency Locking**:
  ```python
  @firestore.transactional
  def _tx_claim(transaction, doc_ref):
      snapshot = doc_ref.get(transaction=transaction)
      curr = snapshot.to_dict()
      if expected_version is not None and curr.get("lock_version") != expected_version:
          raise ValueError(f"Concurrency Conflict: current version is {curr.get('lock_version')}")
      transaction.update(doc_ref, {
          "assigned_paralegal": paralegal_name,
          "lock_version": curr.get("lock_version", 1) + 1,
          "updated_at": firestore.SERVER_TIMESTAMP
      })
  ```
- **Attorney Review Checklist**: Persists verification items (life-safety communicated, decoys excluded, 11-digit GEOID confirmed, relief prerequisites checked).

---

## 🎬 10-Step Demo Walkthrough Guide

Follow these steps in the [Live Web UI](https://shelterwise-335751565476.us-central1.run.app):

1. **Step 0: Intake & Acute Safety Gate**
   - Review incoming narrative: *"Tenant at 1000 Block Fillmore St. No heat for weeks... Nonpayment hearing Monday at 9am."*
   - Toggle *"Simulate Acute Hazard"* to see immediate life-safety intercept (water dripping into electrical panel).
   - Click **"▶ Send & Run Triage"** to trigger `case_triage_pipeline_ag`.
2. **Step 1: Understand (`intake_structurer_ag`)**
   - Inspect structured JSON: 11-digit GEOID `06075016300`, eviction urgency flagged (`<72h`).
   - Notice inspector-wording query: *"no heat cold dwelling radiators inoperative"*.
3. **Step 2: Gather Evidence (`habitability_vector_ag`)**
   - Click **"▶ Run Vector Search"**. Watch BigQuery `AI.EMBED` execute and return 25 hits.
   - Inspect kept record `SF-202665182` and observe that `DECOY-SANF-01`, `04`, and `07` were excluded.
4. **Step 3: Gather Context (`tract_displacement_ag`)**
   - Inspect neighborhood stability context: 1,653 renter units, 16.0% severe rent burden, 65 annual filings.
   - Notice the **Responsible AI Demographic Firewall** badge confirming zero demographic queries.
5. **Step 4: Decide Law (`statute_and_bulletin_ag`)**
   - Review applicable statutes: SF Housing Code § 701, Prop F Counsel, Cal. Civ. Code § 1942.5.
   - Check the **CA Civil Code § 1942.4 Repair Clock**: 16 of 35 days elapsed (matures 2026-12-09).
6. **Step 5: Decide Relief Funds (`eligibility_and_brief_ag`)**
   - Notice Prop F & DBI Bridge marked **CONDITIONAL** because tenant's own DBI case number is unconfirmed.
   - Check *"Tenant has her own verified DBI case number"*: Watch status flip immediately to **ELIGIBLE**.
7. **Step 6: Write & Verify**
   - Click **"▶ Run Automated Validation Checks"**. Watch 6 automated verifier checks pass.
8. **Step 7: Defense Brief**
   - Review the complete 9-section **Tenant Stabilization Brief** with grounded citations.
   - Click **"🖨 Print / Save Defense Brief PDF"**.
9. **Step 8: Interactive Follow-ups (`shelterwise_navigator_ag`)**
   - Click *"Why did you drop the warehouse boiler one?"* → `evidence_explainer_ag` explains the commercial exclusion.
   - Click *"Transit before 9am Monday?"* → `estimate_courthouse_transit` calculates route to SF Civic Center Courthouse.
   - Click *"Lock this case for Attorney Chen"* → Firestore transaction commits with `lock_version: 2`.
10. **Step 9: Human Review & Equity Audit**
    - Check off the 7 Attorney Review Checklist items (persisted to Firestore).
    - Click **"▶ Run Aggregate Equity Audit"** → `equity_audit_ag` identifies silent-distress tracts across SF.

---

## 🧪 Automated Test Suite

ShelterWise includes 9 unit and integration tests verifying all core requirements:

```bash
# Run test suite
PYTHONPATH=".libs:agent:$PYTHONPATH" /opt/venv/bin/python3 -m unittest discover -s agent/tests -v
```

### Test Results
```text
test_all_agent_names_end_with_ag (test_shelterwise.TestShelterWise.test_all_agent_names_end_with_ag)
STRICT REQUIREMENT: All agent names must end with _ag. ... ok
test_chat_routing (test_shelterwise.TestShelterWise.test_chat_routing)
Tests multi-turn follow-up routing for specialist queries. ... ok
test_decoy_rejection_rules (test_shelterwise.TestShelterWise.test_decoy_rejection_rules)
Tests that commercial, abated, and zero-violation decoy records are filtered ... ok
test_demographic_firewall_in_tract (test_shelterwise.TestShelterWise.test_demographic_firewall_in_tract)
Verifies that no audit_* columns are ever present in case triage. ... ok
test_equity_audit_aggregate (test_shelterwise.TestShelterWise.test_equity_audit_aggregate)
Tests Responsible AI aggregate equity audit. ... ok
test_firestore_transactional_lock (test_shelterwise.TestShelterWise.test_firestore_transactional_lock)
Verifies optimistic concurrency locking via FirestoreStore. ... ok
test_full_triage_pipeline_execution (test_shelterwise.TestShelterWise.test_full_triage_pipeline_execution)
Executes the full triage pipeline and checks brief synthesis. ... ok
test_intake_hazard_and_geoid (test_shelterwise.TestShelterWise.test_intake_hazard_and_geoid)
Tests acute life safety hazard detection and 11-digit GEOID normalization. ... ok
test_statute_clocks_and_relief (test_shelterwise.TestShelterWise.test_statute_clocks_and_relief)
Verifies that statutes and relief programs evaluate habitability prerequisites. ... ok

----------------------------------------------------------------------
Ran 9 tests in 9.350s

OK
```

---

## 🚀 Local Development Quickstart

```bash
# 1. Clone repository
git clone https://github.com/researchsite/ShelterWise.git
cd ShelterWise

# 2. Install dependencies
pip install -r agent/requirements.txt

# 3. Set environment variables
export PROJECT_ID="qwiklabs-gcp-04-99fa355171e1"
export BIGQUERY_DATASET="a4i_housing"
export METRO_AREA="San Francisco"
export VERTEX_AI_LOCATION="us-central1"

# 4. Run FastAPI server locally
python3 agent/server.py

# 5. Open browser at http://localhost:8080
```

---

## 📄 License & Attribution
Developed for the **Google Cloud Agents for Impact Hackathon 2026**.  
Licensed under the Apache License 2.0.
