# ShelterWise UI prototypes

Open `chat.html` in a browser. It is the single main UI. (Earlier 6-screen proposals were removed; see git history before this commit.)
Everything runs on a **mock backend** with sample data; no server is needed.

## 📌 Note: proposed backend contract (DRAFT, to confirm with the team)

```
POST /api/chat  { session_id, message }
→ { reply, agent_trace:[{agent,label,ms}], blocks:[{type, ...data}], suggestions:[...] }
```

The UI just draws whatever blocks arrive, so the agents decide what the user sees.

Block types used by the mock: `safety`, `summary`, `evidence`, `law`, `relief`, `tract`,
`next_steps`, `brief_cta`, `brief`, `explain`, `equity_audit`, `draft_311`,
`relief_fallback`, `transit`, `lock`, `diff`.

**Open question for the team:** confirm field names in `schemas.py` (Shiva) and the
endpoint in `server.py` (Member 4). Each chat reply's "{ } response JSON" toggle shows
the exact shape the mock returns.

## Test prompts (run in order in `chat.html`)

Tip: in `chat.html`, click **🧪 Test prompts** (top right) to Run, Copy or "Put in box" each prompt with one click.

| # | Prompt | Expected result |
|---|---|---|
| 1 | Mother of 2 on the 1000 block of Fillmore St. Radiators stone cold for 2 weeks, about 50 degrees inside, kid keeps getting sick. Now water is dripping near the kitchen fuse box. Behind about two months on rent. Nonpayment hearing Monday 9am. What do we have? | 6-step agent trace (3 parallel steps) · red safety alert · facts · 1 corroborating 311 + 3 excluded look-alikes · 3 statutes · 4 funds (Conditional) · tract charts · next steps · brief card |
| 2 | Why did you exclude the boiler shutdown complaint? | `evidence_explainer_agent`: DECOY-SANF-01, rank #1, Commercial |
| 3 | Why did you exclude DECOY-SANF-04 (the abated one)? | DECOY-SANF-04, Closed: Abated |
| 4 | Why did you exclude DECOY-SANF-07? | DECOY-SANF-07, Closed: No Violation |
| 5 | She has her own DBI case number | Prop F + DBI Bridge become **Eligible** · "What changed" diff |
| 6 | Household of 3, about $45k a year | SF ERAP becomes **Eligible**; MEDA stays Conditional |
| 7 | Can she reach the courthouse by bus before 9am Monday? | Transit card → 400 McAllister St, leave by 8:00am |
| 8 | Draft the attorney brief | 9-section brief (v2 after 5–6) + 6-item checklist; ticking all 6 shows a toast |
| 9 | Who lives in the tracts our triage rules prioritize, and where might 311 under-reporting blind us? | Fenced `equity_audit_agent` card (aggregate only) |
| 10 | Lock this case for Attorney Chen | Firestore lock card, lock_version 4 → 5 |
| 11 | Tenant is Black, can that raise priority? | Guardrail refusal: protected traits not used |
| 12 | Tenant on 2400 block Mission St, mold and leak, no 311 filed yet, owner move-in notice. What can we do? | `hazard_311_drafter_agent`: 311 draft + funds that don't need a case |
| 13 | How severe is eviction filing pressure in tract 06075016300 compared with the rest of SF? | Tract charts only |
| 14 | Correction: household is 4 people | Fact updated · Brief v2 diff (same as clicking ✎ on a fact) |
| 15 | hello | Clarifying question (fallback) |

Also click: the **Why?** buttons on the excluded cards, the "Answer to unlock more" buttons on the relief card,
the suggestion buttons under each reply, and **view trace** / **{ } response JSON**.

**Note:** the mock routes by keyword. Run prompt 1 first, and refresh the page to reset the fund state.

## Color system

Themes (switch in the top bar, saved in the browser): **Courthouse** (default: navy + brass on warm paper,
serif headings), **Civic** (teal + terracotta), **Original** (first prototype). Themes change surfaces and
brand colors only. **Status colors never change**, so they always mean the same thing, and every one is
paired with an icon and a text label (never color alone):

| Token | Meaning | Used for |
|---|---|---|
| `--crit` ⚡ | Life-safety only | Wet panel / gas / fire banner (the only solid-red surface) |
| `--urg` ⏱ | Deadline / act today | Hearing countdown, "call today" |
| `--warn` ◐ | Conditional / needs review | Fund "Conditional", attorney review, DRAFT, review notices |
| `--ok` ✓ | Eligible / corroborated | Kept 311 record, eligible funds, "likely applies" |
| `--info` ℹ | Neutral record / fact | Record status, tenant-reported facts |
| `--grey` 🔒 | Locked / excluded / unknown / not yet | Decoys, gated funds, unknown facts, §1942.4 "not yet" |
| `--audit` 🛡 | Isolated equity audit | Aggregate-only metro audit card |
