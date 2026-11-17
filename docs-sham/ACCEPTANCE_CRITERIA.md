# Acceptance criteria

## End-to-end
- [ ] User can enter a case narrative and select a jurisdiction.
- [ ] Extracted facts are reviewable and editable.
- [ ] User can trigger evidence search.
- [ ] Evidence results show source, date, geography, status, and rationale.
- [ ] Legal/resource results link to official sources and include caveats.
- [ ] Evidence gaps are displayed when evidence is absent or incomplete.
- [ ] Brief can be generated and viewed.

## Evidence quality
- [ ] Residential relevance is enforced using legitimate fields.
- [ ] Wrong-metro records are excluded.
- [ ] Stale/closed records are handled according to documented rules.
- [ ] All challenge-provided decoy categories are tested.
- [ ] No `audit_*` field is used in runtime retrieval or ranking.
- [ ] Public records are not presented as proof of unit-level conditions.
- [ ] GEOIDs remain strings; leading zeros are preserved.
- [ ] Eviction counts are aggregated at the intended grain before joins.

## Legal and safety
- [ ] No definitive legal advice or guaranteed eligibility language.
- [ ] Official sources and jurisdiction are visible.
- [ ] Deadlines and urgent risks are flagged for human review.
- [ ] Immediate danger guidance does not wait for full intake.
- [ ] Protected traits are not used for individual ranking or eligibility.
- [ ] Aggregate equity context is caveated and non-stigmatizing.

## UX and demo
- [ ] Sample/demo mode is available.
- [ ] Empty states are useful.
- [ ] Citations are easy to inspect.
- [ ] New case/reset path is clear.
- [ ] Demo can be completed reliably in under four minutes.
