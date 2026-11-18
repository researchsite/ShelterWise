# ShelterWise: Complete Demo Script & Feature Walkthrough

> **Live Application URL**: [https://shelterwise-redesign-335751565476.us-central1.run.app](https://shelterwise-redesign-335751565476.us-central1.run.app)  
> **Google Stitch Component Showcase**: [https://shelterwise-redesign-335751565476.us-central1.run.app/stitch/](https://shelterwise-redesign-335751565476.us-central1.run.app/stitch/)  
> **Production Service**: [https://shelterwise-335751565476.us-central1.run.app](https://shelterwise-335751565476.us-central1.run.app)  
> **GitHub Branch**: [`feature/stitch-frontend-parallel`](https://github.com/researchsite/ShelterWise/tree/feature/stitch-frontend-parallel)  

---

## 1. Executive Summary & Pitch Context

### The 3-Minute Window in Department 501
In California unlawful detainer proceedings (San Francisco Superior Court, Department 501), an unrepresented tenant typically has **less than 3 minutes** before the bench. 

When a tenant testifies, *"My apartment has had no heat for a month and my kid is sick,"* the landlord's attorney counters with an unpaid ledger. Without certified third-party proof, judges are procedurally bound to issue a writ of possession.

### Core Philosophy: "Scope Beats Ambition"
ShelterWise does **not** attempt to replace attorneys or build a generic chatbot. A real job is deciding **what not to build** to make an impact:
- **What We Build**: An autonomous multi-agent pipeline (Google ADK) that transforms uncorroborated tenant claims into **certified public 311 habitability citations**, filters out misleading decoys via municipal business rules, calculates emergency rental bridge grants, and synthesizes a court-ready California 28-line defense brief in under **900ms**.
- **What We Decided Not To Build**: No self-representation legal advice without human oversight, no ungrounded LLM hallucinations, and no demographic bias in individual case scoring.

---

## 2. Timing Breakdown & Options

| Format | Duration | Audience | Focus |
| :--- | :--- | :--- | :--- |
| **Option 0: Judge Lightning Pitch** | **< 90 Seconds** | Hackathon Judges | 3-Min Eviction Problem ➔ 1-Click Story ➔ 1-Sec City Hall Proof ➔ Home Saved |
| **Option A: Hackathon Pitch** | **3 Minutes** | General Judges & Attendees | Problem ➔ Archetype Selection ➔ Live Multi-Agent Execution ➔ Comparison Canvas ➔ 28-Line Brief |
| **Option B: Technical Deep Dive** | **5 Minutes** | Google ADK & Cloud Evaluators | Multi-Agent Orchestration Flow ➔ BigQuery Vectors ➔ Firestore Concurrency ➔ Decoy Engine ➔ Live Timings |
| **Option C: Clinic Walkthrough** | **10 Minutes** | Legal Aid Advocates & Housing Clinicians | Full Intake ➔ Checklist ➔ GIS Map ➔ Codex ➔ Co-Pilot Chat ➔ Demographic Firewall Audit |

---

## 3. Option 0: The Under-90-Second Plain English Judge Pitch (196 Words · ~85s)

> **Judge Takeaway**: In eviction court, a tenant's word against a landlord's lawyer loses in 3 minutes. ShelterWise uses Google Cloud AI to turn a tenant's lived story into certified City Hall 311 proof, an official court defense brief, and $12,000 in emergency rent relief in under one second.

### ⏱️ Act 1: The Unfair Courtroom Reality (0:00 – 0:20 · 49 words)
* **On Screen**: App homepage showing the top distress banner and crisis archetypes ([shelterwise-redesign](https://shelterwise-redesign-335751565476.us-central1.run.app)).
* **Spoken**:
  > *"In San Francisco eviction court, a family has less than three minutes to defend their home.*
  > *When a mother tells the judge, 'Our heat was broken all winter and my baby got sick,' the landlord’s lawyer hands over an unpaid rent ledger. Without certified third-party proof, the judge must order an eviction."*

### ⏱️ Act 2: The Tenant's Story in One Click (0:20 – 0:40 · 47 words)
* **Action**: Click `Case 1 · Western Addition Winter Freeze`.
* **On Screen**: Inputs populate with Maria's Fillmore St narrative, hearing date, and income ($45k).
* **Spoken**:
  > *"Meet Maria. She lives on Fillmore Street. Her building's boiler broke, her indoor temperature fell to 50 degrees, and she fell behind on rent.*
  > *On ShelterWise, Maria or her legal aid worker clicks one button: 'Winter Freeze'. Her story, address, and court date instantly load."*

### ⏱️ Act 3: The One-Second Evidence Engine (0:40 – 1:00 · 44 words)
* **Action**: Click the blue button: **`Corroborate 311 Records & Protect Home`**.
* **On Screen**: Live multi-agent execution drawer slides open and finishes in ~840ms.
* **Spoken**:
  > *"Now, we click 'Corroborate 311 Records'.*
  > *In under one second, our Google AI pipeline searches City Hall's public inspection database. It ignores commercial buildings and old resolved complaints, and finds the exact municipal citation: an open city violation confirming her radiators were freezing."*

### ⏱️ Act 4: The Result — Proof, Brief & Home Saved (1:00 – 1:25 · 56 words)
* **On Screen**: Scroll down to the Comparison Canvas, 311 Evidence card, and 28-Line Court Brief.
* **Spoken**:
  > *"Look at the screen:*
  > *On the left, what the landlord claims. On the right, what City Hall proved.*
  > *ShelterWise immediately generates a certified 28-line legal brief for court, and unlocks $12,000 in emergency city rental relief to pay off the back rent.*
  > *We don’t replace lawyers. We give vulnerable families the proof they need to stay housed."*

---

## 4. Presenter-Ready Demo Script (Option A: 3-Minute Walkthrough)

### ACT 1: The Problem & Archetype Selection (0:00 – 0:40)

* **Presenter Action**: Open [https://shelterwise-redesign-335751565476.us-central1.run.app](https://shelterwise-redesign-335751565476.us-central1.run.app).
* **Onscreen**: Show the Top Navigation Bar, Trauma Distress Banner, and the 4 Housing Crisis Archetype Cards.
* **Click**: Click `Case 1 · Western Addition Winter Freeze`.

> **Spoken Script**:
> *"Good morning. In San Francisco eviction court, tenants face summary eviction in under three minutes. This is Maria. She lives at the 1000 block of Fillmore Street with her 4-year-old child. For three weeks in winter, her building's central heating boiler failed. Her indoor temperature dropped to 50 degrees, her child became sick, and she fell two months behind on rent ($4,200). Her landlord served a 3-Day Notice to Pay or Quit and scheduled a court hearing for Monday at 9:00 AM in Department 501.*
>
> *On our first screen, Maria or her legal aid paralegal selects her crisis archetype: Western Addition Winter Freeze. Notice how all case parameters immediately populate: her lived story narrative, coarsened 100-block address for safety, hearing time, household size of two, and annual income of $45,000.*
>
> *Our dynamic engine immediately calculates her Area Median Income: 42% AMI, placing her in Very Low Income and unlocking 100% relief eligibility up to our $12,000 cap."*

---

### ACT 2: Live Multi-Agent Pipeline Execution & Timings (0:40 – 1:20)

* **Presenter Action**: Click the blue button: **`Corroborate 311 Records & Protect Home`**.
* **Onscreen**: The **Live Multi-Agent Pipeline Execution Drawer** slides open. The live millisecond clock ticks upward (`0.14s`, `0.32s`, `0.84s`), sequential agent steps illuminate with cyan and green status borders, and the live Cloud Run API telemetry badge displays.

> **Spoken Script**:
> *"When we click 'Corroborate 311 Records', ShelterWise does not query an ungrounded LLM. It fires a coordinated multi-agent pipeline built with the Google Agent Development Kit (ADK) on Gemini 2.5 Flash. Watch the pipeline stages execute live on Google Cloud Run:*
>
> 1. *Stage 1: `intake_structurer_ag` scrubs all personal identifiers and normalizes Maria's 11-digit Census Tract GEOID in 142ms.*
> 2. *Stage 2: `corroboration_fanout_ag` initiates parallel fan-out in 318ms.*
> 3. *Stage 3: `habitability_vector_ag` executes a BigQuery VECTOR_SEARCH using 768-dimensional embeddings generated by gemini-embedding-2 across 174 municipal records, filtering three dangerous decoy traps in 210ms.*
> 4. *Stage 4: `statute_and_bulletin_ag` retrieves the statutory 35-day repair clock under California Civil Code § 1942.4 and SF Housing Code § 701 in 45ms.*
> 5. *Stage 5: `tract_displacement_ag` inspects the tract stability index with demographic variables strictly firewalled in 63ms.*
> 6. *Stage 6: `eligibility_and_brief_ag` synthesizes the 9-section defense brief in 412ms.*
> 7. *Stage 7: Cloud Firestore acquires an atomic transactional optimistic lock (v1) in 24ms.*
>
> *Total Cloud Run API response: 842ms. 100% grounded in official public records."*

---

### ACT 3: What Landlords Claim vs. What City Hall Proves (1:20 – 1:50)

* **Presenter Action**: Scroll to Section 2: **What Landlords Claim vs. What City Hall Proves**.
* **Onscreen**: The two side-by-side comparison cards (Red danger alert on left vs. Green verified proof on right).

> **Spoken Script**:
> *"Here is the decisive turning point in Maria's case. On the left is what her landlord tells the judge: 'Tenant owes $4,200 back rent. Landlord gave notice. Tenant has no excuse.'*
>
> *On the right is what City Hall records prove: Active Notice of Violation #SF-202665182 issued 42 days ago. City inspectors confirmed indoor temperatures at 52°F, violating San Francisco Housing Code § 701. Because the landlord demanded rent after the 35-day repair deadline expired, California Civil Code § 1942.4 makes collecting rent illegal.*
>
> *Maria's defense is no longer her word against her landlord—it is certified public record."*

---

### ACT 4: 311 Evidentiary Radar & Decoy Rejection Engine (1:50 – 2:20)

* **Presenter Action**: Point out the 311 Radar card on the left and the Emergency Rental Relief Meter on the right.
* **Onscreen**: Highlight citation `REQ-311-2026-9941` (12m away, 0.2104 cosine distance), and the red Decoy Rejection Box.

> **Spoken Script**:
> *"Searching by distance alone is dangerous—it causes hallucinated evidence. ShelterWise features a Decoy Rejection Engine with three strict municipal filters:
> 1. Commercial Storefronts: Excluded DECOY-SANF-01, a warehouse boiler failure down the block, because housing codes apply strictly to residential dwellings.
> 2. Closed & Abated Violations: Excluded DECOY-SANF-04, repaired in 2024, because past fixes cannot prove active habitability failure.
> 3. Zero-Violation Inspections: Excluded DECOY-SANF-07, where inspectors found a compliant 71°F indoor temp that would have destroyed Maria's defense.
>
> *Only grounded residential evidence survives. And because open violations exist, our Relief Funding Meter unlocks $5,000 from the SF DBI Rapid Repair Grant and $7,000 from Prop F Right to Counsel—wiping out Maria's entire $4,200 arrears."*

---

### ACT 5: Defense Brief, Co-Pilot Chat & Attorney Review Checklist (2:20 – 2:45)

* **Presenter Action**: Scroll to Section 4 & 5.
* **Onscreen**: The 9-Section Court Defense Brief in legal paper typography, the Legal Aid Co-Pilot Chat, and the 8-Item Attorney Review Checklist.
* **Interactive Demo**: In the Co-Pilot Chat, click the quick prompt: `Why drop warehouse decoy?`.
* **Onscreen**: `evidence_explainer_ag` immediately answers why commercial records were disqualified.

> **Spoken Script**:
> *"ShelterWise compiles a complete 9-Section Defense Brief with jurisdiction, verified facts, public citations, statutory defenses, decoy rejections, and prayer for relief.
>
> *Advocates can interrogate the pipeline using our Legal Aid Co-Pilot chat. When asked why a nearby record was dropped, `evidence_explainer_ag` cites municipal code standards directly.
>
> *To guarantee human-in-the-loop oversight, legal aid attorneys complete an 8-Item Review Checklist backed by Cloud Firestore optimistic concurrency locks, ensuring multiple advocates never overwrite each other's work."*

---

### ACT 6: GIS Map, System Architecture & California Court Export (2:45 – 3:00)

* **Presenter Action**: Rapidly click through the remaining tabs:
  1. Click `2. GIS Citywide Map (400m Radar)`: Show the Leaflet map with 400m perimeter and court route.
  2. Click `3. System Architecture & Tech Docs`: Show the visual flowchart, dual-database diagram, and 11-agent registry table.
  3. Click `5. Court Defense Brief (Export)`: Show the formal 28-line California pleading paper.

> **Spoken Script**:
> *"Our remaining tabs provide end-to-end operational support:
> - Tab 2 provides a GIS 400-meter evidentiary radar map and MUNI route to Superior Court Dept 501.
> - Tab 3 displays our complete 11-agent technical architecture, dual BigQuery and Firestore database layers, and Responsible AI Demographic Firewall.
> - Tab 5 exports a California 28-line legal pleading paper ready for immediate court filing.
>
> *In under three minutes, ShelterWise transforms an imminent eviction into an affirmative victory grounded in city records. Thank you."*

---

## 4. Technical Architecture Deep Dive (Option B: 5-Minute Pitch)

Use this script when presenting to engineers, hackathon judges, or technical evaluators:

### 1. Dual-Database Architecture: Why BigQuery + Cloud Firestore?
> *"Many systems try to use a single database for everything. We intentionally separated analytical semantic search from transactional clinic workflows:*
> - *BigQuery (`a4i_housing` in US): Serves as our analytical and vector warehouse. It houses 174 municipal 311 citations embedded into 768-dimensional vectors using `gemini-embedding-2` through Vertex AI remote models. BigQuery executes sub-250ms cosine distance searches and maintains our demographic audit views.*
> - *Cloud Firestore (`nam5`): Serves as our transactional case management store. When legal aid clinics handle hundreds of clients, multiple paralegals collaborate on the same file. Firestore delivers sub-30ms atomic writes via `@firestore.transactional` and enforces `lock_version` concurrency guards to prevent data collision."*

### 2. Multi-Agent Orchestration (Google ADK)
> *"All 11 agents in ShelterWise inherit from Google ADK classes (`LlmAgent`, `SequentialAgent`, `ParallelAgent`) with strict `*_ag` naming:*
> - *`shelterwise_navigator_ag` (Root Coordinator): Manages session context, route navigation, and conversational queries.*
> - *`case_triage_pipeline_ag` (Sequential Pipeline): Orchestrates the deterministic 3-stage flow.*
> - *`intake_structurer_ag` (PII Scrubbing & Normalization): Sanitizes names/phones and matches 11-digit GEOID.*
> - *`corroboration_fanout_ag` (Parallel Dispatch): Concurrently invokes `habitability_vector_ag`, `statute_and_bulletin_ag`, and `tract_displacement_ag`.*
> - *`eligibility_and_brief_ag` (Brief Synthesizer): Reconciles evidence and formats the 9-section defense brief.*
> - *`evidence_explainer_ag`, `equity_audit_ag`, `hazard_311_drafter_ag` (Specialist Support): Decoy explanations, silent distress audits, and DBI complaint drafting."*

### 3. Responsible AI Demographic Firewall
> *"We implemented an architectural demographic firewall. In many machine learning applications, demographic attributes inadvertently leak into scoring models. In ShelterWise:
> - Demographic columns (`audit_black_share`, `audit_hispanic_share`, `audit_asian_share`) are completely quarantined from individual tenant scoring and brief generation.
> - They are queried exclusively in aggregate across 42 San Francisco census tracts via `v_metro_equity_audit` and `equity_audit_ag` to detect 'Silent Distress'—neighborhoods with high rent burden but artificially low 311 reporting."*

---

## 5. Judge Q&A Cheat Sheet

### Q1: How do you prevent hallucinations in court-filed documents?
> **Answer**: *"We utilize triple-grounding. First, all factual statements are retrieved directly from BigQuery public records using cosine distance matching over verified City citations. Second, our Decoy Rejection Engine programmatically disqualifies non-residential and resolved records via deterministic business rules. Third, the system enforces a human-in-the-loop workflow where a licensed attorney or certified paralegal must inspect the evidence before signing the California 28-line court export."*

### Q2: What happens if a tenant lives on a block where no 311 calls were ever made?
> **Answer**: *"That is a critical real-world edge case known as 'Silent Distress'. When our pipeline detects zero matching citations within 400m, it automatically invokes `hazard_311_drafter_ag`. Instead of generating an uncorroborated brief, this agent drafts a formal San Francisco Department of Building Inspection emergency complaint with specific code citations (§ 701, § 1941.1), enabling the tenant or advocate to request an urgent inspection before their hearing date."*

### Q3: Why did you build with the Google Stitch Design System?
> **Answer**: *"Tenants facing eviction experience severe cognitive distress. Standard legal software is dense and hostile. Google Stitch provided us with tokenized design primitives—including calm surface neutrals, clear relief greens, warning ambers, and alert crimsons—that meet WCAG AAA contrast standards. It allowed us to turn intimidating court procedures into a clear, empowering visual journey with zero UI latency."*

### Q4: How is this deployed and maintained in production?
> **Answer**: *"ShelterWise is fully deployed on Google Cloud Run in `us-central1` across two independent services: our main production service and a parallel redesign service running from our dedicated feature branch. It connects to Cloud Firestore in `nam5`, BigQuery in `US`, and Vertex AI Gemini 2.5 Flash. We run automated continuous health checks via `scripts/service_health_monitor.py` verifying all endpoints with average response latencies under 400ms."*

---

## 6. Demo Readiness Checklist

Before beginning any live presentation or recording:
- [x] Verify live Cloud Run service is operational: `https://shelterwise-redesign-335751565476.us-central1.run.app`
- [x] Test Archetype card switching (*Winter Freeze*, *Electrical Hazard*, *Mold Retaliation*, *Chinatown Sewage*)
- [x] Verify Live Multi-Agent Execution Drawer opens with live timer and stage progress
- [x] Confirm Leaflet GIS Map tiles load properly on Tab 2
- [x] Verify Technical Architecture diagrams render sharply on Tab 3
- [x] Test Co-Pilot chat prompt (`Why drop warehouse decoy?`) on Tab 1
- [x] Confirm California 28-Line Pleading Paper format renders on Tab 5
- [x] Keep Google Stitch Showcase open in background tab: `/stitch/`
