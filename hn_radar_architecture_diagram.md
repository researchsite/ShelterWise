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
    TopMatches["Deterministic Scorer Output<br/>• match command: Top 3 opportunities<br/>• draft command: Evaluates top 10 candidates"]
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

  %% Development Engine & Qodo Review Quality Gate
  subgraph DevEngine["Engineering Workflow & Qodo Review Gate"]
    HumanDev["Human Engineer (Sham)<br/>+ AI Pair (Claude Sonnet)<br/>• Hand-crafted implementations & commands"]
    GooseOneOff["Goose Experiment (PR #9)<br/>• One-off trial on Ticket #5 only"]
    LocalVerify["Local Verification & Quality Gate<br/>• uv run pytest -q<br/>• verify-jobs-parse real-data skill"]
    GitHubPRs["GitHub Pull Requests<br/>(Branch pushes & reviews)"]
    QodoReview["Qodo Code Review Bot<br/>• Automated architecture diagrams<br/>• AGENTS.md Review Standards (Rules 9, 10)"]
    ReviewTriage["Human Review Triage & Fixes<br/>• fix: ... review round 1 commits<br/>• Human maintainer merge to main"]
  end

  HumanDev --> LocalVerify
  GooseOneOff -. One-time experiment .-> GitHubPRs
  LocalVerify --> GitHubPRs
  GitHubPRs --> QodoReview
  QodoReview --> ReviewTriage
  ReviewTriage -->|"Merge Approval"| GitHubPRs
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
    
    EvGen --> HeapSort["heapq.nlargest(limit, ...)<br/>• hnradar match: limit=3 (Top 3)<br/>• hnradar draft: limit=11 (Scans top 10)"]
    HeapSort --> FinalMatches["Top 3 Scored Matches for User (match)<br/>or Ranked Candidate Stream (draft)"]
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
        User->>User: Human reviews note and citations (Rule 4: Nothing sent automatically)
    else No Usable Match in Top 10
        CLI-->>User: Print "No cited problem found", list skipped matches, and exit 0
    end
