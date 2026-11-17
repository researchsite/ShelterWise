# ShelterWise — Affordable Housing Stability & Eviction Prevention Navigator

**Agents for Impact 2026 · Default Metro: San Francisco, CA (`FIPS 06`)**

> **Approved Team Architecture Blueprint:** [`docs/shiva_arc.md`](docs/shiva_arc.md) — Multi-Agent Google ADK (`LlmAgent` + `SequentialAgent` + `ParallelAgent`) + BigQuery (`AI.EMBED` + `VECTOR_SEARCH` + Managed MCP) + Cloud Firestore (Multi-Paralegal Transactional Store) on Cloud Run (`--min-instances=1`).

---

## ShelterWise 6-Member Implementation Plan (Zero-Collision Split)

Every teammate works on **separate files/folders** and **their own Git branch** so nobody hits merge conflicts:

| Member | Role & Branch | Exact Deliverables (from [`docs/shiva_arc.md`](docs/shiva_arc.md)) | Exclusive Files Owned |
|---|---|---|---|
| **Member 1** | **BigQuery Data, Embeddings & Views**<br>`branch: data-bq` | 1. Run `bash scripts/load.sh san-francisco` (`a4i_housing` in `US`)<br>2. Create Vertex connection `us.a4i-vertex` + grant `roles/aiplatform.user`<br>3. Run `sql/setup_vector_and_views.sql` (`complaints_embedded` + fan-out-safe `v_tract_stability_context`)<br>4. Verify Section 12's 26 checks + export SF Equity Audit cohort query | `sql/setup_vector_and_views.sql`<br>`scripts/setup_bigquery.sh` |
| **Member 2 (Shiva)** | **Schemas & 5 Core Triage Custom Tools**<br>`branch: shiva` | 1. Canonical JSON contracts (`schemas.py` + `config.py`) **← ship first to unblock M3, M4, M5**<br>2. `bigquery_client.py` (with offline SF fixtures for instant local dev)<br>3. **5 Core Custom ADK `FunctionTool`s**: `structure_intake`, `search_public_evidence` (`VECTOR_SEARCH` + 9-decoy post-filter), `fetch_statutes_and_bulletins`, `get_tract_displacement_baseline`, `reconcile_gaps_and_generate_brief` | `agent/shelterwise_agent/config.py`<br>`agent/shelterwise_agent/schemas.py`<br>`agent/shelterwise_agent/db/bigquery_client.py`<br>`agent/shelterwise_agent/tools/{intake,evidence,policy,tract,brief}.py` |
| **Member 3 (Rohith)** | **ADK Multi-Agent Tree & Managed MCP**<br>`branch: rohith` | 1. Google-managed **BigQuery `MCPToolset`** (`https://bigquery.googleapis.com/mcp`)<br>2. ADK Agent Hierarchy (`agent.py`): Root `shelterwise_navigator` (`LlmAgent`) + `case_triage_pipeline` (`SequentialAgent` → 3-way `ParallelAgent` `corroboration_fanout`)<br>3. Specialist Sub-Agents: `evidence_explainer_agent`, isolated `equity_audit_agent`, `hazard_311_drafter_agent` | `agent/shelterwise_agent/agent.py`<br>`agent/shelterwise_agent/__init__.py`<br>`agent/shelterwise_agent/mcp/bigquery_mcp.py` |
| **Member 4** | **Firestore, Bonus Tools, FastAPI & Cloud Run**<br>`branch: platform-deploy` | 1. Provision Cloud Firestore (`nam5`) + `firestore_store.py` (`@firestore.transactional` multi-paralegal lock)<br>2. **Bonus & Post-Output Tools**: `draft_311_inspection_request`, `run_metro_equity_audit`, `claim_or_update_case_task` + `estimate_courthouse_transit` (`400 McAllister St`)<br>3. FastAPI gateway (`server.py`: `/api/triage`, `/api/chat`, `/api/cases/{id}`) + `Dockerfile` + Cloud Run deploy (`--min-instances=1`) | `agent/shelterwise_agent/db/firestore_store.py`<br>`agent/shelterwise_agent/tools/{drafter_311,equity_audit,logistics}.py`<br>`agent/server.py`<br>`agent/requirements.txt`<br>`agent/Dockerfile`<br>`agent/deploy_cloud_run.sh` |
| **Member 5** | **Case Workspace Web UI**<br>`branch: frontend` | Interactive **ShelterWise Case Workspace** (not a blank chatbox):<br>1. One-click SF Demo Case loader (*3:40pm Thu · 400 Block · cold radiators + wet fuse box · Mon 9am court*)<br>2. Immediate Life-Safety Alert Banner<br>3. **Evidence Room** tabs: **Valid Open Residential 311s** vs. **Excluded Decoys** (`cosine_distance` & exclusion reason)<br>4. **Statutes + 4 Relief Funds** (`requires_open_habitability_case` badge) + **Tract Baseline** (`[Modeled]` badge)<br>5. **9-Section Brief + 6-Item Reviewer Checklist + Paralegal Lock** + **Multi-Turn Chat Sidebar** | `frontend/*` |
| **Member 6** | **QA Red-Team, Pitch Deck & <=3m Video**<br>`branch: story-qa` | 1. `pytest` & live red-team suite (`agent/tests/*`): verify all 9 `DECOY-*` caught, `'06075...'` GEOIDs intact, 0 `audit_*` in case outputs, no 4× fan-out<br>2. Update slides for **San Francisco (`FIPS 06`)**, architecture diagram, real vs. `[Modeled]` provenance, & SF Post-Output Equity Audit table (`audit_*` + `no_vehicle_rate`)<br>3. Script & record crisp **`<= 3:00` live walkthrough video** + AngelHack portal submission | `agent/tests/*`<br>`slides/*`<br>`qa/*` |

