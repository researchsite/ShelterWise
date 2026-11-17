For **ShelterWise – San Francisco**, I recommend building the solution entirely on Google Cloud: **Gemini + Google ADK + BigQuery + Vertex AI + Cloud Run**.

The key is to build a working paralegal-support workflow, not just a chatbot. The agent should turn a tenant's housing issue into an evidence-backed **Tenant Stabilization Brief**, with sources, missing evidence, relevant resources, and actions for a human paralegal to review.

## **1. Master prompt for your team**

Use this as the main instruction in Gemini or your coding agent. It establishes San Francisco as the project location and Google Cloud as the required technology stack.

# ShelterWise — San Francisco Google Cloud Build Prompt

Act as the **technical lead and hands-on implementation engineer** for ShelterWise, an AI-assisted Housing Stability Navigator for San Francisco, California.

## 1. Objective

Build a working application that helps a tenant or paralegal organize a housing problem and produce a cited **Tenant Stabilization Brief** for human review.

Example intake:

- Tenant reports that their apartment has no heat.
- Water is leaking near an electrical outlet.
- The tenant has received an eviction notice.
- They need to understand what evidence may be relevant, which official resources to contact, and what questions to ask a qualified legal professional.

The application must distinguish tenant-reported facts from independently verified public records. It must never claim that a public record proves what happened inside a tenant's home.

## 2. Location and legal scope

Use **San Francisco city and county only** for the first release.

Research and use authoritative sources, including:

