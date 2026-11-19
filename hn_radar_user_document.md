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
3. **Reach out** directly to the hiring lead with concrete solutions, pull requests, or architectural insights rather than a generic resume.

---

## 2. Prerequisites & Installation

### System Requirements
- **Python:** 3.13 or newer
- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- **Git:** Version 2.25+

### Optional Dependencies
- **GitHub Personal Access Token (`GITHUB_TOKEN`):** Raises GitHub API rate limits from 60 requests/hour to 5,000 requests/hour. Strongly recommended if fingerprinting accounts with many repositories.
- **Ollama:** Required for the `hnradar pulse` qualitative AI feature. Needs `qwen2.5:7b` (or another compatible model) running locally on port 11434.

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
           │                                │
           └──────────────┬─────────────────┘
                          ▼
                        match
                      (match.py)
                          │
                          ▼
            Top 3 Matches with Cited Reasons
```

### Safety & Resilience Invariants
- **Atomic Caching:** Every API response is cached in `data/cache/` using atomic writes (`tempfile` + `os.replace`), protecting against corruption during interrupted runs.
- **Terminal Sanitization (Rule 8):** Untrusted text from Hacker News comments or GitHub metadata is stripped of control characters (ANSI sequences, BEL, CR) and bidirectional formatting overrides before terminal printing.
- **Zero Hallucination (Rule 1):** Every match reason and sentiment pulse insight must cite an authentic comment ID or repository name.
- **Privacy First (Rule 5):** No LinkedIn scraping, no resume parsing, and no tracking of private repositories. Only public, aggregate GitHub stats are retained.

---

## 4. Comprehensive Command Reference

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

#### Example Usage:
```bash
# Ingest full monthly thread
uv run hnradar fetch-hiring

# Quick test fetching only the first 25 comments
uv run hnradar fetch-hiring --limit 25

# Output JSON directly to stdout for piping to jq
uv run hnradar fetch-hiring --limit 5 --json | jq '.[0]'
```

#### Sample Terminal Output:
```text
Fetching latest hiring story from HN...
Found: Ask HN: Who is hiring? (November 2026) (ID: 42109876)
Processing 482 comments...
Skipped 34 candidate profile comments.

Found 448 jobs (12 closed). Saved to data/jobs.json

| ID       | Company        | Role                   | Location         | Remote | Stack                  | Closed |
|----------|----------------|------------------------|------------------|--------|------------------------|--------|
| 42109912 | Acme Cloud     | Senior Backend Eng     | San Francisco    | Yes    | Python, Go, Kubernetes | No     |
| 42109945 | VectorLabs     | Machine Learning Eng   | New York / Remote| Yes    | Python, PyTorch, CUDA  | No     |
| 42110018 | FinScale       | Staff DevOps Architect | London, UK       | No     | AWS, Terraform, Docker | Yes    |
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

#### Sample Generated Profile (`data/profiles/octocat.json`):
```json
{
  "user": "octocat",
  "languages": [
    {"name": "Ruby", "bytes": 542100},
    {"name": "Python", "bytes": 312000},
    {"name": "JavaScript", "bytes": 184500}
  ],
  "topics": ["cli", "developer-tools", "api-wrapper", "docker"],
  "repos": [
    {
      "name": "Spoon-Knife",
      "description": "This repo is for spooning and knifing",
      "stars": 12850,
      "language": "Ruby"
    },
    {
      "name": "Hello-World",
      "description": "My first repository on GitHub!",
      "stars": 2410,
      "language": null
    }
  ],
  "scraped_at": "2026-11-19T06:00:00Z"
}
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

#### Sample Terminal Output:
```text
Loaded profile for octocat (3 languages, 4 topics, 2 notable repos)
Loaded 448 jobs from data/jobs.json

Top 3 Matches for @octocat:

1. Acme Cloud — Senior Backend Eng (Score: 65/100)
   Comment ID: 42109912 | Location: San Francisco (Remote: Yes)
   Reasons:
     • Language Match: Your profile features Python (matches job stack: Python, Go)
     • Topic Match: Your repo Spoon-Knife uses topic 'cli' (matches job stack)
     • Remote Bonus: +5 points (Position supports remote work)

2. DataStream Inc — Data Infrastructure Engineer (Score: 45/100)
   Comment ID: 42110540 | Location: Remote
   Reasons:
     • Language Match: Your profile features Python
     • Remote Bonus: +5 points (Position supports remote work)

