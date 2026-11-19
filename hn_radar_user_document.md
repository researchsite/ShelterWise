# HN Radar — Comprehensive User Guide & Operator Manual

> **Project:** HN Radar  
> **Repository:** [researchsite/hn-radar](https://github.com/researchsite/hn-radar)  
> **Philosophy:** *"Arrive with the fix: HN Who-is-Hiring → cited warm intros"*

---

## 1. Introduction & Guiding Philosophy

**HN Radar** is an intelligent developer intelligence tool designed to bridge the gap between job listings on Hacker News and meaningful developer outreach.

### Why "Arrive with the Fix"?
Traditional job applications are transactional and low-signal. A standard resume submitted to a generic email rarely cuts through the noise. On Hacker News, engineering founders and hiring managers frequently post their open positions in the monthly *"Ask HN: Who is hiring?"* threads, and they often showcase their products on *"Show HN"*.

HN Radar equips developers to:
1. **Discover** the exact roles that align with their authentic coding footprint.
2. **Understand** what real users are saying about the company's product (what they love, what bugs they encounter, and what features they are asking for).
3. **Draft** a concrete, 5-line outreach note via `hnradar draft` citing authentic user bug reports from Hacker News, connecting them directly to your open-source projects—with zero hallucination and strict ownership respect.

---

## 2. Prerequisites & Installation

### System Requirements
- **Python:** 3.13 or newer
- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- **Git:** Version 2.25+

### Optional Dependencies
- **GitHub Personal Access Token (`GITHUB_TOKEN`):** Raises GitHub API rate limits from 60 requests/hour to 5,000 requests/hour. Strongly recommended if fingerprinting accounts with many repositories.
- **Ollama:** Required for `hnradar pulse` (qualitative sentiment extraction) and `hnradar draft` (outreach synthesis). Needs `qwen2.5:7b` (or another compatible model) running locally on port 11434.

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/researchsite/hn-radar.git
cd hn-radar

# 2. Install dependencies using uv (creates an isolated virtual environment)
uv sync

# 3. Verify the CLI is working
uv run hnradar --help
```

If you prefer using standard `pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
hnradar --help
```

---

## 3. Core Architecture & Data Lifecycle

HN Radar operates as a pipeline of modular, isolated subsystems:

```
[ Hacker News Algolia API ]       [ GitHub Public API ]       [ Local Ollama Server ]
           │                                │                            │
           ▼                                ▼                            ▼
  sources/hn.py (Cache)           sources/github.py (Cache)     sources/ollama.py (JSON Schema)
           │                                │                            │
           ▼                                ▼                            ▼
     fetch-hiring                      fingerprint                     pulse
 (parse.py & closed.py)              (fingerprint.py)             (pulse/cluster.py)
           │                                │                            │
           ▼                                ▼                            ▼
    data/jobs.json               data/profiles/<user>.json      data/pulse/<story_id>.json
           │                                │                            │
           └──────────────┬─────────────────┘                            │
                          ▼                                              ▼
                        match ──────────────────────────────────────►  draft
                      (match.py)                                   (draft/write.py)
                          │                                              │
                          ▼                                              ▼
            Top Matches with Cited Reasons                    5-Line Cited Outreach Note
```

### Safety & Resilience Invariants
- **Atomic Caching & Resilience (PR #53):** Responses are cached in `data/cache/` using atomic writes. If writing the cache fails (e.g. read-only filesystem or permission denial), the fetch does not crash—it returns the data safely and emits a single warning to stderr.
- **Terminal Sanitization (Rule 8):** Untrusted text from Hacker News comments or GitHub metadata is stripped of control characters (ANSI sequences, BEL, CR) and bidirectional formatting overrides before terminal printing.
- **Zero Hallucination (Rule 1):** Every match reason, sentiment pulse insight, and draft outreach line must cite an authentic comment ID or repository name.
- **Platform Host Safety (Rule 9 & PR #50):** Links to multi-tenant platform domains (github.com, notion.so, substack.com) are flagged as low confidence because stories linking to shared hosts often belong to third parties.
- **Privacy First (Rule 5):** No LinkedIn scraping, no resume parsing, and no tracking of private repositories. Only public, aggregate GitHub stats are retained.

---

## 4. Comprehensive Command Reference

HN Radar provides **6 core CLI commands**:

| Command | Purpose | Key PR Features |
| :--- | :--- | :--- |
| `hnradar fetch-hiring` | Ingests monthly hiring thread | Candidate filtering (#46), Closed job detection (#30), Cache resilience (#53) |
| `hnradar fingerprint` | Profiles developer GitHub repos | Fork exclusion (#6), Top languages & topics, 2000-repo limit (#6) |
| `hnradar match` | Deterministic job scoring | Alias normalizer, 20/10/5 point rules, cited reasons (#24, #29) |
| `hnradar showhn` | Company product context | URL-restricted search (#33), Platform domain risk flagging (#50) |
| `hnradar pulse` | AI sentiment clustering | Length-sorted comments, Pydantic schema validation (#49) |
| `hnradar draft` | **Writes cited outreach note** | **Top 10 evaluation, 5-line strict note, cited bugs & repos (#51)** |

---

### 4.1. `hnradar fetch-hiring`

Fetches and parses the latest monthly *"Ask HN: Who is hiring?"* thread.

```bash
uv run hnradar fetch-hiring [OPTIONS]
```

#### Options:
- `--limit INTEGER`: Maximum number of comments to process (useful for quick smoke tests).
- `--out PATH`: Custom JSON output file path (defaults to `data/jobs.json`).
- `--json`: Emits clean, machine-readable JSON directly to standard output.

#### Key Behaviors:
1. Automatically identifies the latest official thread posted by user `whoishiring`.
2. Uses robust heuristic parsing (`parse.py`) to extract company, role title, location, remote policy, tech stack, and external career URLs.
3. **Candidate Filtering (PR #46):** Automatically classifies and discards job-seeker pitches (*"Who wants to be hired?"*), reporting the number of skipped candidate profiles.
4. **Closed Position Detection (PR #30):** Traverses replies posted by the author to detect if the position has been filled (*"Applications are closed"*), recording the closing comment ID.
5. **Resilient Cache Writes (PR #53):** If saving to disk fails (e.g. read-only filesystem), warns once to stderr and safely returns the fetched data.

#### Example Usage:
```bash
# Ingest full monthly thread
uv run hnradar fetch-hiring

# Quick test fetching only the first 25 comments
uv run hnradar fetch-hiring --limit 25

# Output JSON directly to stdout for piping to jq
uv run hnradar fetch-hiring --limit 5 --json | jq '.[0]'
```

---

### 4.2. `hnradar fingerprint`

Constructs a structured developer profile by analyzing a user's public GitHub repositories.

```bash
uv run hnradar fingerprint USERNAME [OPTIONS]
```

#### Arguments & Options:
- `USERNAME`: The GitHub username to analyze (required).
- `--out-dir PATH`: Directory where the profile JSON will be saved (defaults to `data/profiles/`).

#### Key Behaviors:
1. Paginates through all public repositories owned by the user.
2. **Strict Fork Exclusion:** Automatically discards forked repositories so that only authored code contributes to metrics.
3. Computes the **top 5 programming languages** weighted by byte count.
4. Computes the **top 10 repository topics**.
5. Selects the **top 5 notable repositories** ranked by GitHub star count.
6. **Loud Failure Boundary (Rule 6):** If the account contains more than 2,000 public repositories, the command raises an explicit error rather than silently truncating data.

#### Example Usage:
```bash
uv run hnradar fingerprint octocat
```

---

### 4.3. `hnradar match`

Deterministically matches a developer's profile against current job openings.

```bash
uv run hnradar match USERNAME [OPTIONS]
```

#### Arguments & Options:
- `USERNAME`: GitHub username whose profile was generated via `fingerprint` (required).
- `--jobs PATH`: Path to jobs file (defaults to `data/jobs.json`).
- `--profiles-dir PATH`: Directory containing profiles (defaults to `data/profiles/`).
- `--json`: Output matches in structured JSON format.

#### Deterministic Scoring Model:
- **Language Overlap:** +20 points per matching language.
- **Topic Overlap:** +10 points per matching topic.
- **Remote Work Bonus:** +5 points (awarded only if there is already a tech stack match).
- **Cap:** Maximum score is 100 points.
- **Tie-Breaking:** Higher comment ID wins (fresher postings prioritized).
- **Evidence Requirement (Rule 1):** Every match must cite the exact language, repo, or topic that justified the score.

#### Example Usage:
```bash
uv run hnradar match octocat
```

---

### 4.4. `hnradar showhn`

Finds Show HN stories for a company to provide outreach context and product background.

```bash
uv run hnradar showhn COMPANY [OPTIONS]
```

#### Arguments & Options:
- `COMPANY`: Name of the company or product (required).
- `--domain DOMAIN`: Domain name to restrict/prioritize (e.g. `acmecloud.com`).
- `--json`: Outputs raw candidate stories in JSON format.

#### Key Behaviors:
1. Executes an Algolia search restricted to `tags=show_hn`.
2. **Dual-Query Domain Expansion (PR #33):** When `--domain` is specified, runs an additional query targeting `restrictSearchableAttributes=url`.
3. **Platform Domain Risk Flagging (PR #50):** If the domain is a shared or platform host (e.g. `github.com`, `notion.so`, `substack.com`), flags `platform_domain=True` and `low_confidence=True`, printing a warning that stories linking to shared hosts may belong to someone else.
4. **Ownership Invariant (Rule 9):** A matching domain confirms only that the story *links to* that domain; it never asserts company ownership.

#### Example Usage:
```bash
uv run hnradar showhn "Supabase" --domain supabase.com
```

---

### 4.5. `hnradar pulse`

Leverages a local LLM via Ollama to synthesize Show HN discussion into **pros, bugs, and asks**, citing exact comment IDs.

```bash
uv run hnradar pulse STORY_ID [OPTIONS]
```

#### Arguments & Options:
- `STORY_ID`: The Hacker News item ID of the Show HN story (required).
- `--model MODEL`: Ollama model tag (defaults to `qwen2.5:7b`).
- `--out PATH`: Destination file (defaults to `data/pulse/<story_id>.json`).

#### Safety & Schema Guarantees:
- **Length-Weighted Selection:** Sorts comments by length (longest first), selects up to 60 comments, and truncates posts to 1,500 characters.
- **Pydantic Schema Validation (Rule 2):** Constrained to generate structured JSON conforming to `ModelReply`.
- **Strict Citation Check (Rule 1):** Verifies that every single comment ID cited by the LLM exists in the actual story discussion.

#### Example Usage:
```bash
uv run hnradar pulse 23345678
```

---

### 4.6. `hnradar draft` (NEW — PR #51)

Writes an exact 5-line cited outreach note to the best-matched company, referencing a real user-reported bug and your matching open-source repository.

```bash
uv run hnradar draft USERNAME [OPTIONS]
```

#### Arguments & Options:
- `USERNAME`: GitHub username whose profile was generated via `fingerprint` (required).
- `--model MODEL`: Ollama model tag for drafting (defaults to `qwen2.5:7b`).
- `--jobs PATH`: Path to jobs file (defaults to `data/jobs.json`).
- `--profiles-dir PATH`: Directory holding `<user>.json` (defaults to `data/profiles`).
- `--pulse-dir PATH`: Directory holding saved pulses (defaults to `data/pulse`).

#### The Triple Qualification Gate:
`draft` iterates through your **top 10 matches** in descending score order. A match is used only when:
1. **Verified Domain:** Its job link contains an identifiable, non-platform domain (PR #50).
2. **Domain-Linked Show HN:** A Show HN story exists that links directly to that domain (PR #33 / PR #35).
3. **Authentic Bug Report:** The Show HN discussion has a verified `bug` with genuine comment IDs (uses a saved pulse if available, otherwise executes `pulse` on the fly).

#### The 5-Line Contract:
The local model is strictly constrained by Pydantic (`ModelDraft`) to produce exactly 5 lines:
- **Line 1:** Greeting and developer introduction (1 sentence).
- **Line 2:** Problem statement stating what users reported, starting with *"A Show HN that links to &lt;domain&gt;"* and citing exact comment IDs.
- **Line 3:** Explanation of how your matched repository addresses the issue (naming the repo).
- **Line 4:** First action you would take (1 sentence).
- **Line 5:** Polite invitation for a conversation.
- **Rule 9 Guard:** Any phrase implying company ownership (*"your Show HN"*, *"you launched"*) is rejected and retried.

#### Evidence Printing:
`draft` prints the note and displays line-by-line comment citations, repository descriptions, and direct Hacker News URLs. **Nothing is ever sent automatically.**

#### Example Usage:
```bash
uv run hnradar draft octocat
```

#### Sample Terminal Output:
```text
Draft for Acme Cloud (qwen2.5:7b), using your repo spoon-knife:

Hi Acme Cloud team, I'm Alex, a backend engineer specializing in high-throughput APIs.
A Show HN that links to acmecloud.com had users reporting connection pool exhaustion during traffic surges.
My repository spoon-knife implements an adaptive semaphore pool that mitigates this exact failure mode.
I'd start by profiling your async connection lifecycles under simulated peak load.
Would you be open to a 15-minute chat next week to discuss your backend infrastructure?

Evidence (read it before you send anything; nothing is sent):
line 2 cites comment 42109812, 42109940
repo spoon-knife | Python | Adaptive connection pooling library for async HTTP services
comment 42109812 | Users seeing 502 bad gateway when concurrent requests exceed 500 connections | https://news.ycombinator.com/item?id=42109812
comment 42109940 | Connection pool leaks sockets on client disconnects | https://news.ycombinator.com/item?id=42109940
Show HN: https://news.ycombinator.com/item?id=38910245 (links to acmecloud.com)
```

---

## 5. End-to-End Practical Walkthrough: "From Zero to Warm Intro"

Here is a complete scenario showing how a developer uses HN Radar to secure an interview.

```text
Step 1: Ingest monthly hiring posts
$ uv run hnradar fetch-hiring
✔ 448 jobs indexed into data/jobs.json

Step 2: Profile your developer footprint
$ uv run hnradar fingerprint alex-dev
✔ Profile saved to data/profiles/alex-dev.json (Top stack: Python, FastAPI, Docker)

Step 3: Discover top matches
$ uv run hnradar match alex-dev
✔ Top Match: Acme Cloud (Comment ID: 42109912, Score: 70/100)
  Hiring lead: jane@acmecloud.com
  Stack: Python, FastAPI, Kubernetes

Step 4: Research their Show HN history
$ uv run hnradar showhn "Acme Cloud" --domain acmecloud.com
✔ Found Show HN Story #38910245: "Show HN: Acme Cloud – Serverless Python Sandboxes"

Step 5: Run sentiment pulse to discover pain points
$ uv run hnradar pulse 38910245
✔ Highlighted Bug in Comment #38910401:
  "Cold start latency on Python 3.12 containers takes over 4 seconds due to package imports."

Step 6: Generate your cited outreach note!
$ uv run hnradar draft alex-dev
✔ Evaluates Top 10 matches -> Validates Acme Cloud -> Generates 5-line outreach note
  cites Comment #38910401 and developer repo 'fastapi-accelerator'.
```

---

## 6. The 10 AGENTS.md Factory Rules

Every line of code in HN Radar is strictly governed by the 10 invariant engineering rules documented in `AGENTS.md`:

1. **Every claim is cited:** Any pulse item, match reason, or draft line stating what users said must carry the comment ID.
2. **LLM output is schema-validated:** Parse model responses only through Pydantic models; never regex free text.
3. **Network goes through sources/:** All HTTP calls live in `src/hnradar/sources/` with disk caching.
4. **Untrusted URLs only in sandbox layer:** Never fetch arbitrary URLs outside sandbox.
5. **Minimal personal data:** Store only public GitHub metadata; never scrape resumes.
6. **Limits fail loudly:** Pagination caps (2,000 repos) and loops must raise an error; never return partial results.
7. **Every change ships edge-case tests:** Mandatory tests for empty, at-limit, over-limit, and upstream errors.
8. **Clean untrusted post text:** Strip Unicode control characters (`Cc`) and formatting overrides (`Cf`) before terminal printing.
9. **Domain match is never company ownership:** A domain match means a story links to that domain, never that the company owns it. Platform domains are flagged.
10. **Failed upstream request never complete:** Failed requests must raise an error and exit 1; never swallow failures.

---

## 7. Autonomous Engineering & Verification

HN Radar is built using an autonomous engineering factory:

- **PowerShell Mutex Poller (`scripts/agent-poll.ps1`):** Uses an OS named mutex (`Global\HNRadarAgentPoll`) to guarantee single-instance execution when monitoring GitHub issues labeled `ready-for-agent`.
- **Goose Worker Recipe (`.goose/recipes/ticket-worker.yaml`):** Implements code modifications in dedicated git worktrees (`../hn-radar-worktrees/`), enforces minimal diffs, runs test suites, and opens pull requests.
- **Real-Data Verification Skill (`.claude/skills/verify-jobs-parse/`):** When modifying the job parser, runs a verification test against the live Hacker News thread into a scratch file, confirming that `must-keep` IDs are retained and `must-exclude` candidate pitches are dropped.
- **Qodo Code Review Bot & Quality Gate:** Automatically reviews every PR, generates Mermaid architecture diagrams, and classifies findings into High, Medium, and Low. Under the repository's Definition of Done, all High and Medium findings must be resolved with regression tests.

---

## 8. Troubleshooting & Frequently Asked Questions

### Q: `GitHubError: Rate limit exceeded`
**Solution:** GitHub limits unauthenticated requests to 60 per hour. Export a token:
```bash
export GITHUB_TOKEN="ghp_yourTokenHere"
```

### Q: `OllamaError: Failed to connect to Ollama at http://localhost:11434`
**Solution:** Ensure the Ollama daemon is running and the model is downloaded:
```bash
ollama serve &
ollama pull qwen2.5:7b
```

### Q: `draft` reports: `No cited problem found for <user>`
**Solution:** `draft` checks your top 10 matches. If none of the top 10 companies have a non-platform domain with a domain-linked Show HN containing a cited bug, it prints the specific skip reasons for each company. You can inspect other matches or run `showhn` and `pulse` manually.

### Q: Why did `showhn` print a platform domain warning?
**Solution:** The requested domain is on a shared host (e.g., `github.io`, `notion.so`). Anyone can host pages on shared domains, so HN Radar flags it as low confidence (Rule 9).

---

## 9. Conclusion

HN Radar transforms Hacker News from an unstructured message board into a high-precision career engine. By anchoring every match to authentic code repositories, citing every user sentiment claim, and enforcing rigorous autonomous quality gates, HN Radar ensures that your outreach is always grounded in truth and technical substance.