- San Francisco Superior Court: [https://sf.courts.ca.gov/self-help/evictions](https://sf.courts.ca.gov/self-help/evictions)
- California Courts eviction guidance: [https://selfhelp.courts.ca.gov/eviction-landlord/notice-types](https://selfhelp.courts.ca.gov/eviction-landlord/notice-types)
- California Department of Justice tenant resources: [https://oag.ca.gov/tenants](https://oag.ca.gov/tenants)
- San Francisco Rent Board: [https://sfrb.org/](https://sfrb.org/)
- San Francisco Rent Ordinance: [https://codelibrary.amlegal.com/codes/san_francisco/latest/sf_admin/0-0-0-16273](https://codelibrary.amlegal.com/codes/san_francisco/latest/sf_admin/0-0-0-16273)
- Eviction Defense Collaborative: [https://evictiondefense.org/legal-assistance-services/](https://evictiondefense.org/legal-assistance-services/)
- Housing Rights Committee of San Francisco: [https://www.hrcsf.org/](https://www.hrcsf.org/)

For public housing-condition evidence, investigate San Francisco's official open-data sources:

- Code Enforcement dataset: [https://data.sfgov.org/](https://data.sfgov.org/)
- 311 Cases dataset: [https://data.sfgov.org/](https://data.sfgov.org/)

Verify dataset schemas, available fields, update dates, licensing, and API access before writing ingestion code. Do not assume every 311 record relates to housing.

Legal content must be date-aware. Check the effective date of each law or amendment before presenting it as currently applicable. Check whether a local ordinance applies to the specific unit and situation. Do not infer legal eligibility from semantic similarity.

## 3. Required Google technology stack

Use Google products for the implementation:

- **Gemini** for language understanding and brief generation.
- **Google Agent Development Kit (ADK)** for the orchestrating agent and tools.
- **Vertex AI / Google Cloud Agent Platform** for managed model access and agent capabilities where appropriate.
- **BigQuery** for structured public data, legal-resource metadata, and retrieval.
- **BigQuery vector search** for semantic retrieval, combined with keyword and jurisdiction filters.
- **Cloud Storage** for approved source documents and document artifacts.
- **Cloud Run** for hosting the backend and agent.
- **Firebase Hosting** for the web interface if a separate frontend deployment is needed.
- **Secret Manager** for secrets.
- **IAM** for least-privilege access.
- **Cloud Logging and Monitoring** for observability.

Prefer the simplest working architecture. Do not introduce additional databases, model providers, or infrastructure unless there is a clear requirement.

## 4. Agent workflow

Build one orchestrating ADK agent with focused tools:

1. `structure_intake`
   - Extract location, issue type, dates, notice details, reported conditions, and requested help.
   - Preserve the tenant's original narrative.
   - Label every fact as tenant-reported, document-derived, public-record-derived, or inferred.
2. `search_public_evidence`
   - Search official San Francisco records.
   - Apply hard filters for location, date, issue category, and relevant address fields.
   - Return source record IDs, dates, descriptions, and links.
   - Explain why each record was retrieved.
   - Never treat a missing record as proof that an event did not happen.
3. `lookup_legal_resources`
   - Retrieve relevant official court guidance, statutes, forms, and legal aid resources.
   - Return the source URL, issuing authority, publication or update date, and effective date where available.
   - Clearly distinguish general information from legal advice.
4. `identify_evidence_gaps`
   - Identify missing documents, dates, inspection records, notice details, and unanswered questions.
   - Suggest safe questions a paralegal can ask.
   - Flag potentially time-sensitive issues for prompt human review without calculating unverified legal deadlines.
5. `generate_stabilization_brief`
   - Produce a structured, source-cited brief.
   - Include facts, evidence, relevant resources, gaps, suggested next steps, and human-review warnings.

## 5. Data design

Create separate BigQuery datasets or clearly separated tables for:

- `public_evidence`: official 311 and code-enforcement records.
- `legal_resources`: official legal guidance, court forms, and legal aid resources.
- `case_intake`: demo or explicitly authorized case intake data.
- `retrieval_audit`: retrieved source IDs, query filters, timestamps, and retrieval explanations.

Keep private case documents separate from public datasets. Do not put real tenant personal information into public demo data. Use synthetic demo cases and clearly label them as demonstrations.

Preserve original source IDs and URLs. Preserve Census GEOIDs as strings if any geographic data is used. Avoid joins that inflate counts.

## 6. User interface

Build a simple case workspace with these screens:

1. New case intake.
2. Case summary and extracted facts.
3. Public evidence timeline.
4. Legal resources and referrals.
5. Missing evidence and questions.
6. Tenant Stabilization Brief.

Show citations next to claims, with links to the original sources. Clearly label unverified information. Provide a way for a paralegal to review and correct extracted facts before generating the final brief.

## 7. Safety and trust requirements

- This is a paralegal-support tool, not a lawyer or legal-advice service.
- Do not guarantee eligibility, protection, or legal outcomes.
- Do not invent laws, deadlines, court forms, records, or referrals.
- Do not use protected traits to rank tenants or determine eligibility.
- Do not treat public neighborhood-level data as proof about an individual household.
- Do not expose private intake details in logs or public interfaces.
- Minimize personal data and use least-privilege access.
- Every legal or public-evidence claim must have a traceable source.
- If a source cannot be verified, say so.

## 8. Implementation approach

Work in small, testable phases. Do not generate the entire application in one step.

**Phase 1 — Validate**

- Inspect the existing challenge repository and its requirements.
- Confirm the permitted metro, scoring criteria, required Google products, and submission requirements.
- Verify the San Francisco datasets and legal sources.
- Produce a source inventory and architecture decision record.

**Phase 2 — Data**

- Create BigQuery datasets and schemas.
- Ingest a small, real sample of official public records.
- Load a curated set of official legal resources.
- Demonstrate exact filtering and source traceability before adding semantic retrieval.

**Phase 3 — Agent**

- Implement the ADK orchestrator and the five tools.
- Add source-grounded retrieval.
- Add structured outputs and failure handling.
- Test that unsupported claims are rejected or marked unverified.

**Phase 4 — Application**

- Build the case workspace and brief view.
- Connect the frontend to the backend.
- Use synthetic tenant cases for demonstrations.

**Phase 5 — Deploy and evaluate**

- Deploy the backend to Cloud Run.
- Deploy the frontend to Firebase Hosting if used.
- Configure IAM, Secret Manager, logging, and access controls.
- Test retrieval accuracy, citations, missing evidence, privacy, and legal-safety behavior.

## 9. Required deliverables

Create:

- Working source code.
- Architecture diagram.
- BigQuery schema and ingestion scripts.
- ADK agent and tool implementations.
- Frontend case workspace.
- Sample synthetic case and expected brief.
- Setup and deployment instructions.
- Test cases and evaluation results.
- A short demo script explaining the problem, workflow, Google technologies, and limitations.

Before coding, inspect the existing repository and report:

1. What is already provided by the challenge.
2. What must be built.
3. Which Google services and APIs must be enabled.
4. Which data sources are verified and accessible.
5. The smallest end-to-end demo that can be completed first.

Do not overwrite existing challenge files without reviewing them. Do not claim a feature works until it has been run and tested.

**Start with Phase 1. Show me the findings and proposed implementation plan before moving to Phase 2.**

## **2. How to build it with Google products**

I would use this sequence. It avoids spending time configuring every Google service before you have a working demo.

**Google Cloud setup**

Create one Google Cloud project named `shelterwise-sf`. Enable billing, select a region, and enable the required APIs. Use a dedicated project for the hackathon rather than mixing it with personal projects.

**BigQuery — public data**

Create datasets for public evidence and legal resources. Load a small sample of San Francisco 311 and code-enforcement records first. Check the schema and filter the records before adding embeddings.

**Gemini + ADK — agent**

Build the five focused tools in the prompt. Start with deterministic SQL and official-source lookup. Add semantic retrieval after you can prove the basic search is accurate.

**Frontend — case workspace**

Build the intake form, evidence timeline, legal resources, and generated brief. Firebase Hosting is a reasonable option for a separate web frontend.

**Cloud Run — deploy**

Deploy the ADK backend, configure authentication and permissions, then connect the frontend. Keep the demo private or authenticated; do not expose tenant intake publicly.

**Google's current implementation references:**

- [ADK quickstart on Google Cloud](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk?utm_source=chatgpt.com) — create and deploy an agent.
- [Deploy an ADK agent to Cloud Run](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-adk-service?utm_source=chatgpt.com) — practical deployment walkthrough.
- [BigQuery vector search](https://docs.cloud.google.com/bigquery/docs/vector-search-intro?utm_source=chatgpt.com) — semantic and hybrid retrieval.
- [BigQuery RAG tutorial](https://docs.cloud.google.com/bigquery/docs/vector-index-text-search-tutorial?utm_source=chatgpt.com) — embeddings, vector search, and grounded generation.

## **3. Your first hands-on steps**

### **Step 1 — Create the Google Cloud project**

Open [Google Cloud Console](https://console.cloud.google.com/?utm_source=chatgpt.com).

1. Create a project: `shelterwise-sf`.
2. Link a billing account.
3. Note the Project ID (it may differ from the display name).
4. Choose a Google Cloud region. Use `us-west1` as an initial candidate, subject to service availability and your data-location requirements.

### **Step 2 — Install and configure Google Cloud CLI**

On your Windows machine, install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install?utm_source=chatgpt.com).

Open PowerShell:

```
gcloud auth login

gcloud config set project YOUR_PROJECT_ID

gcloud config set run/region us-west1

gcloud auth application-default login
```

Enable the initial services:

```
gcloud services enable `
  aiplatform.googleapis.com `
  bigquery.googleapis.com `
  run.googleapis.com `
  storage.googleapis.com `
  secretmanager.googleapis.com `
  logging.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com
```

### **Step 3 — Create your data foundation**

Open [BigQuery](https://console.cloud.google.com/bigquery?utm_source=chatgpt.com).

Create a dataset called `shelterwise_sf`.

Start with two tables:

| Table             | Purpose                                                |
| ----------------- | ------------------------------------------------------ |
| `public_evidence` | SF 311 and building/code-enforcement records           |
| `legal_resources` | Official court, tenant-rights, and legal-aid resources |

Do not start with thousands of records. Load a manageable sample and demonstrate that your agent can retrieve the correct records with traceable source links.

### **Step 4 — Build the agent locally**

Use Python and Google's ADK. Keep the agent code in a separate folder, for example:

```
shelterwise/
  agent/
    __init__.py
    agent.py
    tools/
      intake.py
      public_evidence.py
      legal_resources.py
      evidence_gaps.py
      stabilization_brief.py
  frontend/
  data/
  tests/
  README.md
```

Official starting point: [Google ADK quickstart](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime/quickstart-adk?utm_source=chatgpt.com).

### **Step 5 — Deploy only after local testing**

Once the agent can produce a correctly cited brief locally, deploy it to Cloud Run. Google's [Cloud Run ADK quickstart](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-adk-service?utm_source=chatgpt.com) walks through deployment.

## **4. What I recommend you build first**

**First milestone: one complete San Francisco tenant case, from intake to brief.**

Use a synthetic case involving no heat, a water leak, and an eviction notice. The agent should:

1. Extract the facts from the tenant's narrative.
2. Search actual SF public records.
3. Find relevant California and San Francisco resources.
4. Identify missing evidence.
5. Generate a cited Tenant Stabilization Brief.

Do not build the full multi-agent architecture, advanced vector search, or complex frontend before this works.

**One question before we start implementation:** where do you want to do the coding?

- **Google Antigravity** — Google-focused agentic development environment.
- **Gemini Code Assist / VS Code** — coding assistance in your IDE.
- **Google Cloud Shell** — work directly inside Google Cloud.

I can guide you click by click, including project creation, API setup, code, BigQuery ingestion, agent testing, and deployment.
