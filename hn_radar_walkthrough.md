# Walkthrough — HN Radar Architecture & User Documentation

We have thoroughly analyzed all **23 closed pull requests** and their corresponding **Qodo Code Review Mermaid diagrams** from [researchsite/hn-radar](https://github.com/researchsite/hn-radar), as well as the complete underlying codebase.

We have produced three complete, high-quality deliverables:

1. **Interactive Architecture HTML Component** ([`hn_radar_architecture.html`](file:///config/Desktop/AgentsForImpact/hn_radar_architecture.html))
2. **Comprehensive Architecture Diagram Specification** ([`hn_radar_architecture_diagram.md`](file:///config/Desktop/AgentsForImpact/hn_radar_architecture_diagram.md))
3. **Comprehensive User & Operator Document** ([`hn_radar_user_document.md`](file:///config/Desktop/AgentsForImpact/hn_radar_user_document.md))

---

## 1. Interactive Architecture HTML Component

**File:** [`hn_radar_architecture.html`](file:///config/Desktop/AgentsForImpact/hn_radar_architecture.html) (112 KB self-contained HTML/CSS/JS)

### Key Features:
- **Interactive SVG Architecture Map:**
  - Visual layout covering External Services, Source Adapters, Storage/Cache, Processing Engines, CLI Commands, Security Boundaries, and Autonomous Factory.
  - Hover highlights and real-time category filtering (CLI, Ingestion, Adapters, Scoring, Pulse, Autonomous Factory).
  - Component search box for instant discovery.
- **Click-to-Explain Slide-Over Drawer:**
  - Clicking any node opens a rich panel with:
    - **Overview:** Functional breakdown, inputs, outputs, schemas.
    - **Live Qodo Mermaid Diagram:** Rendered dynamically using Mermaid.js from the exact PR that introduced or modified the component.
    - **Rules & Specs:** Source file paths, governing `AGENTS.md` rules, and related PR badges.
- **Pull Request Evolution Timeline:**
  - Dedicated tab displaying all **23 closed PRs** (#1 through #49) in chronological sequence.
  - Shows PR title, merge/experiment status, architectural contribution, and the original Qodo review Mermaid diagram for each PR.
- **Subsystems Breakdown & AGENTS.md Governance Matrix:**
  - Quick-navigation cards for the 8 core subsystems and a 10-rule verification matrix with enforcing files.

---

## 2. Architecture Diagram Specification

**File:** [`hn_radar_architecture_diagram.md`](file:///config/Desktop/AgentsForImpact/hn_radar_architecture_diagram.md) (31 KB Markdown)

### Included Diagrams & Analyses:
1. **Unified End-to-End System Architecture (Mermaid Graph):**
   - Synthesizes all 23 PRs into a single cohesive system map showing data flow across APIs, disk cache, parsing, matching, LLM pulse, CLI, and the autonomous factory.
2. **Subsystem Deep Dives:**
   - **Job Ingestion & Pre-processing Pipeline:** Sequence diagram showing Algolia query, atomic caching, comment parsing, candidate filtering, closed job detection, and terminal sanitization.
   - **Developer Fingerprinting & Deterministic Match Pipeline:** Flowchart detailing fork filtering, byte-weighted language calculation, topic aggregation, alias normalization, and point scoring.
   - **Show HN & Sentiment Pulse Intelligence Pipeline:** Sequence diagram showing length-sorted comment harvesting, local Ollama prompting (`qwen2.5:7b`), Pydantic schema validation, and comment ID citation verification.
   - **Autonomous Engineering Factory & Quality Gate:** State machine diagram illustrating PowerShell mutex polling (`Global\HNRadarAgentPoll`), Goose ticket worker execution in isolated worktrees, Qodo review bot triage, and Definition of Done gates.
3. **Complete Catalog of 23 Qodo Review Diagrams:**
   - Full Mermaid source code and architectural commentary for PRs #1, #2, #6, #7, #8, #9, #10, #11, #21, #22, #24, #28, #29, #30, #33, #34, #35, #36, #39, #43, #46, #48, and #49.

---

## 3. Comprehensive User Document

**File:** [`hn_radar_user_document.md`](file:///config/Desktop/AgentsForImpact/hn_radar_user_document.md) (20 KB Markdown)

### Contents:
- **Mission Statement:** Explains the core philosophy of *"Arrive with the fix"*.
- **Setup & Prerequisites:** Installation with `uv` and `pip`, Python 3.13 configuration, optional `GITHUB_TOKEN` rate-limit boost, and Ollama setup.
- **Detailed Command Reference:** Full usage, arguments, options, and realistic output examples for:
  1. `hnradar fetch-hiring` (with candidate filtering and closed job detection)
  2. `hnradar fingerprint` (with fork exclusion and 2000-repo loud limit)
  3. `hnradar match` (with deterministic points and cited reasons)
  4. `hnradar showhn` (with URL-restricted query and domain validation)
  5. `hnradar pulse` (with local Ollama sentiment clustering)
- **End-to-End Walkthrough:** Practical 6-step scenario demonstrating how a developer discovers a role, extracts a critical Show HN bug, and sends an outreach email with the fix already built.
- **Governance & Autonomous Operations:** Practical guide to the 10 `AGENTS.md` rules, ticket worker poller, and `verify-jobs-parse` regression testing.
- **Troubleshooting Guide & FAQ:** Solutions for common errors (API limits, missing profiles, Ollama connectivity).
