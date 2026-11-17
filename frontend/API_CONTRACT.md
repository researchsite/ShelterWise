# ShelterWise chat UI ↔ agent API contract (DRAFT, to confirm with the team)

The UI (`chat.html`) is one chat box plus a map. It sends the user's message and renders whatever
**blocks** come back. The agents decide *what* to show; the UI decides *how*.

Source of truth for the data: `hualin/agent/shelterwise_hualin` session state
(`state.case`, `state.safety`, `state.evidence`, `state.tract`, `state.statutes`, `state.relief`,
`state.brief`). Most blocks are a **direct copy of a state key**, so no new agent logic is needed.

---

## 1. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat` | Send one chat turn, get the full response (below). **Required.** |
| `POST` | `/api/chat/stream` | Same, as Server-Sent Events: `trace` events while agents run, then one `response` event. *Optional* (live agent-step list); the UI falls back to `/api/chat`. |
| `GET`  | `/api/session/{session_id}` | Re-open a case: returns the last response + current state. *Optional.* |
| `POST` | `/api/cases/{case_id}/checklist` | `{item_id, checked}` → save a reviewer-checklist tick (Firestore). *Stretch.* |

### Request
```json
POST /api/chat
{ "session_id": "SF-1042",      // omit on the first turn; server creates one and returns it
  "message": "Mother of 2 on the 1000 block of Fillmore St…",
  "user": "maria.r" }           // for case locking / audit trail
```

### Response envelope
```json
{
  "session_id": "SF-1042",
  "reply": "Safety first: there's an electrical hazard…",        // markdown, short (1–3 sentences)
  "agent_trace": [ { "agent": "habitability_vector_agent",        // ADK event.author
                     "label": "VECTOR_SEARCH top 25 → 1 kept, 3 excluded",
                     "ms": 2400, "parallel": true } ],
  "blocks": [ { "type": "safety", "...": "..." } ],               // rendered top → bottom
  "suggestions": [ "Why did you exclude DECOY-SANF-01?", "She has her own DBI case number" ]
}
```
- **`agent_trace`**: one item per ADK event/tool call (`event.author`, a short label, elapsed ms).
  Set `parallel: true` for the steps inside the ParallelAgent.
- **`suggestions`**: 2–4 follow-up prompts. Can be built in code from gaps (unknown facts, excluded IDs).
- **Unknown block `type`** → the UI shows it as a generic card. **Free-text agent output** → send a
  `markdown` block.

---

## 2. Recommended build: an adapter, not new agents

```
FastAPI /api/chat ─▶ ADK Runner (root_agent) ─▶ session.state
                                       │
                         state_to_blocks(state, turn)  ← pure Python, deterministic
                                       │
                            { reply, agent_trace, blocks, suggestions }
```
`state_to_blocks` decides which blocks to send based on what changed this turn
(e.g. `state.brief` changed → send the full case blocks; `explain_exclusion` was called → send `explain`).
The LLM never writes the JSON blocks, so they can't be hallucinated.

---

## 3. Block catalog

`✅ exists` = field already in agent state today · `➕ add` = small addition needed · `🆕 new` = feature not in the agent yet.

| `type` | When | Source in agent | Status |
|---|---|---|---|
| `safety` | Hazard detected | `state.safety.alerts[]` | ✅ |
| `summary` | New / updated intake | `state.case` | ✅ (+ hearing time ➕) |
| `evidence` | After triage | `state.evidence` (`kept`, `excluded`) | ✅ (+ lat/lng ➕) |
| `law` | After triage | `state.statutes[]` | ✅ |
| `relief` | After triage / fact update | `state.relief[]` | ✅ |
| `tract` | After triage | `state.tract` | ✅ (+ metro distribution ➕) |
| `next_steps` | After triage | `state.brief.next_steps`, `to_confirm`, `questions_for_tenant` | ✅ |
| `brief` / `brief_cta` | After triage / "draft the brief" | `state.brief` (`summary`, `memo_markdown`, `verification`) | ✅ |
| `explain` | "Why exclude X?" | `explain_exclusion()` tool result | ✅ |
| `diff` | A fact changed | compare previous vs new `state.case` / `state.relief` | ➕ adapter only |
| `draft_311` | No open record nearby | `inspection_request_drafter` | ➕ needs structured output (today: free text) |
| `relief_fallback` | No open record nearby | `state.relief` filtered to no-case funds | ✅ |
| `equity_audit` | Metro equity question | `equity_audit_agent` | 🆕 (Member 4 tool) |
| `transit` | Courthouse question | `estimate_courthouse_transit` | 🆕 (Member 4 tool) |
| `lock` | "Lock for Attorney Chen" | `claim_or_update_case_task` (Firestore) | 🆕 (Member 4 tool) |
| `markdown` | Any other free-text answer | agent text | ✅ |

### Field details

**`safety`**: `{ "alerts": [ { "id": "water_near_electrical", "message": "Do NOT touch…" } ] }`