### Sync Checkpoints
1. **Checkpoint 1 (15 mins):** Member 2 pushes `schemas.py` + offline SF fixtures → unblocks Member 3 (`agent.py`), Member 4 (`server.py` + Firestore), Member 5 (`frontend/`), and Member 6 (`tests/`). Member 1 loads SF BigQuery + `complaints_embedded` + `v_tract_stability_context`.
2. **Checkpoint 2 (60 mins):** Member 3 + Member 4 merge ADK agents + FastAPI + Firestore and deploy to Cloud Run (`--min-instances=1`), sharing the live URL with Member 5 & Member 6.
3. **Checkpoint 3 (105 mins):** Member 5 wires UI to live Cloud Run endpoints; Member 6 runs full red-team QA + pulls SF Equity Audit numbers into slides.
4. **Final 45 mins:** Feature freeze, end-to-end demo rehearsal on deployed URL, record `<=3:00` video, and submit.

---

*(Official Agents for Impact 2026 Challenge Brief below for reference)*

---

## Why this one matters

More than half of low-income renters in America spend over half their paycheck on rent, leaving families one missed shift, medical bill, or broken car transmission away from a court eviction filing. Across major cities, residential tenants hauled into housing court for nonpayment frequently live in buildings the city *already knows* have no heat, raw sewage backups, toxic mold, or unsafe electrical wiring.

Under state and municipal housing codes, active residential habitability hazards unlock emergency rental stabilization grants, rent-escrow protections, and statutory legal defenses. Yet most tenants lose by default or sign away those protections in five-minute hallway settlements because nobody connected the building-code file to the court docket before Monday morning.

This is not a shortage of municipal records. Cities log hundreds of thousands of 311 and code-enforcement narratives every year. It is a **triage and corroboration problem under a clock**. A right-to-counsel legal-aid clinic has a waiting room full of families, scarce stabilization funds with strict eligibility rules, and minutes to separate active residential hazards from closed repairs, commercial warehouse complaints, and noisy free-text logs.

**Your job today is to build the navigator that connects those files before the hearing starts.**

You will build it for **one metro**, not for everywhere. Which city you solve for is a real engineering decision, and it is yours to make a few sections down once you see how the six cities differ.

---

## How to read this

**This is a reference for your whole afternoon, not something to read end to end right now.** Here is what each lane needs in the first fifteen minutes.

