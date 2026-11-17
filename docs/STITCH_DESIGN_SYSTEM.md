# 🎨 Google Stitch Design System: Stitch-Civic (ShelterWise)

**Version**: 2.0  
**Design Philosophy**: "Civic Warmth & Judicial Rigor"  
**Target Audience**: Tenants under acute eviction stress, legal aid paralegals, housing attorneys, and civic evaluators.

---

## 1. Design Tokens Specification

### Color Tokens
```css
:root {
  /* Brand & Intent */
  --stitch-brand-primary: #1A73E8;       /* Trust Blue (Google Civic Blue) */
  --stitch-brand-navy: #0F172A;          /* Deep Court Navy */
  --stitch-brand-soft: #E8F0FE;          /* Soft Ice Blue Accent */
  --stitch-brand-border: #BFDBFE;        /* Subtle Border Blue */

  /* Emotional & Legal States */
  --stitch-relief-green: #188038;        /* Financial Relief / Corroborated */
  --stitch-relief-soft: #E6F4EA;         /* Soft Grant Background */
  --stitch-alert-crimson: #D93025;       /* Acute Hazard / Life Safety */
  --stitch-alert-soft: #FCE8E6;          /* Danger Warning Tint */
  --stitch-clock-amber: #F29900;         /* 35-Day Repair Clock Warning */
  --stitch-clock-soft: #FEF7E0;          /* Warning Tint */
  --stitch-trust-purple: #7C3AED;        /* AI Insights & Reasoning */
  --stitch-trust-soft: #F3E8FD;          /* Soft Purple Accent */

  /* Neutral Surfaces */
  --stitch-surface-ground: #F8F9FA;      /* Canvas Surface */
  --stitch-surface-card: #FFFFFF;        /* Elevated Card Surface */
  --stitch-surface-subtle: #F1F3F4;      /* Input & Table Header Gray */
  --stitch-ink-primary: #202124;         /* High-contrast Readability Ink */
  --stitch-ink-secondary: #5F6368;       /* Supporting Label Gray */
  --stitch-ink-muted: #80868B;           /* Placeholders & Muted Notes */
  --stitch-border-line: #DADCE0;         /* Clean Card Borders */

  /* Elevation Shadows */
  --stitch-shadow-sm: 0 1px 3px rgba(60,64,67,0.12), 0 1px 2px rgba(60,64,67,0.08);
  --stitch-shadow-card: 0 4px 12px rgba(60,64,67,0.08), 0 1px 3px rgba(60,64,67,0.05);
  --stitch-shadow-hover: 0 8px 24px rgba(60,64,67,0.14), 0 2px 6px rgba(60,64,67,0.08);

  /* Radii */
  --stitch-radius-sm: 6px;
  --stitch-radius-md: 12px;
  --stitch-radius-lg: 18px;
  --stitch-radius-pill: 999px;
}

/* Trauma-Informed Distress Mode */
body.distress-mode {
  --stitch-surface-ground: #000000;
  --stitch-surface-card: #121212;
  --stitch-ink-primary: #FFFFFF;
  --stitch-ink-secondary: #E0E0E0;
  --stitch-border-line: #333333;
  --stitch-brand-primary: #8AB4F8;
  --stitch-relief-green: #81C995;
  --stitch-alert-crimson: #F28B82;
  --stitch-clock-amber: #FDD663;
  font-size: 17px;
  line-height: 1.7;
}
```

---

## 2. Component Taxonomy (24 Components across 5 Tiers)

```
stitch/
├── tokens/
│   ├── colors.css
│   ├── typography.css
│   └── elevation.css
├── atoms/
│   ├── StitchBadge.js / .css
│   ├── StitchButton.js / .css
│   ├── StitchInput.js / .css
│   ├── StitchTooltip.js / .css
│   └── StitchAvatar.js / .css
├── molecules/
│   ├── DistressModeBanner.js
│   ├── HabitabilityClockPill.js
│   ├── DecoyRejectionCard.js
│   ├── ReliefFundingMeter.js
│   ├── VoiceInputPill.js
│   ├── GeoProximityRadar.js
│   ├── ScenarioCard.js
│   ├── StepStepper.js
│   └── AttorneyChecklistPill.js
├── organisms/
│   ├── UniversalHeader.js
│   ├── IntakeWorkbench.js
│   ├── FactsMatrix.js
│   ├── EvidentiaryMapCanvas.js
│   ├── ReliefReconciliationPanel.js
│   ├── BriefPreviewCard.js
│   ├── AgentStudioGrid.js
│   └── EquityAuditMatrix.js
└── templates/
    ├── DefenseWorkspaceTemplate.html
    ├── AgentStudioTemplate.html
    └── CourtBriefPrintTemplate.html
```

