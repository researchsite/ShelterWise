# Retrieval and evidence rules

## Retrieval philosophy

The system must prefer explainable, source-backed evidence over a fluent but unsupported answer. Similarity is a discovery signal, not proof.

## Recommended pipeline

1. Parse issue and geographic scope from the reviewed intake.
2. Apply mandatory filters: correct metro, relevant residential/property category, appropriate time window, and status rules required by the use case.
3. Generate embeddings for the query and eligible records using the challenge-approved embedding path (the planning notes mention `AI.EMBED` and `VECTOR_SEARCH`; verify exact syntax and availability).
4. Retrieve candidates.
5. Validate candidates against structured fields and remove duplicates.
6. Rank using transparent signals: issue match, geography, recency, status, and source reliability.
7. Return top records plus exclusions and limitations.

## Exclusion and decoy handling

The challenge discussion highlighted planted decoys. Build explicit tests for all decoy classes supplied by the challenge data. Common exclusion reasons may include:
- commercial rather than residential;
- closed or stale record when open/current is required;
- wrong geography;
- unrelated issue category;
- duplicate record;
- unsupported or malformed location.

Do not hardcode a hidden audit field or decoy label into the runtime ranking logic. Use legitimate source attributes and documented business rules. Do not use `audit_*` fields in retrieval, ranking, or user-facing explanations.

## Evidence labels

- **Tenant-reported:** stated by the tenant; not independently verified.
- **Public-record match:** public record that matches selected criteria; may refer to a nearby property or broader area.
- **Official legal/program source:** official published rule or program information; applicability still requires review.
- **Contextual statistic:** aggregate geography-level data; not evidence about an individual.
- **Not found:** no matching record returned; does not mean no issue exists.
- **Needs verification:** uncertain, stale, conflicting, or incomplete.

## Required explanation for each result

- Why it was included.
- Which fields matched.
- Source and date.
- Geography precision.
- What it does and does not establish.
- Any reason for reduced confidence.

## Evaluation metrics

- Precision among top retrieved records.
- Recall on challenge-provided relevant records.
- Decoy rejection rate by decoy type.
- Citation completeness.
- Percentage of claims correctly labeled as reported vs public evidence.
- Unsupported inference rate.
