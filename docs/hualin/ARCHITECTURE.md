# ShelterWise — Architecture

**Owner:** Hualin · **Scope:** San Francisco · Track "Today at intake" · Python + Google ADK · Agent Runtime

![architecture](./architecture.svg)

---

## 1. The problem in one paragraph

A tenant walks into legal aid with an eviction hearing in a few days and a unit with no heat. If the city already has an **open** housing complaint about that block, the tenant may have legal defenses and access to emergency funds. Today nobody connects the city's 311 records to the court case before the hearing.

**ShelterWise does that link-up in about a minute:** the paralegal describes the case in plain words, and the agent returns a brief the attorney can act on.

## 2. The core problem (what is actually hard)

Finding records is the easy part. **The hard part is not over-claiming.** There are three traps:

| # | Trap | Example | Our answer |
|---|---|---|---|
| 1 | **Different words, same problem** | Tenant: "radiators stone cold". City record: "inadequate heating below code minimum" | **Vector search** (`AI.EMBED` + `VECTOR_SEARCH`) matches by meaning, not by keyword |
| 2 | **Look-alike records that don't count** | "Boiler shutdown, no heat… *commercial warehouse*", or "broken boiler… *landlord replaced it, case closed*" | After the search, **hard rules in code** keep only `Residential` + still open (`closed_date IS NULL`). Each dropped record keeps its reason |
| 3 | **Saying more than the evidence proves** | A complaint on the same block ≠ proof about *this* apartment. Modeled filing counts ≠ a real court docket. A statute with a 35-day clock may not apply yet | Funds get **ELIGIBLE / CONDITIONAL / INELIGIBLE**, statutes get "applies / not yet", and a **verifier** blocks any brief that overstates |

> In one sentence: **search wide by meaning, then filter strictly by rules, then only claim what the record proves.**

---

## 3. End-to-end sample

### 3a. Input: what the paralegal types (in our UI; `adk web` while testing)

```text
Tenant at the 1000 block of Fillmore St. No heat for weeks, she says it's about
50 degrees inside and her kid keeps getting sick. Nonpayment hearing Monday
Nov 23 at 9am. Single mom, behind about two months on rent. What do we have?
```

*(Intake date: Thursday 2026-11-19, so the hearing is 4 days away.)*

### 3b. What the agent extracts first (`state.intake`)

```json
{
  "address_text": "1000 Block Fillmore St",
  "lat": 37.77907, "lng": -122.43185,
  "hazards": ["heat"],
  "search_query": "no heat in residential dwelling unit, indoor temperature below code minimum",
  "hearing_date": "2026-11-23",
  "days_to_hearing": 4,
  "tenant_has_own_dbi_case": null,
  "household_income_pct_ami": null
}
```

### 3c. Output: the Tenant Stabilization Brief

Our UI renders `state.brief` (JSON) as a **brief card** next to the chat. In `adk web` the same content shows up as a chat reply.
*The records, laws, funds and tract numbers below are real SF data. Which decoys rank highest is illustrative until the embeddings are built.*

