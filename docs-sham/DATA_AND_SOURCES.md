# Data and source plan

## Source hierarchy

1. Official city/county open-data portals for 311, building inspections, code violations, and housing complaints.
2. Official court or government sources for eviction process and public aggregate filing data.
3. Census / ACS for aggregate housing, rent burden, and renter context.
4. Official housing authority and government program pages for rental assistance and stabilization resources.
5. Reputable nonprofit/legal-aid sources as supplementary plain-language explanations, clearly labeled.

## Data inventory to confirm

For each source, record:
- publisher and dataset name;
- official URL and license/terms;
- geography and coverage period;
- refresh cadence and last updated date;
- primary key and available location fields;
- issue/category and status fields;
- whether records are complaints, inspections, violations, or outcomes;
- known missingness and limitations.

## Suggested initial metro

Chicago was the initial recommendation because the planning discussion identified meaningful public 311 volume and renter/eviction context. This is a planning choice, not a verified current data-quality claim. Reconfirm data availability and challenge scoring requirements before locking it. Baton Rouge may be useful for demonstrating how low complaint counts can reflect reporting/access gaps, but it can be harder to show direct evidence. San Francisco was also identified as an alternative.

## Data quality rules

- Preserve Census GEOIDs as strings, including leading zeros.
- Normalize dates to a documented timezone and retain source timestamps.
- Preserve original source IDs and raw source values.
- Keep complaint, inspection, violation, and adjudicated outcome concepts distinct.
- Do not join quarterly eviction records to multiple fact rows before aggregation; aggregate to the intended grain first to avoid multiplying counts.
- Deduplicate only with documented rules.
- Label modeled eviction estimates as modeled; do not present them as observed individual filings.
- Track missing, null, stale, and suppressed values explicitly.

## Privacy

Minimize personally identifying data. Do not ingest tenant names, phone numbers, or free-text details from public datasets unless clearly necessary and permitted. Restrict access to case narratives. Use synthetic data only when labeled as synthetic.

## Data dictionary template

| Field | Meaning | Type | Source | Notes |
|---|---|---|---|---|
| `source_record_id` | Original record key | STRING | City portal | Preserve exactly |
| `metro` | Selected metro | STRING | App | Controlled vocabulary |
| `issue_category` | Normalized issue | STRING | Derived | Keep source category too |
| `record_status` | Open/closed/etc. | STRING | Source | Do not infer |
| `created_at` | Original creation date | TIMESTAMP | Source | Retain timezone |
| `latitude`, `longitude` | Approximate location | FLOAT | Source | Apply privacy rules |
| `geoid` | Census geography ID | STRING | Census | Preserve leading zeros |
| `source_url` | Record/source URL | STRING | Source | Required for citation |
