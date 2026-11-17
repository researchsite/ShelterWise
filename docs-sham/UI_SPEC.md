# UI specification

## Product surface

Build a case workspace, not a generic chat window.

## Main screen layout

1. **Header:** ShelterWise, selected metro, privacy/help link.
2. **Case intake panel:** narrative field and a small set of optional structured questions.
3. **Case summary:** extracted facts with edit controls and reported/unknown labels.
4. **Evidence panel:** public-record cards with source, date, status, match rationale, geography, and limitation.
5. **Rights & resources panel:** legal/program cards with jurisdiction, source, eligibility caveat, and last-checked date.
6. **Evidence gaps panel:** missing items and safe next steps.
7. **Brief preview:** generated brief with citations and human-review banner.

## UX rules

- Show a sample case/demo mode before requiring account creation.
- Keep the demo path to a few clicks.
- Provide clear progress and useful empty states.
- Make it easy to edit extracted facts.
- Do not bury citations behind multiple clicks.
- Use plain language and readable typography.
- Provide a clear reset/new-case action; if authentication exists, provide logout.
- Do not show invented live status. Clearly label sample data.
- Avoid color-only meaning; pair status colors with text labels.
- Ensure keyboard navigation and responsive layout.

## Suggested components

- `CaseIntakeForm`
- `ExtractedFactsReview`
- `EvidenceResultCard`
- `LegalResourceCard`
- `EvidenceGapList`
- `StabilizationBriefPreview`
- `HumanReviewBanner`