```

---

### 3.5. Autonomous Agent Factory & Quality Gate Cycle

The project implements a fully autonomous ticket-worker loop with rigorous architectural oversight.

```mermaid
stateDiagram-v2
    [*] --> IssueScoping: Human developer authors GitHub issue with acceptance criteria
    
    state EngineeringWorkflow {
        [*] --> Implementation: Developer (Sham) pairs with Claude Sonnet
        Implementation --> TestsAndChecks: Minimal clean diff + edge-case tests
        TestsAndChecks --> LocalVerify: uv run pytest -q
        LocalVerify --> RealDataCheck: verify-jobs-parse skill check (PR #48)
        RealDataCheck --> PushBranch: git commit & git push origin feat/...
        PushBranch --> OpenPR: gh pr create with checklist
    }

    state HistoricalGooseExperiment {
        Issue5: Ticket #5 (fetch-hiring --json)
        GooseRun: Goose ticket-worker recipe (PR #9 only)
        Issue5 --> GooseRun
    }

    OpenPR --> QodoReview: GitHub webhook activates qodo-code-review[bot]
    
    state QodoReviewGate {
        [*] --> GenerateDiagrams: Synthesize Mermaid architecture delta
        GenerateDiagrams --> ClassifyFindings: Categorize into High, Medium, Low
        ClassifyFindings --> ApplyReviewStandards: Evaluate against AGENTS.md rules (Rules 9, 10)
    }

    QodoReviewGate --> DeveloperTriage: Human reviews Qodo findings
    
    state RemediationLoop {
        DeveloperTriage --> FixRequired: High / Medium findings need resolution
        FixRequired --> Round1Commit: Write tests and push review remediation commit
        Round1Commit --> QodoReviewGate: Re-review updated diff
        DeveloperTriage --> GatePassed: All findings resolved or verified safe
    }

    GatePassed --> HumanSignoff: Maintainer verifies final clean diff
    HumanSignoff --> MergedMain: Merged to main (or stacked branch for careers)
    MergedMain --> [*]
```

---

## 4. Comprehensive Catalog of Qodo PR Diagrams

The following section catalogues the architectural diagrams generated by **Qodo Code Review** across all 26 closed Pull Requests in `researchsite/hn-radar`, documenting the chronological evolution of the system.

### PR #1: feat: add hnradar fetch-hiring command
- **Status:** `Merged`
- **Architectural Contribution:** Initial foundation PR. Added fetch-hiring command and core parser. (Note: Developer's Qodo account access was blocked until November 11, 2026; once unblocked on Nov 11, /agentic_review ran cleanly without errors).

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
- **Architectural Contribution:** Day 11 Seeded-Defect Experiment A (do not merge): Intentionally tested Qodo review bot by introducing subtle fallback behavior and misleading labels when URL search fails. Closed unmerged as planned once Qodo triaged the behavior.

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
- **Architectural Contribution:** Day 11 Seeded-Defect Experiment B (do not merge): Intentionally tested Qodo review bot detection on a second seeded variation combining name and URL queries into a coordinator. Closed unmerged as planned.

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
- **Status:** `Merged into stacked branch feat/site-careers (NOT main)`
- **Architectural Contribution:** Integrated isolated Pagefind 1.6.0 static indexing over jobs.json for full-text careers search in site/careers/pagefind/. Part of the 3-tier careers branch stack (PR #42 OPEN against main, PR #43 MERGED into stack, PR #44 OPEN against stack).

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



---

## 2.1. Human Decision Points & Operational Governance

HN Radar operates as a human-in-the-loop system where automation assists but never usurps developer oversight:

```mermaid
graph TD
  subgraph HumanGates["Mandatory Human Decision Gates"]
    G1["1. Ticket Scoping & Rule Formulation<br/>• Defines acceptance criteria & AGENTS.md rules"]
    G2["2. Local Command Execution<br/>• Runs test suite, smoke checks, and parser verification"]
    G3["3. Qodo Review Triage<br/>• Evaluates AI review suggestions, discards false positives, writes fixes"]
    G4["4. Outreach Review (Rule 4 Gate)<br/>• Reviews 5-line outreach note & cited comments before sending"]
    G5["5. Branch Merge Governance<br/>• Approves PRs, manages branch stacks (feat/site-careers)"]
  end

  G1 --> G2
  G2 --> G3
  G3 --> G5
  G2 -. Runs CLI .-> G4
```

- **Rule 4 Gate (Outreach Delivery):** `hnradar draft` outputs the drafted outreach note and evidence to stdout. It is strictly forbidden from transmitting emails or API messages autonomously. A human engineer must inspect the cited Hacker News comments, verify the repository attribution, and transmit the communication.
- **Review Triage Gate:** Qodo review comments are advisory; the human developer evaluates each item, writes reproducible tests, and commits fixes in explicit `review round 1` commits.

---

## 2.2. Chronological Qodo Layering Evolution

Rather than a static one-time setup, Qodo code review was layered into the repository progressively across the 14-day cycle:

1. **Phase 1 (Nov 11 - PR #1, #2, #7):** Account access activated; enabled basic automated PR reviews (`/agentic_review`).
2. **Phase 2 (Nov 12 - PR #8):** Infrastructure hardening; Qodo review identified git worktree race conditions and uncommitted change retention issues in `scripts/agent-poll.ps1`.
3. **Phase 3 (Nov 14 - PR #22):** Formalized the repository Quality Gate and Definition of Done in `docs/quality-gate.md`.
4. **Phase 4 (Nov 16-17 - PR #28, #35, #39):** Codified `AGENTS.md` rules directly into Qodo Review Standards:
   - *Rule 9:* Domain match is never company ownership (PR #35).
   - *Rule 10:* Upstream failures are never returned as complete (PR #39).
   - *Pre-review checklist:* Added 9-item pre-review verification list (PR #28).
5. **Phase 5 (Nov 18 - PR #48):** Real-data verification armor; created `.claude/skills/verify-jobs-parse/` to verify parser changes against live threads, with Qodo review hardening it against false PASS results.
6. **Phase 6 (Nov 19 - PR #49, #50, #51, #53):** Standardized the multi-round remediation workflow (`fix: ... review round 1`) for sentiment clustering, platform domain protection, 5-line outreach draft contract, and resilient cache writes.

---

## 3.6. Day 14 Production Guards & Review Remediation

The final Day 14 stabilization sprint introduced three architectural guards:

1. **Resilient Cache-Write Guard (PR #53 / Issue #52):**
   - Implemented `_warn_cache_not_written()` in `src/hnradar/sources/hn.py`.
   - When disk or cache directory is unwritable or permissions are denied, prints a single warning to `stderr` and carries on without failing.
   - Reverses previous brittle behavior where an `OSError` on cache write crashed a successful fetch.
2. **ModelDraft 5-Line Contract Guard (PR #51 / Issue #14):**
   - `_check()` strictly validates LLM output: exactly 5 non-empty lines.
   - Line 2 MUST cite Hacker News comment IDs from the thread and use the phrasing *"links to <domain>"* (Rule 9).
   - Rejects forbidden AI clichés (*"streamline"*, *"delve"*, *"thrilled"*).
   - Enforces a 2-attempt retry loop; if invalid after 2 attempts, exits cleanly with exit code 0 and logs diagnostic skip reasons.
3. **Platform Domain Leak Guard (PR #50 / Issue #38):**
   - `is_platform_domain()` checks domains against 14 multi-tenant platform hosts (`github.io`, `notion.so`, `substack.com`).
   - Flags platform hosts as low confidence and skips them in `draft` to prevent attributing third-party Show HN stories to unrelated companies.

---

## 3.7. The Careers Static Web Portal (`site/careers/`)

The repository includes a decoupled static web portal located in `site/careers/` (developed on branch `feat/site-careers`):
- **Architecture:** Zero-build pure HTML5/CSS/JavaScript consuming `data/jobs.json`.
- **Search Subsystem:** Dedicated **Pagefind 1.6.0** indexer (`site/tools/build_careers_index.py`) generating an isolated search index in `careers/pagefind/`. Does not conflict with parent website search.
- **Brand Tokens:** Uses `--rw-*` CSS variables (`--rw-text`, `--rw-orange`, `--rw-card`) supporting instant dark/light themes.
- **XSS Boundary:** All job descriptions and Hacker News comment text are rendered via `textContent` after stripping bidirectional and control characters; `innerHTML` is strictly prohibited.
- **Branch Stack Status:** PR #42 (Base: `main`, Head: `feat/site-careers` - OPEN), PR #43 (Base: `feat/site-careers`, Head: `feat/careers-search` - MERGED into stack), PR #44 (Base: `feat/site-careers`, Head: `feat/careers-company` - OPEN).

---

## 5. Works Now vs Planned / In-Progress Status Matrix

| Subsystem / Feature | Current State | Code Location | Governing Rules / PRs |
|---|---|---|---|
| **Hiring Thread Ingestion** | **WORKS NOW** | `src/hnradar/sources/hn.py`, `parse.py` | PR #1, #46, #53; Rules 4, 10 |
| **Poster Reply Closed Job Filter** | **WORKS NOW** | `src/hnradar/closed.py` | PR #30; Rule 8 |
| **Resilient Cache Write** | **WORKS NOW** | `src/hnradar/sources/hn.py` | PR #53 (Issue #52); Rule 10 |
| **Candidate Profile Skip** | **WORKS NOW** | `src/hnradar/parse.py` (`is_candidate_profile`) | PR #46 (Issue #45) |
| **GitHub Developer Fingerprint** | **WORKS NOW** | `src/hnradar/sources/github.py`, `fingerprint.py` | PR #6; Rule 5 (no resume scraping) |
| **Job Matching Engine (Top 3)** | **WORKS NOW** | `src/hnradar/match.py` (`top_matches`) | PR #11; Deterministic scoring |
| **Show HN Dual-Search & Domain Check** | **WORKS NOW** | `src/hnradar/showhn.py` | PR #33, #50; Rules 9, 10 |
| **Platform Domain Filter** | **WORKS NOW** | `src/hnradar/showhn.py` (`is_platform_domain`) | PR #50 (Issue #38); Rule 9 |
| **Show HN Sentiment Pulse** | **WORKS NOW** | `src/hnradar/pulse/` | PR #49 (Issue #13); Rule 7 |
| **5-Line Outreach Draft (Top 10)** | **WORKS NOW** | `src/hnradar/draft/` | PR #51 (Issue #14); Rules 1, 2, 4 |
| **Parser Regression Skill** | **WORKS NOW** | `.claude/skills/verify-jobs-parse/` | PR #48; Quality Gate |
| **Careers Web Pages (Static)** | **IN PROGRESS (Branch Stack)** | `site/careers/` (on branch `feat/site-careers`) | PR #42 (OPEN against `main`) |
| **Careers Pagefind Search Index** | **IN PROGRESS (Branch Stack)** | `site/tools/build_careers_index.py` | PR #43 (MERGED into `feat/site-careers`) |
| **Company Detail Pages** | **IN PROGRESS (Branch Stack)** | `site/careers/company.html` | PR #44 (OPEN against `feat/site-careers`) |
| **Pre-Flight URL Reputation Checker** | **PLANNED (Issue #27)** | Not yet started | Issue #27 (Open); Rule 4 |
| **Autonomous Multi-Agent Fleet** | **HISTORICAL EXPERIMENT** | `scripts/agent-poll.ps1` (ran on PR #9 only) | Manual pair-programming remains current engine |

## 6. Summary

The HN Radar architecture achieves high reliability and deterministic behavior through strict decoupling:
1. **Source Adapters** isolate network I/O, rate limiting, and resilient on-disk caching (PR #53).
2. **Pure Domain Functions** (`parse.py`, `match.py`, `fingerprint.py`, `showhn.py`, `closed.py`) operate without side effects or network calls.
3. **Pydantic Validation Models** enforce boundary constraints across CLI inputs, API payloads, and LLM outputs (`ModelReply`, `ModelDraft`).
4. **Outreach Draft Generation** (`hnradar draft` / PR #51) synthesizes company matches, Show HN bugs, and developer repos into cited outreach notes without false claims of ownership (PR #50 / Rule 9).
5. **The Autonomous Factory & Qodo Quality Gate** ensure that every modification is accompanied by edge-case tests, loud limits, and architectural verification.