```markdown
## Tenant Stabilization Brief: 1000 Block Fillmore St (hearing in 4 days)

### 1. City records that support the tenant
| Request ID    | Block                  | Status                 | Opened     | Match  |
|---------------|------------------------|------------------------|------------|--------|
| SF-202665182  | 1000 Block Fillmore St | Open - Active DBI Case | 2026-11-03 | strong |
> "...resident has been without heat... it's 52 degrees in the dwelling unit."

**Excluded look-alikes (similar text, but they don't count):**
- DECOY-SANF-01: "no heat, ceiling leak… commercial retail warehouse" → *commercial property*
- DECOY-SANF-04: "broken central boiler, freezing rooms" → *closed: landlord fixed it*
- DECOY-SANF-07: "winter readiness inspection… boiler at 71F" → *closed: no violation found*

### 2. Laws
| Citation | Applies? | Why |
|---|---|---|
| SF Admin. Code Ch. 37 & Prop F | **Yes** | Just-cause protection + city-funded lawyer for eviction cases |
| Cal. Civ. Code § 1942.5 (anti-retaliation) | **Yes, if** the tenant herself complained to the city | 180-day protection after a complaint |
| Cal. Civ. Code § 1941.1 & § 1942.4 (rent-demand bar) | **Not yet** | The violation must stay unfixed **more than 35 days**; this case opened 2026-11-03 (16 days ago). Recheck on 2026-12-09 |

### 3. Emergency help (ranked for a 4-day deadline)
| Program | Verdict | Still to confirm |
|---|---|---|
| Prop F Right to Counsel: lawyer + up to $6,000 (Eviction Defense Collaborative) | **CONDITIONAL**, call first (4 days) | DBI case covers *her unit* · evictiondefense.org |
| SF ERAP: up to $12,000 back rent (MOHCD) | **CONDITIONAL** | Income ≤ 80% AMI · sf.gov/renthelp |
| MEDA Family Stabilization: up to $7,500 | **CONDITIONAL** | Income ≤ 60% AMI + medical leave or wage loss · medasf.org |
| DBI Relocation Bridge: up to $8,500 hotel stipend | **CONDITIONAL** | Open no-heat notice on *her unit* · sf.gov/dbi |

**Ask the tenant:** (1) Do you have your own DBI case number? (2) Household size and yearly income?

### 4. Neighborhood context (tract 06075016300)
- Severe rent burden: 265 of 1,653 renter households (16.0%), vs about 17.5% across SF
- Eviction filings: about 65 per year *(MODELED estimate, not real court records)*

### 5. What this does NOT prove
- The city record is about the **block**, not her apartment. Ask whether she has her own DBI case number.
- Filing counts are modeled from county totals, not her court docket.

### 6. Draft intake memo (for attorney review)
> Client resides on the 1000 block of Fillmore St, facing a nonpayment hearing 11/23...
```

### 3d. Follow-up questions the agent should handle in the same session

| Paralegal asks | What happens |
|---|---|
| "Why did you drop the warehouse boiler one?" | `explain_exclusion("DECOY-SANF-01")` → "commercial property, no residential tenants" |
| "She has her own DBI case number" | The relief check runs again: Prop F and the DBI Bridge become **ELIGIBLE** |
| "2-person household, about $45k a year" | Income is checked against AMI: ERAP becomes **ELIGIBLE**. This needs the official MOHCD AMI chart in `funds_sf.yaml`; until then income stays "to confirm" (never guessed) |
| "How many open heat complaints are in this tract?" | BigQuery MCP query |
| *(no open record near the block)* | Hands off to `inspection_request_drafter`: drafts a 311 request plus a photo checklist, and points to ERAP/MEDA meanwhile |

---

## 4. How it works (6 steps)

```
paralegal ─► navigator (chat) ─► brief_pipeline:
                                   1. understand  the intake                         (LLM)
                                   2. prepare     safety check · scrub personal info · find the block · days to hearing (code)
                                   3. gather      311 evidence + tract context       (code, in parallel)
                                   4. decide      which laws apply + fund verdicts   (code, in parallel)
                                   5. write       memo + plain-language summary      (LLM)
                                   6. verify      no over-claims, assemble the brief (code, sends back for rewrite up to 2x)
```

| Step | Agent | Kind | Reads | Writes |
|---|---|---|---|---|
| chat | `navigator` | LLM (Flash) | user message | calls the tools below; shows **safety alerts first** |
| 1 | `intake_parser` | LLM (Flash) | user message | `state.intake` |
| 2 | `intake_prep` | **code** | `state.intake` + raw message | `state.intake` (lat/lng, tract, days to hearing, scrubbed query), `state.safety` |
| 3 | `evidence_agent` ★ | **code** | `state.intake` | `state.evidence` (kept + excluded with reasons) |
| 3 | `context_agent` | **code** | tract GEOID | `state.tract` |
| 4 | `legal_agent` | **code** | `state.intake`, `state.evidence`, `statutes_sf.yaml` | `state.statutes` (yes / yes, if / not yet + why) |
| 4 | `relief_agent` | **code** | `state.intake`, `state.evidence`, `funds_sf.yaml` | `state.relief` |
| 5 | `brief_writer` | LLM (Pro) | all of the above | `state.brief_draft` (memo, summary, questions for the tenant) |
| 6 | `verifier` | **code** | draft + all facts | `state.brief` (final), or `state.verifier_feedback` |
| fallback | `inspection_request_drafter` | LLM (Flash) | `state.intake` | a draft 311 request |

