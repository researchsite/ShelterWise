# HN Radar — End-to-End System Architecture Specification

> **Document Type:** System Architecture & Technical Design Document  
> **Source Repository:** [researchsite/hn-radar](https://github.com/researchsite/hn-radar)  
> **Synthesis Scope:** Complete integration across all 26 closed Pull Requests (#1 through #53) and Qodo Bot Review Diagrams.

---

## 1. Executive Summary & Core Mission

**HN Radar** is an autonomous intelligence and matchmaking engine designed around a single guiding principle: **"Arrive with the fix."**

Instead of sending generic job applications or cold outreach messages, HN Radar connects developers to high-signal opportunities on Hacker News by:
1. Ingesting monthly *"Ask HN: Who is hiring?"* threads, parsing job postings, discarding candidate self-pitches, and verifying active status against poster replies.
2. Generating a privacy-respecting **Developer Fingerprint** from public GitHub repositories (languages, topics, notable repos).
3. Deterministically **scoring and matching** jobs against the developer profile with transparent, cited evidence (Rule 1).
4. Discovering relevant **Show HN** product posts for target companies with domain-restricted search, strict ownership semantics (Rule 9), and platform domain risk filtering (PR #50).
5. Extracting actionable sentiment—**pros, bugs, and asks**—from Show HN comments using a local LLM (Ollama), requiring comment-ID citations for every claim.
6. Generating an exact **5-line cited outreach note** via `hnradar draft` (PR #51) that pairs an authentic user-reported bug with the developer's specific open-source repository.
7. Providing **resilient on-disk caching** (PR #53) where read-only or permission-denied cache paths warn safely to stderr and never abort successful data fetches.
8. Governing all human and AI code changes through a rigid **Autonomous Software Engineering Factory** (Goose recipes, mutex-protected pollers, real-data verification skills, and Qodo automated code reviews enforcing the 10 rules of `AGENTS.md`).

---

## 2. High-Level Unified System Architecture

The following diagram unifies the entire HN Radar ecosystem, mapping external APIs, source adapters, storage layers, processing pipelines, user CLI commands, security boundaries, and the autonomous agent factory.

```mermaid
graph TB
  %% External Services
  subgraph ExternalServices["External Services & APIs"]
    AlgoliaAPI["Hacker News Algolia REST API<br/>(hn.algolia.com/api/v1)"]
    GitHubAPI["GitHub Public REST API<br/>(api.github.com/users/repos)"]
    LocalOllama["Local / Remote Ollama Server<br/>(localhost:11434 / qwen2.5:7b)"]
  end

  %% Network & Caching Adapters
  subgraph SourceLayer["Source Adapters & Disk Cache (src/hnradar/sources/)"]
    HNSource["sources/hn.py<br/>• find_latest_hiring_story()<br/>• search_show_hn()<br/>• fetch_item()<br/>• Resilient cache write (PR #53)"]
    GHSource["sources/github.py<br/>• fetch_repos()<br/>• Rate limit check<br/>• Hard limit: 2000 repos"]
    OllamaSource["sources/ollama.py<br/>• OllamaClient.complete()<br/>• format: schema<br/>• num_predict: 2048"]
    
    HNCache[("data/cache/hn_*.json<br/>Atomic tempfile+rename<br/>Warns on failure (PR #53)")]
    GHCache[("data/cache/github_*.json<br/>TTL: 1 hour")]
  end

  AlgoliaAPI <-->|HTTP GET| HNSource
  GitHubAPI <-->|"HTTP GET (Bearer Token)"| GHSource
  LocalOllama <-->|HTTP POST /api/chat| OllamaSource
  HNSource <-->|Read / Atomic Write| HNCache
  GHSource <-->|Read / Atomic Write| GHCache

  %% Ingestion & Parsing Subsystem
  subgraph IngestionSubsystem["Ingestion & Data Normalization"]
    ParseComment["parse_comment()<br/>• Pipe header extraction<br/>• Tech stack regex (_STACK, _GO_RE)<br/>• Remote status & URL extraction"]
    CandidateFilter["is_candidate_profile()<br/>• Drops job-seeker pitches<br/>• First-person / Resume heuristics"]
    ClosedDetector["closing_reply_id()<br/>• Scans poster replies<br/>• Natural language clause parser<br/>• Bisect condition checking"]
    JobsJSON[("data/jobs.json<br/>Validated Job Records")]
  end

  HNSource -->|Raw Comment HTML| ParseComment
  ParseComment -->|Parsed Candidate| CandidateFilter
  CandidateFilter -->|Not Candidate| ClosedDetector
  ClosedDetector -->|Enriched with closed_id| JobsJSON

  %% User Fingerprinting Subsystem
  subgraph FingerprintSubsystem["Developer Profiling"]
    ProfileBuilder["build_profile()<br/>• Filters out all forks<br/>• Top 5 languages by byte size<br/>• Top 10 repository topics<br/>• Top 5 notable repos by stars"]
    ProfileJSON[("data/profiles/{user}.json<br/>Pydantic Profile")]
  end

  GHSource -->|Own Repositories| ProfileBuilder
  ProfileBuilder -->|"Validate & Save"| ProfileJSON

  %% Matching Engine Subsystem
  subgraph MatchingSubsystem["Scoring & Recommendation Engine"]
    NormAliases["_norm() Tech Alias Normalizer<br/>(k8s ↔ kubernetes, golang ↔ go)"]
    Scorer["score_job() & top_matches()<br/>• 20 pts per matching language<br/>• 10 pts per matching topic<br/>• 5 pts remote bonus<br/>• Max 100 points"]
    TopMatches["Top 10 Matches<br/>+ Cited Evidence Reasons (Rule 1)"]
  end

  JobsJSON --> Scorer
  ProfileJSON --> Scorer
  NormAliases -. Normalizes terms .-> Scorer
  Scorer --> TopMatches

  %% Show HN & Pulse Subsystem
  subgraph PulseSubsystem["Company Radar & AI Pulse Intelligence"]
    ShowHNRanker["showhn.py / build_result()<br/>• URL-restricted Algolia query<br/>• Domain match precedence<br/>• is_platform_domain() check (PR #50)<br/>• Rule 9: Links to domain != ownership"]
    PulseClusterer["pulse/cluster.py<br/>• Selects longest comments (max 60)<br/>• JSON array injection defense<br/>• Pydantic schema validation<br/>• 2-attempt retry loop"]
    PulseVerify["Citation Validator<br/>• Verifies cited comment_ids in thread"]
    PulseJSON[("data/pulse/{story_id}.json<br/>Pros, Bugs, Asks")]
  end

  HNSource --> ShowHNRanker
  HNSource --> PulseClusterer
  OllamaSource <--> PulseClusterer
  PulseClusterer --> PulseVerify
  PulseVerify --> PulseJSON

  %% Outreach Draft Synthesizer Subsystem (PR #51)
  subgraph DraftSubsystem["Outreach Draft Synthesis (PR #51)"]
    DraftMatchLoop["Top 10 Match Evaluator<br/>• Non-platform domain required<br/>• Domain-linked Show HN required<br/>• Cited bug required"]
    DraftWriter["draft/write.py (write_draft)<br/>• System prompt: 5 exact lines<br/>• ModelDraft Pydantic validation<br/>• Line 2 comment citation<br/>• Names developer repo<br/>• Rejects ownership claims (Rule 9)"]
    DraftResultOut["5-Line Outreach Draft<br/>+ Line-by-Line Evidence Citations"]
  end

  TopMatches --> DraftMatchLoop
  ShowHNRanker --> DraftMatchLoop
  PulseJSON --> DraftMatchLoop
  DraftMatchLoop --> DraftWriter
  OllamaSource <--> DraftWriter
  DraftWriter --> DraftResultOut

  %% CLI Layer
  subgraph CLILayer["User Interface (CLI Layer via Typer)"]
    FetchHiringCLI["hnradar fetch-hiring<br/>[--limit, --out, --json]"]
    FingerprintCLI["hnradar fingerprint<br/>[<user> --out-dir]"]
    MatchCLI["hnradar match<br/>[<user> --jobs --json]"]
    ShowHNCLI["hnradar showhn<br/>[<company> --domain --json]"]
    PulseCLI["hnradar pulse<br/>[<story_id> --model --out]"]
    DraftCLI["hnradar draft<br/>[<user> --model --pulse-dir]"]
  end

  FetchHiringCLI --> IngestionSubsystem
  FingerprintCLI --> FingerprintSubsystem
  MatchCLI --> MatchingSubsystem
  ShowHNCLI --> ShowHNRanker
  PulseCLI --> PulseSubsystem
  DraftCLI --> DraftSubsystem

  %% Security & Sanitization
  subgraph SecurityLayer["Security & Sanitization Boundary"]
    TerminalSanitizer["_terminal_safe() (Rule 8)<br/>• Strips Cc control codes (ESC, BEL, CR)<br/>• Drops Cf format codes (Bidi overrides)<br/>• stdout JSON uses ensure_ascii=True"]
    URLSandbox["URL Sandbox Boundary (Rule 4)<br/>• Untrusted URLs only parsed, never fetched"]
    PrivacyBoundary["Privacy Boundary (Rule 5)<br/>• Public repo stats only, zero resume scraping"]
  end

  CLILayer -. Sanitized by .-> TerminalSanitizer
  ShowHNRanker -. Enforces .-> URLSandbox
  ProfileBuilder -. Enforces .-> PrivacyBoundary

  %% Autonomous Engineering Factory
  subgraph AutonomousFactory["Autonomous Agent Engineering Factory"]
    GitHubIssues["GitHub Issue Queue<br/>(label: ready-for-agent)"]
    NamedMutex["Global\HNRadarAgentPoll<br/>(Windows Named OS Mutex Guard)"]
    Poller["scripts/agent-poll.ps1<br/>• Mutex single-instance check<br/>• Spawns dedicated git worktrees<br/>• Retries up to 2 times"]
    Worktrees["Git Worktree Isolation<br/>(../hn-radar-worktrees/agent-{N})"]
    GooseAgent["Goose Ticket Worker<br/>(.goose/recipes/ticket-worker.yaml)<br/>• Model: gpt-oss:20b-cloud<br/>• Minimal clean diffs<br/>• Pytest & smoke check"]
    QodoReview["Qodo Code Review Bot<br/>• Mermaid architecture diagrams<br/>• Severity: High, Medium, Low"]
    QualityGate["AGENTS.md Quality Gate (DoD)<br/>• High & Medium findings fixed with tests<br/>• Low findings reported to human"]
    VerifySkill[".claude/skills/verify-jobs-parse/<br/>• Real-data regression testing<br/>• Must-keep vs must-exclude IDs"]
  end

  GitHubIssues --> Poller
  NamedMutex -. Guards .-> Poller
  Poller --> Worktrees
  Worktrees --> GooseAgent
  GooseAgent -->|"Git Push & PR"| QodoReview
  QodoReview --> QualityGate
  GooseAgent -. Verified by .-> VerifySkill
```

---

## 3. Subsystem Deep-Dive Diagrams

### 3.1. Job Ingestion & Sanitization Pipeline (Data Flow)

When `hnradar fetch-hiring` executes, it performs a complete sweep across the monthly Hacker News thread.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / CLI
    participant CLI as cli.fetch_hiring
    participant HN as sources/hn.py
    participant Cache as data/cache/
    participant Algolia as HN Algolia API
    participant Parse as parse.py
    participant Closed as closed.py
    participant Disk as data/jobs.json

    User->>CLI: hnradar fetch-hiring [--limit N] [--out PATH]
    CLI->>HN: find_latest_hiring_story()
    HN->>Cache: Check cached story (TTL: 1h)
    alt Cache Miss
        HN->>Algolia: GET search_by_date?tags=story,author_whoishiring
        Algolia-->>HN: JSON stories
        HN->>Cache: Atomic write cache file (Warns on failure, PR #53)
    end
    HN-->>CLI: Return story_id & title

    CLI->>HN: fetch_item(story_id)
    HN->>Cache: Check cached item (TTL: 6h)
    alt Cache Miss
        HN->>Algolia: GET items/{story_id}
        Algolia-->>HN: Full comment tree
        HN->>Cache: Atomic write cache file (Warns on failure, PR #53)
    end
    HN-->>CLI: Full item payload with children

    loop For each top-level comment
        CLI->>Parse: parse_comment(comment_id, html_text)
        Parse-->>CLI: Job(company, role, location, remote, stack, url)
        CLI->>Parse: is_candidate_profile(text)
        alt Is Candidate Pitch
            CLI->>CLI: Increment skipped_candidates count
        else Genuine Job Listing
            CLI->>Closed: closing_reply_id(comment_node)
            Closed-->>CLI: closing_id or None
            CLI->>CLI: Append to valid jobs list
        end
    end

    CLI->>Disk: Write atomic data/jobs.json
    CLI->>CLI: Apply _terminal_safe() [Rule 8]
    CLI-->>User: Render ASCII table or JSON stdout + summary
```

---

### 3.2. Developer Fingerprinting & Deterministic Match Pipeline

The `fingerprint` and `match` commands work in tandem to provide transparent, cited career recommendations.

```mermaid
graph TD
  subgraph Fingerprinting["1. Profile Fingerprint Phase"]
    UserArg["Username Argument"] --> CLI_FP["hnradar fingerprint <user>"]
    CLI_FP --> GH_Source["sources/github.py"]
    GH_Source -->|"GET /users/{user}/repos"| GH_API["GitHub REST API"]
    GH_API -->|Public Repos| FilterForks{"Is Fork?"}
    FilterForks -->|Yes| DropFork["Discard Fork"]
    FilterForks -->|No| KeepRepo["Retain Author's Repo"]
    
    KeepRepo --> AggLang["Aggregate Byte Size per Language<br/>(Keep Top 5)"]
    KeepRepo --> AggTopics["Count Topics Occurrence<br/>(Keep Top 10)"]
    KeepRepo --> TopRepos["Sort by Stars Descending<br/>(Keep Top 5 Notable)"]
    
    AggLang --> PydanticProfile["Pydantic Profile Model"]
    AggTopics --> PydanticProfile
    TopRepos --> PydanticProfile
    PydanticProfile --> SaveProfile[("data/profiles/{user}.json")]
  end

  subgraph Matching["2. Job Matching Phase"]
    CLI_Match["hnradar match <user>"] --> ReadProfile[("data/profiles/{user}.json")]
    CLI_Match --> ReadJobs[("data/jobs.json")]
    
    ReadProfile --> MatchEngine["Deterministic Match Engine"]
    ReadJobs --> MatchEngine
    
    MatchEngine --> AliasNorm["_norm() Alias Canonicalization<br/>(postgres ↔ postgresql, ts ↔ typescript)"]
    AliasNorm --> ScoreCalc["Scoring Algorithm:<br/>• Language Overlap: +20 pts<br/>• Topic Overlap: +10 pts<br/>• Remote Bonus: +5 pts (if stack overlap)<br/>• Max Score: 100 pts"]
    
    ScoreCalc --> EvGen["Evidence Synthesizer (Rule 1):<br/>• 'Your Python work matches stack'<br/>• 'Your repo fastapi-app is written in Python'<br/>• 'Your repos use topic kubernetes'"]
    
    EvGen --> HeapSort["heapq.nlargest(10, ...)<br/>Sort by (score desc, comment_id desc)"]
    HeapSort --> FinalMatches["Top Matches Table or JSON"]
  end

  SaveProfile --> ReadProfile
```

---

### 3.3. Pulse Qualitative Sentiment Pipeline (Ollama LLM)

The `pulse` command utilizes a local LLM to structure feedback into pros, bugs, and asks with strict citation guarantees.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as hnradar pulse
    participant HN as sources/hn.py
    participant Cluster as pulse/cluster.py
    participant Schema as pulse/schema.py
    participant Ollama as sources/ollama.py (OllamaClient)
    participant Disk as data/pulse/{story_id}.json

    User->>CLI: hnradar pulse 12345 [--model qwen2.5:7b]
    CLI->>HN: fetch_item(12345)
    HN-->>CLI: Return Show HN story & comments

    CLI->>Cluster: cluster(story_id, title, comments, client)
    Cluster->>Cluster: select_comments(): Filter text, sort by length (longest first, max 60, cut to 1500 chars)
    Cluster->>Cluster: Re-sort selected comments in thread order
    Cluster->>Cluster: Enforce MIN_COMMENTS >= 3

    Cluster->>Schema: ModelReply.model_json_schema()
    Schema-->>Cluster: JSON Schema definition

    loop Up to 2 Attempts (Rule 2 & Retry Logic)
        Cluster->>Ollama: complete(system_prompt, user_prompt, schema)
        Note over Ollama: Options: temperature=0, num_predict=2048
        Ollama-->>Cluster: Raw JSON string reply
        Cluster->>Schema: ModelReply.model_validate_json(raw)
        alt Validation Error
            Schema-->>Cluster: ValidationError (loc, message)
            Cluster->>Cluster: Format clean input-free error message
        else Schema Passes
            Cluster->>Cluster: _check_ids(): Verify all cited comment_ids belong to the thread
            alt Unknown IDs Found
                Cluster->>Cluster: Reject attempt (IDs not in thread)
            else IDs Verified
                Cluster-->>CLI: Return validated PulseResult
            end
        end
    end

    CLI->>Disk: Atomically write data/pulse/{story_id}.json
    CLI-->>User: Output terminal table of Pros, Bugs, and Asks with Comment Citations
```

---

### 3.4. 5-Line Outreach Draft Generation Pipeline (`hnradar draft` — PR #51)

The `draft` command brings together developer profile matching, company domain validation, Show HN sentiment bugs, and local LLM composition into an exact 5-line cited outreach note.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as hnradar draft <user>
    participant Match as match.top_matches()
    participant ShowHN as showhn.search_show_hn()
    participant Pulse as _cited_bug() (Pulse)
    participant Writer as draft/write.py (write_draft)
    participant Ollama as sources/ollama.py (OllamaClient)

    User->>CLI: hnradar draft username [--model qwen2.5:7b]
    CLI->>Match: top_matches(profile, jobs, limit=11)
    Match-->>CLI: Top 10 scored matches

    loop For each match in Top 10
        CLI->>CLI: Extract matched repo and job URL domain
        alt No matched repo or domain missing
            CLI->>CLI: Record skip reason & continue
        end
        CLI->>CLI: Check is_platform_domain(domain) [PR #50]
        alt Domain is shared/platform host (github.io, notion.so)
            CLI->>CLI: Record platform skip reason & continue
        end
        CLI->>ShowHN: search_show_hn(company, domain=domain)
        ShowHN-->>CLI: Candidate stories
        alt No story links to domain or low confidence
            CLI->>CLI: Record skip reason & continue
        end
        CLI->>Pulse: _cited_bug(story_id, comments, pulse_dir, client)
        Pulse-->>CLI: (summary, cited_comments) or None
        alt No cited bug found in Show HN comments
            CLI->>CLI: Record skip reason & continue
        else Valid bug found!
            CLI->>Writer: write_draft(user, company, domain, repo, problem, cited, client)
            loop Up to 2 Attempts (Rule 2)
                Writer->>Ollama: complete(SYSTEM_PROMPT, facts_json, ModelDraft.schema)
                Ollama-->>Writer: JSON string
                Writer->>Writer: ModelDraft.model_validate_json(raw)
                Writer->>Writer: _check(): Exactly 5 lines, line 2 cites comments, names repo, rejects forbidden phrases
            end
            Writer-->>CLI: DraftResult (lines, evidence)
            Note over CLI: Match succeeded -- break out of loop
        end
    end

    alt Match Found & Drafted
        CLI-->>User: Print 5-line outreach note + line-by-line comment citations and repo details
    else No Usable Match in Top 10
        CLI-->>User: Print "No cited problem found", list skipped matches, and exit 0
    end
```

---

### 3.5. Autonomous Agent Factory & Quality Gate Cycle

The project implements a fully autonomous ticket-worker loop with rigorous architectural oversight.

```mermaid
stateDiagram-v2
    [*] --> Idle: Single-instance Mutex Guard (agent-poll.ps1)
    
    Idle --> TicketFound: Poll finds issue labeled 'ready-for-agent'
    Idle --> Idle: No ready issues (quiet exit 0)

    TicketFound --> WorktreeSetup: Create dedicated git worktree in ../hn-radar-worktrees/
    WorktreeSetup --> GooseWorker: Launch Goose with .goose/recipes/ticket-worker.yaml
    
    state GooseWorker {
        [*] --> ReadIssue: gh issue view {N}
        ReadIssue --> ReadRules: type AGENTS.md (Rules 1-10 & Quality Gate)
        ReadRules --> InspectCode: Read necessary files with shell tool
        InspectCode --> ImplementDiff: Minimal diff + Edge-case tests (Rule 7)
        ImplementDiff --> RunTests: uv run pytest -q
        RunTests --> SmokeCheck: uv run hnradar fetch-hiring --limit 20
        SmokeCheck --> CommitPush: git commit & git push origin agent/{N}
        CommitPush --> OpenPR: gh pr create (Checklist & acceptance criteria)
    }

    GooseWorker --> QodoReview: PR Trigger activates qodo-code-review[bot]
    
    state QodoReview {
        [*] --> GenDiagram: Synthesize Mermaid Architecture Diagram
        GenDiagram --> ClassifyFindings: Categorize into High, Medium, Low
    }

    QodoReview --> QualityGate: AGENTS.md Quality Gate Check

    state QualityGate {
        HighOrMedium: High / Medium findings present?
        ResolveRequired: Agent must fix in next run with new tests
        LowOnly: Low / Informational findings only?
        HumanEscalate: Report in PR body for human review
    }

    QualityGate --> HumanReview: Definition of Done Satisfied
    QualityGate --> TicketRetry: Findings exist (Attempt <= 2)
    QualityGate --> NeedsHuman: Attempt > 2 or Blocked
    
    NeedsHuman --> [*]: Add label 'needs-human' & post diagnostic comment
    HumanReview --> Merged: Human merges PR into main
    Merged --> [*]
```

---

## 4. Comprehensive Catalog of Qodo PR Diagrams

The following section catalogues the architectural diagrams generated by **Qodo Code Review** across all 26 closed Pull Requests in `researchsite/hn-radar`, documenting the chronological evolution of the system.

### PR #1: feat: add hnradar fetch-hiring command
- **Status:** `Merged`
- **Architectural Contribution:** Initial foundation PR. Added fetch-hiring command and core parser. (Qodo automated review errored on first run; diagram synthesized from PR code).

```mermaid
graph TD
  HN["HN Algolia API"] --> Fetch["fetch-hiring CLI"] --> Parser["Job Parser"] --> Jobs[("data/jobs.json")]
  Fetch --> Table["CLI Table Output"]
```

---
### PR #2: docs: AGENTS.md factory rules
- **Status:** `Merged`
- **Architectural Contribution:** Codified the initial 5 AGENTS.md factory rules governing citation, schema validation, network isolation, sandboxing, and minimal personal data.

```mermaid
graph TD
  A["Coding agents"] --> B["AGENTS.md"] --> C["Setup and checks"]
  B --> D["Development rules"] --> E["Target modules"]
```

---
### PR #6: feat: add hnradar fingerprint command (#3)
- **Status:** `Merged`
- **Architectural Contribution:** Added GitHub user fingerprinting, analyzing up to 2000 public repos (excluding forks) to extract top 5 languages, top 10 topics, and top 5 notable repos.

```mermaid
graph TD
  CLI["Fingerprint CLI"] --> Source["GitHub source"] --> API["GitHub REST API"]
  Source --> Cache[("Response cache")]
  CLI --> Builder["Profile builder"] --> Model["Pydantic Profile"] --> Output[("Profile JSON")]
```

---
### PR #7: docs: add AGENTS.md rules 6 and 7 (limits fail loudly, edge-case tests)
- **Status:** `Merged`
- **Architectural Contribution:** Introduced Rule 6 (limits fail loudly, no truncated silent outputs) and Rule 7 (every PR must ship edge-case tests for empty, limit, over-limit, and upstream errors).

```mermaid
graph TD
  F["Review findings"] --> A["AGENTS.md rules"] --> C["Future changes"]
  C --> L["Loud failures"]
  C --> T["Edge-case tests"]
```

---
### PR #8: feat: add Goose ticket-worker recipe and agent poller
- **Status:** `Merged`
- **Architectural Contribution:** Created autonomous engineering pipeline: PowerShell poller with OS named mutex single-instance guard and Goose ticket-worker recipe operating in isolated worktrees.

```mermaid
graph TD
  A["PowerShell poller"] --> B{"Ready issue?"} -->|yes| C["Goose runner"] --> D["Ticket recipe"] --> E["Git and tests"] -->|passes| F["GitHub PR"]
  B -->|none| G["Quiet exit"]
  E -->|blocked| H["Needs human"]
  C -->|run fails| H
```

---
### PR #9: feat: add --json option to fetch-hiring (#5)
- **Status:** `Merged`
- **Architectural Contribution:** Added --json option and clean terminal table default for fetch-hiring, allowing composable piping into downstream tools.

```mermaid
graph TD
  CLI["fetch-hiring CLI"] --> HN["HN source"] --> Parser["Job parser"] --> Mode{"JSON flag?"} -->|yes| Stdout["JSON stdout"]
  Mode -->|no| File["Jobs file"]
```

---
### PR #10: fix: cloud model and stricter tool rules for the ticket worker
- **Status:** `Merged`
- **Architectural Contribution:** Upgraded worker to gpt-oss:20b-cloud, added strict directives forbidding deleting existing code and requiring full file writes.

```mermaid
graph TD
  P["Issue poller"] --> G["Goose run"] --> M["Cloud model"] --> T["Shell and write tools"] --> F["Worktree files"]
  R["Worker recipe"] --> G
  R --> M
```

---
### PR #11: feat: rule 8 - clean untrusted post text before printing
- **Status:** `Merged`
- **Architectural Contribution:** Added Rule 8: untrusted text from HN/GitHub must be cleaned before printing (strips Cc control characters, Cf bidi overrides; ensure_ascii=True on stdout JSON).

```mermaid
graph TD
  A["HN posts"] --> B["Comment parser"] --> C["Job records"] --> D["Terminal cleaner"] --> E["CLI table"]
  C --> F["JSON output"]
  A --> D
```

---
### PR #21: feat: hnradar showhn - find a company's Show HN story
- **Status:** `Merged`
- **Architectural Contribution:** Introduced showhn command to discover Show HN posts via Algolia, ranking by domain match, points, and recency with atomic cache writes.

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant HNSource as HN Source
    participant Cache
    participant Algolia
    participant Ranker
    User->>CLI: showhn company and domain
    CLI->>CLI: Validate input
    CLI->>HNSource: Search Show HN
    HNSource->>Cache: Read cached response
    alt Valid cached response
        Cache-->>HNSource: Validated hits
    else Cache miss or invalid entry
        HNSource->>Algolia: Relevance search
        Algolia-->>HNSource: Hits and total count
        HNSource->>HNSource: Validate response
        HNSource->>Cache: Atomic cache write
    end
    HNSource-->>CLI: Mapped hits and total count
    CLI->>Ranker: Rank against domain
    Ranker-->>CLI: Top five and confidence
    CLI-->>User: Table or JSON
```

---
### PR #22: docs: add quality gate (definition of done) to AGENTS.md and the ticket-worker recipe
- **Status:** `Merged`
- **Architectural Contribution:** Formalized Definition of Done: High and Medium findings must be fixed with tests, Low findings reported, disagreements require code citations, latest commit covered.

```mermaid
graph TD
  Gate["Quality gate"] --> Worker["Ticket worker"] --> Findings["Review findings"] --> Fixes["Finding fixes"] --> Checks["Tests and smoke"] --> PR["Open PR"] --> Poller["Issue poller"] --> Human["Human review"]
  PR --> Findings
  Gate --> Human
```

---
### PR #24: feat: hnradar match - top 3 jobs for a user (#12)
- **Status:** `Merged`
- **Architectural Contribution:** Introduced match command: deterministic scoring (20 pts language, 10 pts topic, 5 pts remote bonus, max 100), alias normalization, and cited reason generation.

```mermaid
graph TD
  CLI["Match CLI"] --> Profile[("Saved profile")] --> Scorer["Job scorer"] --> Result["Match result"] --> Output["Table or JSON"]
  CLI --> Jobs[("Saved jobs")] --> Scorer
```

---
### PR #28: docs: pre-review checklist in AGENTS.md
- **Status:** `Merged`
- **Architectural Contribution:** Added 9-point pre-review checklist addressing recurring defect patterns (ticket line-by-line, clean input failures, ambiguity rejection, identity checking).

```mermaid
graph TD
  A["PR changes"] --> B["Pre-review checklist"] --> C{"Ready for review?"} -->|Yes| D["Request review"] --> E["Quality gate"]
  C -->|No| A
```

---
### PR #29: docs: README with setup and how to run every command
- **Status:** `Merged`
- **Architectural Contribution:** Added full repository README with setup, uv invocation patterns, and command documentation for fetch-hiring, showhn, fingerprint, and match.

```mermaid
graph TD
  HN["HN API"] --> Fetch["fetch-hiring"] --> Jobs[("jobs.json")] --> Match["match"]
  GitHub["GitHub API"] --> Fingerprint["fingerprint"] --> Profiles[("profile JSON")] --> Match
  HN --> ShowHN["showhn"]
```

---
### PR #30: feat: flag closed jobs from the poster's own replies (#25)
- **Status:** `Merged`
- **Architectural Contribution:** Added closed.py parser: analyzes author's child replies to detect closing notices with natural language clause parsing and bisect positioning.

```mermaid
graph TD
  HN["HN thread"] --> Fetch["Fetch hiring"] --> Parse["Parse comment"] --> Jobs["Job JSON"]
  Fetch --> Scan["Poster reply scan"] --> Check{"Closing notice?"} --> Jobs
```

---
### PR #33: feat: showhn URL-restricted domain query (#20)
- **Status:** `Merged`
- **Architectural Contribution:** Added secondary Algolia search with restrictSearchableAttributes=url when --domain is provided, deduplicating IDs and aggregating total counts.

```mermaid
sequenceDiagram
    actor User
    participant CLI as showhn CLI
    participant Search as HN search
    participant Cache as Response cache
    participant API as Algolia API
    participant Rank as Result ranking
    User->>CLI: company and optional domain
    CLI->>Search: search_show_hn
    Search->>Cache: look up name query
    opt cache miss
        Search->>API: name search
        API-->>Search: name hits
        Search->>Cache: save validated response
    end
    opt domain provided
        Search->>Cache: look up URL query
        opt cache miss
            Search->>API: URL-restricted search
            API-->>Search: URL hits
            Search->>Cache: save validated response
        end
        Note over Search: Deduplicate IDs and compute total
    end
    Search-->>CLI: hits and total or error
    CLI->>Rank: build_result
    Rank-->>CLI: domain-first top five
    CLI-->>User: candidates or error
```

---
### PR #34: experiment: showhn fallback and labels (Day 11, do not merge)
- **Status:** `Experiment (Closed, Not Merged)`
- **Architectural Contribution:** Experimental run evaluating fallback behaviors and label cues when URL search fails or domain is absent.

```mermaid
graph TD
  CLI["showhn CLI"] --> Name["Name search"] --> Domain{"Domain provided?"} -->|yes| URL["URL search"] -->|available| Merge["Deduplicate hits"] --> Rank["Rank candidates"] --> Out["Table or JSON"]
  Domain -->|no| Rank
  URL -->|unavailable| Rank
```

---
### PR #35: docs: AGENTS.md rule 9, a domain match is never company ownership
- **Status:** `Merged`
- **Architectural Contribution:** Added Rule 9: a domain match means a story links to that domain, never that the company owns it or posted it (protects against multi-tenant platforms like notion.so).

```mermaid
graph TD
  A["AGENTS.md rule 9"] --> B["Qodo re-import"] --> C["Future reviews"] --> D["Show HN wording"]
```

---
### PR #36: experiment: showhn domain search (Day 11 run B, do not merge)
- **Status:** `Experiment (Closed, Not Merged)`
- **Architectural Contribution:** Second experiment testing unified search coordinator structure for name and URL search.

```mermaid
graph TD
  CLI["showhn CLI"] --> Search["Search coordinator"] --> Name["Name search"] --> Merge["Deduplicate hits"] --> Rank["Rank candidates"] --> Output["Table or JSON"]
  Search -->|"if domain"| URL["URL search"] --> Merge
```

---
### PR #39: docs: AGENTS.md rule 10, a failed upstream request is never returned as complete
- **Status:** `Merged`
- **Architectural Contribution:** Added Rule 10: any failed request to Algolia, GitHub, or Ollama must raise an error and exit 1; never swallow failures into partial results.

```mermaid
graph TD
  U["Upstream services"] --> S["Source adapters"] --> C["CLI commands"] --> O["Visible outcome"]
  R["Rule 10"] -. governs .-> S
  R -. governs .-> C
```

---
### PR #43: feat: careers-only full-text search with its own Pagefind index (#40)
- **Status:** `Merged`
- **Architectural Contribution:** Integrated Pagefind static indexing over jobs.json for full-text careers search with field-level fallback.

```mermaid
graph TD
  Jobs[("Jobs JSON")] --> Builder["Index builder"] --> CLI["Pagefind CLI"] --> Index[("Careers index")] --> Helper["HN search"] --> Explorer["Job explorer"]
  Jobs --> Explorer
  Helper -->|"Index unavailable"| Fallback["Field fallback"] --> Explorer
```

---
### PR #46: feat: skip candidate profiles in fetch-hiring and report the count (#45)
- **Status:** `Merged`
- **Architectural Contribution:** Added is_candidate_profile() to filter out self-promotional job seekers from fetch-hiring, keeping data/jobs.json strictly hiring companies.

```mermaid
graph TD
  A["HN comments"] --> B["Limit slice"] --> C["Parse comment"] --> D{"Candidate profile?"}
  D -->|No| E["Kept jobs"] --> F["Jobs output"]
  D -->|Yes| G["Skip count"] --> H["CLI note"]
```

---
### PR #48: feat: verify-jobs-parse skill, a real-data check for parser changes
- **Status:** `Merged`
- **Architectural Contribution:** Added Claude skill and compare_jobs.py to verify parser changes against live HN threads, validating must-keep/must-exclude IDs and baseline stability.

```mermaid
graph TD
  Skill["Verification skill"] --> Preflight["Tests and hash"] --> Fetch["Fetch hiring"] --> Scratch[("Scratch jobs")] --> Compare["Compare IDs"] --> Report[("JSON report")]
  Baseline[("Baseline jobs")] --> Compare
  Fetch --> Thread[("Cached thread")]
  Thread --> Compare
```

---
### PR #49: feat: hnradar pulse STORY_ID groups Show HN comments into pros, bugs and asks (#13)
- **Status:** `Merged`
- **Architectural Contribution:** Introduced pulse command: leverages local Ollama LLM (qwen2.5:7b) to cluster comments into pros, bugs, and asks with mandatory comment ID citation.

```mermaid
graph TD
  CLI["Pulse CLI"] --> HN["Cached HN source"] --> Cluster["Comment selection"] --> Ollama["Ollama client"] --> Validate["Reply validation"] --> Output[("Pulse JSON")]
  CLI --> Output
```

---
### PR #50: feat: showhn flags platform domains as low confidence (#38)
- **Status:** `Merged`
- **Architectural Contribution:** Flags shared/platform domains (github.com, notion.so, substack.com, form hosts) as low confidence (Rule 9). Links to platform domains may belong to someone else, not the company.

```mermaid
graph TD
  CLI["showhn CLI"] --> Search["HN search"] --> Rank["Candidate ranking"] --> Check{"Platform host?"} -->|confidence flag| Result["ShowHNResult"] --> Output["Table or JSON"]
  Domains["Platform domains"] --> Check
  Rank -->|candidates| Result
```

---
### PR #51: feat: hnradar draft writes a 5-line cited outreach note (#14)
- **Status:** `Merged`
- **Architectural Contribution:** Introduced draft command: evaluates top 10 matches, requires non-platform domain, Show HN link, and cited bug from comments. Writes a 5-line outreach note via local LLM with strict validation (Rule 1 & Rule 2).

```mermaid
graph TD
  A["Profile and jobs"] --> B["Top 10 matches"] --> C{"Matched repo and domain?"} -- "Yes" --> D["Domain-safe Show HN"] --> E{"Cited bug?"} -- "Yes" --> F["Draft validation"] --> G["Note and evidence"]
  C -- "No" --> H["Skip or explain"]
  D -- "No matching story" --> H
  E -- "No" --> H
```

---
### PR #53: fix: an unwritable HN cache no longer fails a successful fetch (#52)
- **Status:** `Merged`
- **Architectural Contribution:** Resilient cache writing: an unwritable or permission-denied cache directory emits a single safe warning to stderr and returns the fetched data instead of crashing the CLI command.

```mermaid
graph TD
  A["CLI commands"] --> B["Fetch HN JSON"] --> C{"Valid response?"}
  C -- "yes" --> D["Write cache"] --> E{"Write fails?"}
  C -- "no" --> H["Raise error"]
  E -- "yes" --> F["Warn once"] --> G["Return data"]
  E -- "no" --> G
```

---

## 5. Architectural Compliance & AGENTS.md Invariants

All components in the HN Radar architecture are bound by the 10 invariant development rules documented in `AGENTS.md`:

| Rule | Name | Architectural Mechanism | Enforcing Files |
| :--- | :--- | :--- | :--- |
| **Rule 1** | **Every claim is cited** | Insights, match reasons, and draft outreach lines must cite exact source comment IDs. | `pulse/cluster.py`, `match.py`, `draft/write.py`, `closed.py` |
| **Rule 2** | **LLM output is schema-validated** | Outputs from Ollama parse exclusively through Pydantic models with constrained JSON decoding. | `pulse/schema.py`, `draft/schema.py`, `sources/ollama.py` |
| **Rule 3** | **Network goes through sources/** | All HTTP requests are centralized in `src/hnradar/sources/` backed by atomic file-based caching. | `sources/hn.py`, `sources/github.py`, `sources/ollama.py` |
| **Rule 4** | **Untrusted URLs only in sandbox layer** | URLs taken from posts are only parsed for host validation, never fetched over the network. | `showhn.py` (`host_matches`, `url_domain`) |
| **Rule 5** | **Minimal personal data** | No scraping of LinkedIn, resumes, or private info; derived strictly from public GitHub repos. | `fingerprint.py`, `sources/github.py` |
| **Rule 6** | **Limits fail loudly** | Pagination caps (2,000 repos) and loops raise hard errors; never return silent partial results. | `sources/github.py`, `sources/hn.py`, `cli.py` (draft cap) |
| **Rule 7** | **Every change ships edge-case tests** | Mandatory tests for empty inputs, boundary limits, over-limit inputs, and upstream errors. | `tests/`, `AGENTS.md` |
| **Rule 8** | **Untrusted post text is cleaned** | Strips Unicode control chars (`Cc`) and formatting overrides (`Cf`) before terminal rendering. | `cli.py` (`_terminal_safe`) |
| **Rule 9** | **Domain match is never company ownership** | A domain match means a story links to that domain, never that the company owns or posted it. Platform domains are flagged. | `showhn.py`, `draft/write.py`, `models.py` |
| **Rule 10** | **Failed upstream request never complete** | Upstream API failures must exit 1 with an informative message; never return partial data. | `sources/hn.py`, `sources/github.py`, `cli.py` |

---

## 6. Summary

The HN Radar architecture achieves high reliability and deterministic behavior through strict decoupling:
1. **Source Adapters** isolate network I/O, rate limiting, and resilient on-disk caching (PR #53).
2. **Pure Domain Functions** (`parse.py`, `match.py`, `fingerprint.py`, `showhn.py`, `closed.py`) operate without side effects or network calls.
3. **Pydantic Validation Models** enforce boundary constraints across CLI inputs, API payloads, and LLM outputs (`ModelReply`, `ModelDraft`).
4. **Outreach Draft Generation** (`hnradar draft` / PR #51) synthesizes company matches, Show HN bugs, and developer repos into cited outreach notes without false claims of ownership (PR #50 / Rule 9).
5. **The Autonomous Factory & Qodo Quality Gate** ensure that every modification is accompanied by edge-case tests, loud limits, and architectural verification.