| If you are... | Read now | Come back for |
|---|---|---|
| **Everyone, together** | [The four things](#the-four-things-youre-working-with) · [Three tracks](#three-tracks-one-architecture) · [What you're building](#what-youre-building) · [Now pick your metro](#now-pick-your-metro) | Agree on these before anyone opens a keyboard |
| **Team lead** | [Step 0](#step-0-organize-your-team) · [How you'll be judged](#how-youll-be-judged) | [Going further](#going-further) (read it *before* writing code, not right before the demo) |
| **Data lane** | [Step 4, load the data](#step-4-load-the-data) · [What you'll have](#what-youll-have) | [The data, and why we chose it](#the-data-and-why-we-chose-it) · Section 13 of the notebook |
| **Agent lane** | [What you're building](#what-youre-building) · [The technology](#the-technology-youll-use) | [`agent/README.md`](agent/README.md) · [Questions that need more than we gave you](#questions-that-need-more-than-we-gave-you) |
| **Front end lane** | [Front end lane](#front-end-lane-2-people) | [Your output artifact](#your-output-artifact-the-tenant-stabilization-brief) |
| **Story lane** | [Your output artifact](#your-output-artifact-the-tenant-stabilization-brief) | [The data](#the-data-and-why-we-chose-it) (know what is real vs. modeled, because judges check) |

**Three things everybody should know by the end of hour one**, whatever lane you are in:

1. **Know what is real and what is modeled.** Census rent-burden counts (`acs_tract_housing_tenure`) and 100-block 311 complaints (`municipal_311_housing_complaints`) are real public records, except for nine labeled `[Planted Case]` decoys per metro. Quarterly court filings (`court_eviction_filings`) are **modeled** from county court baselines because Princeton's Eviction Lab has zero California coverage and only ZIP-level New York City coverage. Read `data_provenance` and state this plainly in your deck and video.
2. **`court_eviction_filings` has four quarters per census tract.** Join it directly to 311 complaints without aggregating by `census_tract_geoid` first, and every 311 complaint gets counted four times.
3. **Vector search alone will catch planted traps unless you filter afterward.** Nine `DECOY-*` rows per metro semantically describe broken heat or mold, but three sit in commercial properties, three are already closed/abated, and three found zero violations.

---

## The four things you're working with

Small vocabulary, used consistently everywhere from here on.

| Term | What it means |
|---|---|
| **Intake** | One tenant crisis or block-level inquiry arriving at a legal-aid desk, described in everyday language: *"Radiators have been stone cold since Tuesday, ceiling is leaking onto the breaker box, nonpayment hearing Monday."* This is the **query** side |
| **311 Narrative** | A 100-block municipal housing or code-enforcement record (`municipal_311_housing_complaints`), carrying messy inspector/citizen text alongside structured `property_type`, `inspection_status`, and `closed_date`. This is the primary **corpus** you embed and search |
| **Relief & Statute Rules** | Emergency rental assistance programs (`rental_relief_program_bulletins`) and state/local housing statutes (`municipal_housing_ordinance_statutes`) that govern which open residential conditions unlock financial aid or legal defenses |
| **Stabilization Brief** | Corroborated 100-block complaint evidence paired with the matching statute, eligible relief fund, neighborhood context, and a drafted legal-aid intake memo |

The whole challenge is: **tenant crisis or block triage in, corroborated stabilization brief out, with defensible eligibility reasoning attached.**

---

## Three tracks, one architecture

Every team building this challenge shares the same spine: one embedded corpus of 311 habitability narratives, one semantic vector search, one relational eligibility filter, one statutory/fund match, and one drafted brief. **What changes between tracks is the operational entry point, not the machinery.**

**These are starting points, not a cage.** Pick one, combine two, or define a sharper housing-stability workflow in the same vein if you can defend why it matters.

| Track | What arrives | Who acts on it | What makes it hard |
|---|---|---|---|
| ⚖️ **Today at intake** | A tenant walks into legal aid with a Monday nonpayment hearing and an unheated or moldy unit | Right-to-counsel paralegal or housing attorney | Finding corroborating 100-block open residential complaints when citizen phrasing never matches statute text, while rejecting closed or commercial decoys |
| 🛟 **This relief cycle** | Multiple households competing for four local stabilization funds with strict habitability and residential rules | Municipal rental-relief coordinator | Two of the four programs (`requires_open_habitability_case = TRUE`) require active habitability proof, while others serve general rent arrears |
| 🏘️ **Next quarter outreach** | A tenant-protection team planning door-knocking before next quarter's filings spike | City housing-navigation lead | Pre-aggregating 4-quarter modeled eviction pressure with real open residential 311 clusters without triggering 4x join inflation or 311 reporting bias |

---

## What you're building

**A stabilization navigator.** Not a static dashboard, and not a single SQL query behind a chat box, but a working agent an intake paralegal or municipal housing counselor can hold a multi-turn conversation with at 4pm on a Thursday.

Picture a single afternoon at a legal-aid intake desk:

> **3:40pm, Thursday.** A mother of two arrives with a three-day nonpayment notice on the 400 block in her neighborhood. She says the radiators have been ice cold for two weeks and water from upstairs is dripping near the kitchen fuse box. Court is Monday at 9am.

Over the next twenty minutes the paralegal asks your agent all of these:

| What they ask | What answers it |
|---|---|
| *"Are there open residential habitability complaints near this block matching heat loss or electrical water intrusion?"* | `AI.EMBED` + `VECTOR_SEARCH` over `municipal_311_housing_complaints`, filtered to `property_type = 'Residential' AND closed_date IS NULL` |
| *"Why did you exclude that severe boiler shutdown complaint on the next block?"* | Explaining the structured post-filter (`Commercial` property or `Closed - Abated` status, including planted `DECOY-*` cases) |
| *"Which local statute covers withholding rent or habitability defense for heat and electrical hazards?"* | Matching `municipal_housing_ordinance_statutes` (`code_citation`, `raw_statute_text`) for this metro |
| *"Which emergency stabilization fund still fits this household, and does it require an open habitability case?"* | Checking `rental_relief_program_bulletins` (`requires_open_habitability_case`, `residential_tenants_only`, `raw_bulletin_text`) |
| *"How severe is eviction filing pressure and rent burden in this census tract compared with the rest of the metro?"* | `acs_tract_housing_tenure` joined cleanly to pre-aggregated `court_eviction_filings` |
| *"Who lives in the tracts our triage rules prioritize, and where might 311 under-reporting blind us?"* | Post-output Equity Audit joining `audit_*` shares and severe rent burden |
| *"Draft the intake corroboration memo and relief referral packet so the attorney can review it tonight."* | Gemini synthesizing cited 100-block request IDs, statute citations, program links, and explicit caveats |

### Questions that need more than we gave you

| The question | What you'd need to add |
|---|---|
| *"Can the tenant reach the courthouse or intake clinic by bus before 9am?"* | Transit schedules or Google Maps routing from tract/block coordinates (`latitude`, `longitude`) |
| *"Has this landlord or parcel accumulated tax liens or utility shutoffs?"* | Municipal assessor or open-data parcel records (check the [BYOD license rules](#bringing-your-own-data) first) |
| *"Track open intake tasks across three paralegals without overwriting each other"* | A transactional state store such as Firestore, Cloud SQL, or AlloyDB (BigQuery is an analytical warehouse, not a row-lock queue) |
| *"Help a tenant document a brand-new hazard not yet reported to 311"* | A structured 311 intake drafter (see [Going further](#going-further)) |

---

## Now pick your metro

**This is an application for one metropolitan corridor**, and choosing yours is the first real decision your team makes. You do **not** have to pick the city you are sitting in.

All six metros below are pre-staged in `data/`, verified end to end, and ready in thirty seconds:

| Metro | State (`FIPS`) | Tracts | Renter units | Severe rent burden (`50%+`) | Annual modeled filings | Open residential 311s | `[Planted Case]` decoys |
|---|---|---:|---:|---:|---:|---:|---:|
| **San Francisco** *(default)* | `CA` (`06`) | 42 | 66,252 | 17.5% | 2,359 | 140 | 9 |
| **Chicago** | `IL` (`17`) | 42 | 100,465 | 18.9% | 6,563 | 165 | 9 |
| **New York** | `NY` (`36`) | 168 | 437,111 | 25.2% | 45,471 | 165 | 9 |
| **Austin** | `TX` (`48`) | 42 | 61,203 | 21.1% | 6,218 | 122 | 9 |
| **Baton Rouge** | `LA` (`22`) | 42 | 36,390 | 27.2% | 5,609 | 10 | 9 |
| **Cincinnati** | `OH` (`39`) | 42 | 55,101 | 23.1% | 6,596 | 152 | 9 |

Look closely at two structural signals in that table before choosing:

1. **Leading-zero FIPS (`San Francisco`, state FIPS `06`):** Cast `census_tract_geoid` to an integer anywhere in Python or SQL and `'06075010800'` turns into a 10-digit number, silently dropping every tract join. Keep GEOIDs as strings everywhere.
2. **The Baton Rouge source-mix contrast:** Baton Rouge carries the highest severe rent burden in the entire pack (`27.2%`), yet `155` of its `165` real 311 complaints are already closed, leaving only `10` open residential 311 records. That is a real municipal reporting and closure dynamic rather than a broken load, and a team that chooses Baton Rouge on purpose has an immediate story about why relying on open 311 tickets alone under-serves high-burden neighborhoods.

Write down your metro, your track, and your opening scenario sentence before writing code:

> *"We support housing intake in ______. A household in ______ is facing ______, and we have to corroborate active residential habitability conditions and match an open stabilization fund before ______. Here is what the city record shows, and here is what it cannot prove."*

---

## The technology you'll use

Every team across every challenge uses the same core stack:

| Component | Role |
|---|---|
| **ADK** (Agent Development Kit) | Build your agent in Python with ADK |
| **Gemini** | Reasoning over messy tenant intakes, weighing statutory/program fit, and drafting the memo |
| **BigQuery** | Hosts your five metro tables (`a4i_housing`) and executes `AI.EMBED` + `VECTOR_SEARCH` |
| **A Google-managed MCP server** | Consume at least one (BigQuery built-in MCP server or MCP Toolbox for Databases) |
| **At least one tool you built** | A Python function tool or custom MCP Toolbox tool authored by your team |
| **Deployed to Google Cloud** | Live service running on **Agent Runtime** or **Cloud Run** |

**Also already set up for you, and worth ten seconds now rather than later: Antigravity.** Your Google Skills lab environment includes a button that launches the **Antigravity IDE**, and the **Antigravity CLI** is one word away in Cloud Shell (`agy`). Neither is required, and nothing here depends on them, so do not lose time fighting one if it is not helping, though we strongly recommend using at least one because every lane has tedious boilerplate a coding agent will happily absorb. [Details in Step 3](#strongly-recommended-antigravity-the-ide-and-the-cli).

### Choosing your MCP server

- **BigQuery's built-in MCP server** is the fastest path for structured discovery and table lookups.
- **[MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox)** gives you prebuilt BigQuery tools plus parameterized SQL tool definitions of your own.

> **Hint worth taking:** if you deploy MCP Toolbox on **Cloud Run, set `--min-instances=1`**. Cloud Run scales to zero by default, and paying a cold start during your recorded demo walkthrough is an unforced error.

### What "a tool you built" means, and why we ask

Consuming only prebuilt generic query tools does not count as custom tool design. We are looking for at least one tool your team engineered (either in Python or as a custom parameterized tool in MCP Toolbox) that encapsulates real domain judgment: running semantic `VECTOR_SEARCH`, applying hard eligibility predicates (`property_type = 'Residential' AND closed_date IS NULL`), checking `requires_open_habitability_case` rules, and assembling structured corroboration evidence.

### And one required differentiator: **BigQuery Vector Search**

Citizens and building inspectors describe the exact same hazard twenty different ways:
- *"radiators stone cold since Tuesday"* vs. *"inadequate heating below municipal code minimum"*
- *"water dripping through ceiling onto fuse panel"* vs. *"electrical arcing hazard from roof leak"*

Meanwhile, a keyword search for `mold` or `no heat` happily retrieves planted decoy records like *"commercial warehouse heater off, zero residential tenants"* or *"proactive inspection: no mold, no leaks, zero habitability defects found."*

Your pipeline must embed narratives in BigQuery (`AI.EMBED` with `gemini-embedding-2` via a `CLOUD_RESOURCE` connection granted `roles/aiplatform.user`), execute `VECTOR_SEARCH`, and then apply hard relational filters so near-miss decoys never reach a legal-aid brief. See Section 13 of [`notebooks/c_housing_01_load_explore.ipynb`](notebooks/c_housing_01_load_explore.ipynb) for exact copy-paste setup commands.

---

## Getting started

You have **4.5 hours** and **8 to 10 teammates**. Spend twenty minutes on Step 0 so the four lanes run in parallel without stepping on each other.

### Step 0: Organize your team

1. **Pick a team lead** who makes scope cuts when the clock tightens.
2. **Pick a repo owner** to create one shared team repository from this template and invite everyone as collaborators.
3. **Agree on your metro, your track, and your demo scenario** in five minutes.
4. **Split into four lanes immediately:**

#### Data lane (2 to 3 people)

- Run `notebooks/c_housing_01_load_explore.ipynb` (or `bash scripts/load.sh <metro>`) to load and validate `a4i_housing`.
- Provision the `us.a4i-vertex` `CLOUD_RESOURCE` connection, bind `roles/aiplatform.user`, and materialize `a4i_housing.complaints_embedded` (Section 13 of the notebook). **Do this first** so the agent lane is unblocked.
- Verify that your post-search filter eliminates all 9 `DECOY-*` cases while preserving genuine open residential hazards.
- Build the fan-out-safe CTE pre-aggregating `court_eviction_filings` across its 4 quarters before joining to tract or 311 tables.
- Run the post-output **Equity Audit** using `audit_*` shares (`Section 11`).

#### Agent lane (2 to 3 people)

- Scaffold the Python ADK agent in `agent/`.
- Wire up at least one **Google-managed MCP server** and **at least one custom tool** wrapping your `VECTOR_SEARCH` + eligibility logic.
- Teach the system prompt when to refuse or caveat: a 100-block 311 match corroborates neighborhood/block conditions (`block_address`), not an individual apartment number, and modeled eviction counts are neighborhood baselines rather than personal court dockets.
- **Deploy early** to Cloud Run or Agent Runtime so the front-end and story lanes have a live URL well before deadline.

#### Front end lane (2 people)

Three routes. **Pick deliberately and be ready to say why**, because your interface choice tells judges who you think the user is.

| Option | Strength | Trade-off |
|---|---|---|
| **`adk web`** | Fastest. Built in, works immediately, and where you should start | Developer tool look and feel. Fine while building, weak as a final product story unless justified |
| **Gemini Enterprise** | Clean internal staff UX over Agent Runtime with minimal front-end code | Serves **internal** staff rather than the public (which fits a legal-aid paralegal persona well if stated on purpose) |
| **Custom web UI** | Full control: an intake triage queue + Tenant Stabilization Brief card beats a raw chat log | Most work by far. Scope tightly so it finishes on time |

- **Do not wait for a working agent.** Mock the response schema now, build against it, and swap in the live endpoint once the agent lane deploys.
- **Whatever you build, the recorded demo runs on it.** Test it end to end before recording.

#### Story lane (1 to 2 people, starting at minute zero)

**What you hand in.** Four artifacts uploaded to https://portal.angelhack.com/a4i-console before the submission cutoff:

1. **Public GitHub repository link**
2. **Google Skills project link** (with your deployed agent live on Cloud Run or Agent Runtime)
3. **Pitch deck** (problem, chosen metro & track, architecture, plain-words data provenance, `audit_*` Equity Audit numbers, and honest limitations)
4. **Pitch video (maximum 3 minutes)**: a crisp screen-share walkthrough narrating a live end-to-end run of your deployed agent

**Judges grade asynchronously from those four artifacts with no live table Q&A.** Every question in [How you'll be judged](#how-youll-be-judged) must be answered clearly inside your deck or your 3-minute video.

### Your output artifact: the Tenant Stabilization Brief

Whatever interface you choose, your agent should produce an actionable brief a paralegal can hand to a supervising attorney:

- **Corroborating 100-block 311 records** (`request_id`, `block_address`, `raw_complaint_type`, `inspection_status`, semantic similarity, and why decoys were excluded)
- **Applicable statute citation** (`code_citation`, `ordinance_title`, key statutory protection)
- **Matched emergency relief program** (`program_name`, `administering_agency`, eligibility fit, and `intake_url`)
- **Tract context & Equity Audit note** (severe rent burden, annual modeled filings without 4x fan-out, and neighborhood context)
- **Explicit evidentiary boundary** (100-block public record vs. unit-level lease/inspection proof)
- **Drafted legal-aid intake memo**, ready for review

### Step 1: Create the team repository

**Repo owner only.**

1. At the top of this page, click the green **Use this template** button -> **Create a new repository**. *(No button? Use **Fork** and tell a coach.)*
2. Name it after your team, choose **Public**, and click **Create repository**.
3. Go to **Settings -> Collaborators** and add every teammate's GitHub username.
4. Paste the repo URL where everyone on your team can see it.

### Step 2: Get into your Google Cloud project

Follow your facilitator's instructions to open your shared Google Skills project. **There is one project per team.** You all share Owner access and see the same BigQuery datasets, which also means you can overwrite each other if you do not coordinate table and service names.

### Step 3: Everyone: get into Cloud Shell

**Cloud Shell is where you will work** (alongside your preconfigured Antigravity workstation if provided at your venue). It already has `gcloud`, `bq`, Python, Node, `git`, Docker, and the Antigravity CLI (`agy`) installed.

1. In the Google Cloud console, click the **terminal icon (`>_`) in the top right** so Cloud Shell opens attached to *this* project and browser session.
2. Clone your team's repository and enter it:

   ```bash
   git clone https://github.com/YOUR-TEAM/YOUR-REPO.git
   cd YOUR-REPO
   ```

3. Open the repository as a workspace in Cloud Shell Editor:

   ```bash
   cloudshell workspace .
   ```

#### One repo, one branch per lane

Eight to ten people committing straight to `main` will collide right before submission. Create a branch per lane from minute one:

```bash
git checkout -b data        # or agent, frontend, story
```

Merge into `main` whenever your lane has something another lane needs (such as the embedded table SQL or the deployed agent URL). Keep your files inside `$HOME` (your cloned repo), because `$HOME` persists across Cloud Shell restarts while directories outside it do not.

Helpful references:
[Using Cloud Shell](https://docs.cloud.google.com/shell/docs/using-cloud-shell)
·
[Cloud Shell Editor overview](https://docs.cloud.google.com/shell/docs/editor-overview)

#### Strongly recommended: Antigravity, the IDE and the CLI

Antigravity is Google's agentic coding environment, already available in two forms:

- **The Antigravity IDE:** Launched from the button in your Google Skills lab environment. It reads your repository, proposes multi-file edits you review before accepting, runs terminal commands, and tests in a browser.
- **The Antigravity CLI (`agy`):** Preinstalled in Cloud Shell with zero setup:

  ```bash
  agy
  ```

  Where it saves the most time in a 4.5-hour sprint:
  - **Agent lane:** scaffolding ADK boilerplate, wrapping your `VECTOR_SEARCH` SQL inside a Python tool, and drafting Cloud Run deployment configs.
  - **Data lane:** iterating on post-search eligibility SQL and pre-aggregated quarterly filing CTEs.
  - **Anyone stuck on an error:** paste the traceback and let it inspect your actual files. Use `/diff` to review pending edits before accepting and `/permissions` to control autonomy.

[Antigravity: getting started](https://antigravity.google/docs/getting-started)
·
[IDE overview](https://antigravity.google/docs/ide/overview/)
·
[CLI install and auth](https://antigravity.google/docs/cli/install)
·
[CLI hands-on codelab](https://codelabs.developers.google.com/antigravity-cli-hands-on)

### Step 4: Load the data

**Data lane's job.** One person runs it while the other lanes start immediately.

1. In the Google Cloud console, search for **Colab Enterprise** and open it.
2. **You will be prompted to enable required APIs. Accept them.** When the Colab Enterprise home page loads, it often displays a *second* **Enable APIs** banner at the top. Click that too. Seeing two prompts on a fresh project is expected.
3. Go to **My Notebooks** -> **Import** -> source **URL**, and paste this raw notebook URL:

   ```text
   https://raw.githubusercontent.com/Bornism/A4I2026-challenge-housing/main/notebooks/c_housing_01_load_explore.ipynb
   ```

   *(If your team modifies the notebook later, get your own copy's raw URL by opening the file on GitHub and clicking **Raw**.)*
4. Click **Import**, open the notebook, set `METRO` in the first code cell, and run the cells top to bottom. Read the markdown explanations between cells: Section 2 proves why `LIKE` fails, Section 5 exposes the 4x quarterly eviction fan-out, Section 6 verifies 311 PII scrubbing, and Section 12 runs 26 automated validation checks.

**Headless CLI Fallback (`scripts/load.sh`):**
If Colab Enterprise is slow or unavailable, run the headless loader from your cloned repository root in Cloud Shell:

```bash
bash scripts/load.sh                 # defaults to san-francisco
bash scripts/load.sh chicago         # or new-york, austin, baton-rouge, cincinnati
bash scripts/load.sh --list          # list all six pre-staged metros
```

Invoke it with `bash` rather than `./scripts/load.sh` so file permissions never block you. Every run replaces tables cleanly (`--replace`), so switching metros or re-running halfway through is completely safe.

### What you'll have

Five validated tables in `<your-project>.a4i_housing` for your selected metro (default `San Francisco` counts shown alongside the 6-metro starter pack total):

| Table | Grain | Loaded rows (`San Francisco` default) | 6-metro pack total | Provenance summary |
|---|---|---:|---:|---|
| `acs_tract_housing_tenure` | 1 row / census tract | 42 | 378 | **Real public** US Census ACS 5-Year rent burden, income, TIGER polygons & `audit_*` shares |
| `court_eviction_filings` | 1 row / tract-quarter (`4` quarters/tract) | 168 | 1,512 | **Modeled** quarterly tract filings calibrated to county court & ACS baselines |
| `municipal_311_housing_complaints` | 1 row / complaint | 174 | 1,044 | **Real public** 100-block municipal 311 narratives (`165`/metro) + `9` `[Planted Case]` decoys/metro |
| `rental_relief_program_bulletins` | 1 row / relief program | 4 | 24 | **Public policy text** & structured habitability/residential eligibility flags |
| `municipal_housing_ordinance_statutes` | 1 row / statute section | 3 | 18 | **Public statutory text** covering habitability, escrow, and anti-retaliation |

---

## The data, and why we chose it

**Say plainly what is real and what is modeled.** Judges reward teams who inspect `data_provenance` and state boundaries honestly:

- **Census housing tenure is real** (US Census ACS 5-Year `B25070` & `B19013`).
- **Municipal 311 narratives are real public records** across San Francisco, Chicago, New York, Austin, Baton Rouge, and Cincinnati, redacted to the 100-block (`block_address`) and pre-scrubbed on disk (plus idempotently scrubbed at load) for residual citizen PII, paired with 9 clearly marked `DECOY-*` test cases per metro (`Example Teaching Way [Planted Case]`).
- **Quarterly eviction filings are modeled**, because Princeton's Eviction Lab has zero California coverage and only ZIP-level New York City coverage. Never present modeled tract filing counts as live court dockets.

### One thing we deliberately excluded from scoring

Every challenge in this series excludes race and ethnicity (`audit_*` columns) as a model, retrieval, or ranking input, and requires them instead for a **post-output Equity Audit**. Severe rent burden, habitability complaints, and income are direct structural measures. Keep `audit_*` out of your prompts, embeddings, and scoring formulas.

### What "auditing the outcome" actually means

1. Run your triage or outreach workflow across a batch of intakes or tracts in your chosen metro.
2. Join the selected tracts back to `acs_tract_housing_tenure` (`audit_black_share`, `audit_hispanic_share`, `audit_asian_share`, `audit_indigenous_share`, `audit_white_share`, plus `renter_hh_rent_50_pct_plus_count` and `no_vehicle_rate`).
3. Compare your prioritized tracts against the metro baseline and answer a critical housing question: **does requiring an open 311 ticket accidentally penalize severely rent-burdened immigrant or low-income tracts where tenants fear retaliation if they call city inspectors?** Showing that trade-off with real numbers will stand out immediately to judges.

---

## Going further

### What will set yours apart

- **Catch every planted decoy (`DECOY-*`) and explain why.** Show a judge a prompt where raw semantic similarity ranked a closed or commercial complaint #1, and show your post-filter catching it cleanly.
- **Handle 311 under-reporting.** In metros like Baton Rouge (high severe rent burden, very few open 311s), build a fallback pathway when a tenant describes severe habitability defects on a block with zero prior city inspections.
- **Pre-hearing deadline awareness.** Weight emergency funds and statutory defenses differently when a hearing is 72 hours away versus 30 days away.

### The add-on we'd build if we had another four hours

**A tenant inspection-request & evidence intake agent.** When no open 311 record exists on a tenant's block, have a secondary agent interview the tenant in plain language, structure the exact municipal code category, draft a clean 311 inspection request alongside photographic checklist guidance, and route them to relief funds where `requires_open_habitability_case = FALSE` while the city inspection is pending.

---

## Bringing your own data

**Augment, do not replace.** Get the five starter tables working first. Any external dataset you add must clear all six licensing rules:

| Rule | Why |
|---|---|
| ❌ No **NonCommercial** (`CC BY-NC`) | Winning projects are promoted publicly |
| ❌ No **NoDerivatives** (`CC BY-ND`) | Building derived outputs is the core task |
| ❌ No **Share-Alike** (`ODbL`, `CC BY-SA`) | Encumbers your repository |
| ❌ No **individual-level personal data (PII)** | Never load tenant names, unit numbers, or individual eviction defendants |
| ❌ No **unstated license** | Unlicensed web scraping grants zero reuse rights |
| ✅ **Public domain, CC0, US Government / municipal open-data works** | Safe to stage and cite |

**The license trap most likely to catch you:** anything derived from **OpenStreetMap carries the `ODbL` share-alike license**, and private eviction-scraping or landlord-rating sites are almost always all-rights-reserved or NonCommercial (`CC BY-NC`). Check the license for thirty seconds before loading, and ask a coach if you are unsure.

---

## What's in this repository

```text
README.md                                      This challenge brief and team runbook.
notebooks/c_housing_01_load_explore.ipynb      Step 1: Load, scrub, explore, and validate all 5 tables.
notebooks/c_housing_90_publish_snapshot.ipynb  Maintainers only (publishes snapshots to Cloud Storage).
scripts/load.sh                                Headless CLI fallback that loads and verifies your metro.
scripts/README.md                              Usage and verification notes for scripts/load.sh.
data/*.parquet                                 Pre-staged 6-metro GeoParquet starter tables (see data/README.md).
agent/                                         Empty on purpose. Your ADK agent goes here.
```

---

## How you'll be judged

**"Finished" is not the goalpost.** Almost nobody completes every stretch idea in 4.5 hours. A team that gets three quarters of the way with clear reasoning, verified guardrails, and honest limitations will beat a team that demos something polished and hollow.

**You are judged against the track you chose**, not against a single canonical answer. Say which metro and track you picked right at the start of your deck and video.

**Judges score your submission asynchronously, not a live Q&A.** Put the answers to the questions below directly into your deck and your **<=3-minute pitch video**:

| Dimension | Weight | The question judges are asking |
|---|---:|---|
| **Impact & insight** | 30 | Would a legal-aid paralegal or housing navigator actually use this on Monday morning? |
| **Technical execution** | 30 | Is the agent deployed and working, using ADK, MCP, a custom tool, and genuine `AI.EMBED` + `VECTOR_SEARCH`? |
| **Rigor & judgment** | 25 | Did you avoid the 4x quarterly join trap, filter out `DECOY-*` cases, state real vs. modeled data honestly, and run the `audit_*` Equity Audit with numbers? |
| **Craft & communication** | 15 | Does your <=3-minute video demonstrate a live end-to-end run clearly, and can you justify your UI choice? |
| **Bonus: range** | **+10** | Extra ambition (such as BYOD enrichment or secondary agent workflows) that sharpens the core solution |

Bonus sits **on top** of the 100, so ambition never cannibalizes the fundamentals. Nail the core workflow and add nothing extra, and you can still win.

### What "Rigor and judgment" actually means

This is a quarter of your score and the easiest place to stand out:

1. **Data decisions you can defend:** Know plainly that ACS housing tenure and 100-block 311 narratives are real public records, `court_eviction_filings` is modeled (because Eviction Lab lacks California and tract-level NYC coverage), and 9 `DECOY-*` rows per metro are planted eligibility traps.
2. **Validation:** Show that you ran the notebook's validation checks (`Section 12`), preserved 11-character leading-zero GEOIDs, and avoided 4x quarterly join inflation.
3. **Bias and under-reporting handling:** Keep `audit_*` columns out of scoring and embeddings, run the post-output Equity Audit (`Section 11`), and report actual numbers on whether open-311 filtering under-counts "silent distress" neighborhoods.
4. **Knowing what your system cannot prove:** A 100-block 311 complaint corroborates block-level conditions, not an individual apartment lease or unit inspection. Saying that out loud builds trust.

### A note on decisions generally

Which metro you pick, whether you embed raw complaint narratives or enriched summaries, how you rank competing relief funds, and which front-end surface you choose have no single answer key. Judges reward teams who make those choices on purpose and state why.

---

## Getting help

Start with your **Table Captain**, then the **ROI facilitator** on the floor and the event Discord channel. If anything in the data or setup misbehaves, run **Section 14 (Diagnostic summary)** at the bottom of `notebooks/c_housing_01_load_explore.ipynb` and share the printed output block.
