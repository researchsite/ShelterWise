# ShelterWise agent

Design: [`docs/hualin/ARCHITECTURE.md`](../docs/hualin/ARCHITECTURE.md).

```
shelterwise/
  agent.py         root_agent = shelterwise_navigator (chat)
  pipeline.py      brief_pipeline: parse → prepare → gather ∥ → decide ∥ → write ⇄ verify
  llm_agents.py    intake_parser, brief_writer, inspection_request_drafter
  code_agents.py   intake_prep, evidence, context, legal, relief, verifier (no LLM)
  tools/           evidence ★ (custom tool), geocode, safety, pii, tract, legal, relief, brief, explain, mcp
  rules/           funds_sf.yaml, statutes_sf.yaml   ← eligibility rules, edit here
  data.py          BigQuery or local parquet; never selects audit_* columns
tests/             pytest: decoys, fan-out, GEOIDs, clocks, fund verdicts, verifier, ADK wiring
```

## Run the tests (offline, no GCP needed)

```bash
cd agent
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q tests
```

## Run the agent

```bash
cp shelterwise/.env.example shelterwise/.env   # fill in project; SHELTERWISE_DATA=bigquery for the demo
gcloud auth application-default login           # or run in Cloud Shell
.venv/bin/adk web .                             # open http://localhost:8000, pick "shelterwise"
```

Before `SHELTERWISE_DATA=bigquery` works, the data lane must run `scripts/load.sh san-francisco`,
create the `us.a4i-vertex` connection, and run [`sql/setup.sql`](../sql/setup.sql).

`SHELTERWISE_DATA=local` runs everything from `data/*.parquet` with a keyword stand-in for vector search.
It is for offline development only, and every brief says so.

---

## Challenge requirements (original starter README)



We built the on-ramp: real American Community Survey housing tenure counts, 100-block municipal 311 complaint narratives across six metros, modeled quarterly eviction baselines, public statutes and emergency rental relief bulletins, and a validation suite that tells you plainly whether any of it is wrong. We did not build the vehicle. The design decisions in your agent are what you will be judged on.

### What has to be true of what you build here

- **An ADK agent**, in Python.
- **At least one tool you built yourself.** A Python function tool or one you defined in MCP Toolbox both count. The obvious candidate wraps your semantic search query, while the more valuable one holds the logic that is not a single query: turning a tenant intake narrative into a targeted search string, enforcing residential and open-case eligibility rules, cross-checking statutory protections, and assembling the Tenant Stabilization Brief. Consuming only prebuilt generic tools and calling that your design does not count.
- **At least one Google-managed MCP server, consumed.** Do not author your own from scratch. Use BigQuery's built-in MCP server or the [MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox).
- **Deployed to Google Cloud**, on Agent Runtime or Cloud Run (your choice).
- **Your required differentiator: BigQuery Vector Search.** Your agent must genuinely call semantic search (`AI.EMBED` + `VECTOR_SEARCH`) over complaint narratives or relief bulletins. Filtering on categories or `LIKE '%no heat%'` does not count, and it is the most common way a team misses the point while appearing to hit it.

### The thing worth remembering while you build

Vector search is a **candidate generator, not an answer**. Every metro in your corpus contains nine planted near-miss decoys (`DECOY-*`): commercial warehouses with broken heaters, closed historical mold repairs, and proactive clearance inspections that semantically resemble an active crisis. What you do *after* the search (enforcing `property_type = 'Residential'`, checking `closed_date IS NULL`, matching program rules in `rental_relief_program_bulletins`, and avoiding the 4x quarterly join inflation on `court_eviction_filings`) is where this agent becomes useful instead of merely clever.

See Section 13 of [`notebooks/c_housing_01_load_explore.ipynb`](../notebooks/c_housing_01_load_explore.ipynb) for the connection setup, query shape, and syntax rules.