★ `search_corroborating_complaints()` is the "tool we built" the challenge asks for.

**Rule of thumb:** LLMs read and write language. **Code makes every yes/no decision.** The brief's facts (records, verdicts, laws, numbers) are filled in by code; the LLM writes only the memo and summary, and the verifier checks those against the facts.

**Why laws are checked by code, not an LLM:** only 3 SF laws, each with a clear test (e.g. § 1942.4 needs the violation unfixed **more than 35 days**). A rule table can't skip the clock; an LLM can.
**Why laws wait for evidence:** those clocks depend on the **open date** of the matched complaint.

### Ideas adopted from Shiva's doc (`shiva` branch, `docs/shiva_arc.md`)

| Idea | Where it lives |
|---|---|
| **Join `complaints_embedded` back to the full 311 table** on `request_id`, so lat/lng and citation fields are always present (no need to change the embedded table) | `tools/evidence.py`, `sql/setup.sql` |
| **`v_tract_stability_context` SQL view**: 4 quarters pre-summed, **no `audit_*` columns** | `sql/setup.sql` |
| **Life-safety check first** (water near electrical panel, gas, fire, CO, sewage) → "don't touch the panel, call 911 / DBI" before anything else | step 2, `tools/safety.py` |
| **Scrub personal info** (names, phone, email, unit numbers) before embedding or logging | step 2, `tools/pii.py` |
| **pytest set**: each decoy class caught, GEOID leading zero kept, no `audit_*` in case tools | `agent/tests/` |

## 5. The rules (all in code, all tested)

0. **Safety first.** A life-safety hazard is shown at the very top of the brief, above everything else.
1. **Search wide, then filter.** Take the top 50 matches by meaning, then apply the rules in Python. No SQL `WHERE` before the search (it would cut results *before* ranking).
2. **Keep** a record only if `property_type = 'Residential'` **and** `closed_date IS NULL` **and** it is within 400 m.
3. **Never** filter on the words `DECOY` or `[Planted Case]`. The real rules must catch all 9.
4. **Funds:** **ELIGIBLE** only when every condition is confirmed. Otherwise **CONDITIONAL**, with the list of what's missing (own case number, income vs AMI, …). **INELIGIBLE** when a known fact rules it out. Block evidence alone never confirms an "open case on your unit". The conditions for the 4 SF funds are written once in `funds_sf.yaml`, taken from the bulletin text.
5. **Statutes with clocks:** compare the complaint's open date with the deadline (e.g. 35 days for § 1942.4).
6. **Filings:** add up the 4 quarters per tract **before** joining (otherwise the count is 4x too high). Always label them "modeled".
7. **GEOIDs are text**, never numbers (`06075…` would lose its leading 0).
8. **`audit_*` columns** (race shares) are never used by the agent, only in the offline equity audit. The data layer never selects them, and the MCP tool blocks any SQL that mentions `audit_`.
9. **Personal info is scrubbed** before the search query is embedded or logged.

## 6. Decisions log