---

## 3. Creative Component Innovations

### 1. `HabitabilityClockPill` (35-Day Statutory Repair Window)
- **Problem**: Under California Civil Code § 1942.4, landlords who receive a notice of habitability violation from a municipal inspector and fail to fix it within 35 days without good cause cannot collect rent or initiate an eviction.
- **Component**: A circular progress dial displaying:
  - Total elapsed days since initial 311 complaint.
  - Green status if under 35 days; bright amber/red alert if >= 35 days.
  - Plain-English statutory notice: *"Day 42 of 35 statutory window. Landlord repair clock expired on Day 35. Eviction action is barred under Cal. Civ. Code § 1942.4."*

### 2. `ReliefFundingMeter` (Interactive Back-Rent Gap Calculator)
- **Problem**: Rent arrears numbers confuse tenants facing court hearings.
- **Component**: A visual arithmetic gauge:
  - `[ Rent Arrears: $4,200 ]`
  - `[ - SF ERAP Grant: $3,500 ]`
  - `[ - MEDA Emergency Assistance: $700 ]`
  - `[ = Remaining Gap: $0.00 (100% Covered!) ]`
  - Includes a one-click *"Submit Emergency Relief Application"* action.

### 3. `DecoyRejectionCard` (Plain-English Filter Explainer)
- **Problem**: Advocates and judges need to understand why nearby search hits were discarded.
- **Component**: A clear rejection card:
  - Icon: `🚫 Decoy Excluded`
  - Case: `DECOY-SANF-COMM-01`
  - Address: `1008 Fillmore St (2 doors down)`
  - Rejection Reason: *"Excluded: Commercial Laundromat. Municipal records confirm this citation belongs to a commercial business, not residential housing. It cannot be used as tenant defense evidence."*

### 4. `GeoProximityRadar` (Civic Geospatial Micro-Badge)
- **Component**: Visual micro-radar card showing:
  - Evidentiary radius: `400-meter municipal boundary`
  - Closest match: `12 meters from tenant entrance`
  - Transit to Court: `22 minutes to SF Superior Court via MUNI Route 31`
  - Next Departure: `Leaves Fillmore & Geary in 4 min`

### 5. `DistressModeBanner` (Trauma-Informed Emergency Mode)
- **Component**: High-contrast, top-fixed ribbon:
  - *"Urgent Court Hearing within 48 Hours? Free legal aid is waiting for you right now."*
  - Direct dial: `Call SF Eviction Defense Collaborative: (415) 555-EVIC`
  - Button: `Switch to Low-Distraction High-Contrast Mode`

---

## 4. Plain-English Technical Translation Guide

| Technical Jargon | Plain-English Term | How We Explain It in the UI |
| :--- | :--- | :--- |
| **BigQuery `AI.EMBED` + `VECTOR_SEARCH`** | **The City Hall Record Matcher** | "Our system reads through thousands of San Francisco City Hall records in 2 seconds to find official government proof of housing code violations on your block." |
| **Decoy Rejection Rules** | **The False Lead Filter** | "We automatically filter out misleading records—like a broken pipe at a nearby laundromat or a repair that was completed years ago—so only genuine residential evidence is shown to the judge." |
| **Multi-Agent ADK Pipeline (`*_ag`)** | **Your AI Legal Support Team** | "A coordinated team of AI assistants acting like a legal aid office: intake interviewer, city records researcher, housing code specialist, neighborhood data analyst, and court brief drafter." |
| **Firestore Transactional Locks** | **The Collaborator Shield** | "Protects the case record so that if a tenant and their attorney are working at the same time, neither person accidentally overwrites the other's notes." |
| **Responsible AI Demographic Firewall** | **The Fairness Firewall** | "Personal demographic details (race, age, language) are locked behind a secure firewall. They can never be used to judge your individual case, but only help the city check which neighborhoods need more funding." |
| **California Civil Code § 1942.4** | **The Landlord Repair Deadline Law** | "If your landlord was told to fix serious housing problems and did not fix them within 35 days, California law bars them from demanding rent or evicting you." |
| **Unlawful Detainer** | **Eviction Court Lawsuit** | "The official legal name for an eviction lawsuit filed by a landlord in California court." |
| **Affirmative Defense** | **Your Legal Shield** | "A legally recognized reason why a landlord cannot evict you, such as failing to provide heating or safe water." |