**`summary`**: from `state.case`
```json
{ "case_id": "SF-1042", "block": "1000 Block Fillmore St", "census_tract_geoid": "06075016300",
  "hearing_date": "2026-11-23", "hearing_time": "09:00", "hours_to_hearing": 89, "case_type": "nonpayment",
  "facts": [ { "key": "hazards", "label": "No heat ~2 wks, ~50°F", "status": "reported" },
             { "key": "tenant_has_own_dbi_case", "label": "Own DBI case #", "status": "unknown" } ],
  "pii_scrubbed_count": 3 }
```
`status` ∈ `reported | inferred | unknown | edited`. Facts = the `IntakeFacts` fields (null → `unknown`).
➕ **add `hearing_time` and `hours_to_hearing`** (today only `hearing_date` + `days_to_hearing`).

**`evidence`**: `state.evidence` as is (`EvidenceResult`). Each `EvidenceHit` ➕ **add
`latitude`, `longitude`** (needed for map pins; they're already read in `exclusion_reasons`).
UI labels for `reasons`: `not_residential` → "Commercial property", `closed_abated` → "Closed: Abated",
`closed_no_violation` → "Closed: No Violation", `closed_other` → "Closed", `outside_radius` → "Too far".

**`law`**: `state.statutes[]` (`StatuteFinding`). Badge mapping:
`APPLIES` → ✓ green "Likely applies" · `APPLIES_IF` → ◐ amber "Applies if…" ·
`NOT_YET` → ⏳ grey "Not yet" (+ `recheck_on`) · `NOT_APPLICABLE` → grey "Doesn't apply".
Optional ➕ `clock: { "elapsed_days": 16, "required_days": 35 }` for the progress bar.

**`relief`**: `state.relief[]` (`ReliefVerdict`). Badge: `ELIGIBLE` ✓ green · `CONDITIONAL` ◐ amber ·
`INELIGIBLE` grey. `urgent: true` → ⏱ "call today". The "Answer to unlock more" buttons come from
`checks[]` where `status = "unknown"` → send as `suggestions` / `ask: ["She has her own DBI case number"]`.

**`tract`**: `state.tract` as is. ➕ **add `metro_distribution`** for the dot charts:
`{ "severe_rent_burden_pct": [41 numbers], "annual_filings_modeled": [41 numbers] }` + the medians.
Never include `audit_*` fields.

**`brief`**: `state.brief` as is. UI shows `summary`, the 9 sections, `memo_markdown`, and the 6-item
checklist; `verification.passed = false` → show the "failed automatic checks" warning.

**`explain`**: `explain_exclusion()` result as is (`status`, `semantic_rank_before_rules`, `reasons`, `record`).

**`draft_311`** ➕: give `inspection_request_drafter` an `output_schema`:
`{ category, location_block, description, started, landlord_notified, photo_checklist[], interim_funds[] }`.
Until then, send its text as a `markdown` block.

**`equity_audit`** 🆕: aggregate only, never linked to the case:
`{ "cohorts": [ { "name": "SF metro", "tracts": 42, "no_vehicle_pct": 42.1 }, … ], "reading": "…",
"silent_distress_geoids": ["06075…"] }`.

**`transit`** 🆕: `{ "from_block", "to": "400 McAllister St", "distance_km", "duration_min", "leave_by": "08:00", "source": "google_directions|estimate" }`

**`lock`** 🆕: `{ "case_id", "assigned_attorney", "status_from", "status_to", "lock_version_from", "lock_version_to" }`;
on a version conflict return `{ "conflict": true, "server_version": 5 }`.

---

## 4. `geo` field (map): GeoJSON on any block

Any block may add `geo`, a GeoJSON `FeatureCollection`. The map draws the features from the latest
reply that has any. Feature `properties`:

| `role` | Geometry | Built from |
|---|---|---|
| `tenant_block` | Point | `state.case.lat/lng` (100-block centroid; **never the exact address**) |
| `corroborating` / `excluded` | Point | each `EvidenceHit` `longitude, latitude` + `request_id`, `reasons`, `meters_away` |
| `tract_focus` | Polygon | `ST_ASGEOJSON(tract_geom)` for `case.census_tract_geoid` |
| `silent_distress` | Polygon | the equity audit's tract geoids (equity block only) |
| `courthouse` / `route` | Point / LineString | transit tool |
| `search_radius` | Point + `radius_m` | `state.evidence.radius_m` around the tenant block |

`properties.ref` = the card id (`request_id` or `geoid`) so hovering a card highlights its pin.
Until the backend sends `geo`, the UI can build it from the block fields plus its bundled `geo_sf.js`.

---

## 5. Who does what (proposal)

| Piece | Owner |
|---|---|
| `/api/chat` FastAPI + ADK Runner + `state_to_blocks` adapter | Member 4 (platform) with Hualin |
| `➕` fields: `latitude/longitude` on hits, `hearing_time/hours_to_hearing`, `metro_distribution`, drafter `output_schema` | Shiva / agent owner |
| `🆕` tools: equity audit, transit, Firestore lock | Member 4 |
| UI renderers read these fields (today they show sample text); SSE trace | Hualin |
| Confirm field names in `schemas.py` | Team |