| Topic | Decision |
|---|---|
| Pattern | Chat agent (`navigator`) + fixed pipeline called as a tool (`AgentTool`) |
| Guardrails | Python code, not SQL-only, not LLM |
| Laws | Code rule table (`statutes_sf.yaml`) with clocks, replacing "LLM picks from 3"; the LLM only explains |
| MCP | BigQuery remote MCP `https://bigquery.googleapis.com/mcp` (confirmed in Google docs), read-only tools only, SQL mentioning `audit_` blocked |
| Data mode | `SHELTERWISE_DATA=bigquery` (real `VECTOR_SEARCH`) or `local` (parquet + keyword-similarity stand-in, **for offline dev/tests only**, and labeled as such in every result) |
| Deploy | Vertex AI Agent Runtime. ❓ *Open:* a single Cloud Run service (Shiva's proposal) may be simpler now that we have our own UI. The agent code works with either |
| UI | **`adk web` for building and testing; our own ShelterWise UI for the final demo** (see section 8) |
| Location | Block centroid from our own data; Google Maps geocoding as fallback; 400 m radius |
| Models | Gemini Flash everywhere, Gemini Pro for `brief_writer` |
| Memory | **One intake per session.** No cross-session memory |
| Testing | **pytest** for the rules + **ADK eval set** for end-to-end |
| ADK detail | Code agents write state via `Event(actions=EventActions(state_delta=...))`, so it is copied back to the chat session (verified in ADK 1.18.0 and 2.14.1). ADK 2.x marks Sequential/Parallel/Loop agents deprecated in favor of `Workflow`, which can't yet be an `LlmAgent` sub-agent, so we keep the classic agents and pin `google-adk==2.14.1` |

## 7. Testing

**pytest** (`agent/tests/`): fast, no LLM
- all 9 `DECOY-SANF-*` excluded with the right reason, **with the radius turned off** (otherwise distance would hide them)
- the Fillmore case keeps SF-202665182
- filings for tract 06075016300 = 65/yr, not 260
- relief verdicts for: no case / block case only / own case number / income above and below AMI
- § 1942.4 "not yet" at 16 days, "applies" at 36 days

**ADK eval** (`agent/eval/`): about 5 full intakes, run with `adk eval`
- Fillmore heat case (above)
- a case where a decoy ranks #1 by raw similarity
- a block with no open records → fallback drafter
- a follow-up that adds a case number → Prop F flips to ELIGIBLE
- an intake that mentions race → the agent ignores it

## 8. Our UI

```
browser (ShelterWise UI) ──► small backend on Cloud Run ──► agent on Agent Runtime
       chat + brief card          holds the Google credentials        returns chat text + state.brief
```

- **Why a backend:** the browser can't hold Google Cloud credentials, so a thin backend on Cloud Run calls Agent Runtime with a service account.
- **The contract is `state.brief`.** The UI never parses chat text. It renders the `StabilizationBrief` JSON in `schemas.py`, so front end and agent work can proceed in parallel against a **mock `brief.json`** (the Fillmore sample in section 3).
- **Screens:** (1) intake box + chat, (2) brief card: evidence, excluded look-alikes, laws, funds with "still to confirm", limits, memo, (3) "Ask the tenant" follow-up buttons.
- **One intake = one session.** A "New intake" button starts a new session.
- **Starting point:** Sham's static mockup (`mockup/index.html`) already follows our steps. Each screen maps to a `state.*` key:

| Mockup screen | Agent state |
|---|---|
| Describe your situation → Review extracted facts | `state.intake` |
| Evidence search | `state.evidence` (kept + excluded) |
| Rights & resources | `state.statutes` + `state.relief` |
| Area context | `state.tract` |
| Evidence gaps / Human review checklist | brief limits + "still to confirm" items |

## 9. Data the agent uses

| Table | Real or modeled | Used for |
|---|---|---|
| `complaints_embedded` (embeddings; joined back to `municipal_311_housing_complaints` on `request_id`) | Real + 9 planted decoys | Vector search |
| `court_eviction_filings` | **Modeled** | Tract context |
| `acs_tract_housing_tenure` | Real (Census) | Tract context, equity audit |
| `rental_relief_program_bulletins` | Public policy text | Fund verdicts |
| `municipal_housing_ordinance_statutes` | Public statute text | Law matching |

## 10. Code layout

```
agent/shelterwise/
  agent.py         root_agent = navigator
  pipeline.py      the 6 steps (Sequential / Parallel / Loop)
  llm_agents.py    intake_parser, brief_writer, inspection_request_drafter
  code_agents.py   intake_prep, evidence, context, legal, relief, verifier
  tools/           evidence.py ★, relief.py, legal.py, tract.py, geocode.py, safety.py, pii.py, mcp.py, explain.py
  data.py          data access: BigQuery or local parquet (never selects audit_*)
  schemas.py       Pydantic models for every state.* key
  config.py        project, dataset, models, radius
  rules/           funds_sf.yaml, statutes_sf.yaml
sql/setup.sql      complaints_embedded + v_tract_stability_context
agent/tests/       pytest
agent/eval/        ADK eval set
ui/                ShelterWise UI + Cloud Run backend
scripts/equity_audit.py   offline only
```