3. DevTools Co — Developer Experience Engineer (Score: 35/100)
   Comment ID: 42111200 | Location: Remote
   Reasons:
     • Topic Match: Your repos use topic 'developer-tools'
     • Remote Bonus: +5 points
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
2. **Dual-Query Domain Expansion (PR #33):** When `--domain` is specified, runs an additional query targeting `restrictSearchableAttributes=url` to capture stories that might not contain the company name in the title.
3. **Domain Normalization & Security:** Strips protocols and `www.`, and rejects invalid hosts or backslashes to avoid domain confusion attacks.
4. **Ownership Invariant (Rule 9):** A matching domain confirms only that the story *links to* that domain; it does not assert that the company posted or owns the thread.

#### Example Usage:
```bash
uv run hnradar showhn "Supabase" --domain supabase.com
```

#### Sample Terminal Output:
```text
Show HN Results for 'Supabase' (Domain: supabase.com)
Total stories found: 14 (showing top 5)

| Story ID | Points | Comments | Domain Match | Title                                      | URL                          |
|----------|--------|----------|--------------|--------------------------------------------|------------------------------|
| 23345678 | 1280   | 342      | Yes          | Show HN: Supabase – An open source Firebase| https://supabase.com         |
| 25410982 | 412    | 98       | Yes          | Show HN: Supabase Storage                  | https://supabase.com/storage |
| 27819230 | 185    | 45       | No           | Show HN: Vector search with Postgres       | https://github.com/my-pg-app |
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
- **Length-Weighted Selection:** Sorts comments by length (longest first) to maximize signal, selects up to 60 comments, and truncates individual posts to 1,500 characters.
- **Pydantic Schema Validation (Rule 2):** Ollama is constrained to generate structured JSON conforming to `ModelReply`.
- **Automatic Retry:** If the LLM generates non-conforming JSON, HN Radar sends the validation error back to the model for a second attempt.
- **Strict Citation Check (Rule 1):** Verifies that every single comment ID cited by the LLM exists in the actual story discussion. Any hallucinated ID triggers a rejection.

#### Example Usage:
```bash
# Analyze feedback on a Show HN story
uv run hnradar pulse 23345678
```

#### Sample Terminal Output:
```text
Analyzing Show HN #23345678 with model 'qwen2.5:7b'...
Harvested 58 top-level comments (longest sorted).
Querying Ollama (temperature=0, num_predict=2048)...
Validated response conforming to Pydantic ModelReply schema.
Saved pulse data to data/pulse/23345678.json

=== Show HN Pulse: Supabase – An open source Firebase ===

[PROS]
• High praise for real-time Postgres subscriptions (Comment #23345890)
• Loved the seamless local Docker developer experience (Comment #23346112)

[BUGS & COMPLAINTS]
• Self-hosted setup documentation lacks clarity on JWT secrets (Comment #23346450)
• Memory consumption spikes during large table migrations (Comment #23347012)

[FEATURE ASKS]
• Support for fine-grained row-level security policy testing in CLI (Comment #23346890)
• Native integration with Cloudflare Workers (Comment #23347500)
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

Step 6: Craft the outreach!
```

### The Winning Outreach Email:
> **Subject:** Solution for container cold start latency (HN #38910401) + Backend Role
>
> Hi Jane,
>
> I saw your post on Hacker News hiring for the Senior Backend Engineer role (HN #42109912).
>
> While checking out Acme Cloud's Show HN announcement (HN #38910245), I noticed user feedback regarding 4+ second cold starts on Python 3.12 imports (HN #38910401). In my open-source project (`fastapi-accelerator`), I resolved this exact issue by pre-compiling bytecode in the base image and lazy-loading heavy SDKs, dropping initialization times by 65%.
>
> I put together a quick 10-line POC demonstrating how Acme Cloud could apply this: `github.com/alex-dev/acme-coldstart-fix`.
>
> I'd love to chat about joining the team and helping scale your backend infrastructure!
>
> Best,  
> Alex

---

## 6. The 10 AGENTS.md Factory Rules

Every line of code in HN Radar is strictly governed by the 10 invariant engineering rules documented in `AGENTS.md`:

1. **Every claim is cited:** Any pulse item or outreach reason stating what users said must carry the comment ID. Zero invented feedback.
2. **LLM output is schema-validated:** Parse model responses only through Pydantic models; never regex free text.
3. **Network goes through sources/:** All HTTP calls to Algolia, GitHub, and Ollama live in `src/hnradar/sources/` with disk caching.
4. **Untrusted URLs only in sandbox layer:** Never fetch arbitrary URLs taken from an HN post or profile outside the sandbox layer.
5. **Minimal personal data:** Store only public GitHub metadata; never scrape LinkedIn or store resumes.
6. **Limits fail loudly:** Pagination caps (2,000 repos) and loops must raise an error; never return a partial result disguised as complete.
7. **Every change ships edge-case tests:** Mandatory tests for empty input, at-the-limit, over-the-limit, upstream errors, and concurrent cache writers.
8. **Clean untrusted post text:** Strip Unicode control characters (`Cc`) and formatting overrides (`Cf`) before terminal printing.
9. **Domain match is never company ownership:** A domain match means a story links to that domain, never that the company owns it.
10. **Failed upstream request never complete:** Failed requests must raise an error and exit 1; never swallow failures into empty results.

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
**Solution:** GitHub limits unauthenticated requests to 60 per hour. Generate a personal access token at [github.com/settings/tokens](https://github.com/settings/tokens) (no special scopes needed) and export it:
```bash
export GITHUB_TOKEN="ghp_yourTokenHere"
```

### Q: `OllamaError: Failed to connect to Ollama at http://localhost:11434`
**Solution:** Ensure the Ollama daemon is running and the model is downloaded:
```bash
ollama serve &
ollama pull qwen2.5:7b
```

### Q: `match` reports: `Profile for <user> not found`
**Solution:** Run the fingerprint command first:
```bash
uv run hnradar fingerprint <user>
```

### Q: Why did `fetch-hiring` skip certain posts?
**Solution:** `fetch-hiring` excludes posts identified by `is_candidate_profile()` as job-seekers looking for employment, as well as comments marked deleted by Hacker News moderators.

---

## 9. Conclusion

HN Radar transforms Hacker News from an unstructured message board into a high-precision career engine. By anchoring every match to authentic code repositories, citing every user sentiment claim, and enforcing rigorous autonomous quality gates, HN Radar ensures that your outreach is always grounded in truth and technical substance.
