# ShelterWise: Hualin's version

**Separate from teammates' work on purpose:**

| Where | Ours | Shared / teammates' (we don't touch) |
|---|---|---|
| Repo | `hualin/` (code), `docs/hualin/` (design) | `agent/`, `docs/`, `mockup/`, other branches |
| Python package / ADK app | `shelterwise_hualin` | anything else |
| BigQuery writes | dataset `hualin_shelterwise` only | `a4i_housing` (we only **read** its source tables) |
| Deployments | names prefixed `hualin-shelterwise-` | everything else |


Design: [`docs/hualin/ARCHITECTURE.md`](../docs/hualin/ARCHITECTURE.md).

Layout (`hualin/agent/`):

```
shelterwise_hualin/
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
cd hualin/agent
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q tests
```

## Run the agent

```bash
cp shelterwise_hualin/.env.example shelterwise_hualin/.env   # fill in project; SHELTERWISE_DATA=bigquery for the demo
gcloud auth application-default login           # or run in Cloud Shell
.venv/bin/adk web .                             # open http://localhost:8000, pick "shelterwise_hualin"
```

Before `SHELTERWISE_DATA=bigquery` works: the shared `a4i_housing` tables must be loaded (data lane,
`scripts/load.sh san-francisco`) and the `us.a4i-vertex` connection must exist. Then run our own setup,
which writes only to `hualin_shelterwise`:

```bash
bq query --use_legacy_sql=false < hualin/sql/setup.sql
```

`SHELTERWISE_DATA=local` runs everything from the repo's `data/*.parquet` with a keyword stand-in for vector search.
It is for offline development only, and every brief says so.


## Deploy to Agent Runtime (live)

```bash
bash hualin/deploy_agent_runtime.sh            # first run creates, later runs update the same instance
hualin/agent/.venv/bin/python hualin/query_remote.py "intake text" "follow-up"
```

- Region `us-central1`, display name `hualin-shelterwise-navigator`.
- Runs as service account `hualin-shelterwise-agent@<project>` with: aiplatform.user, bigquery.jobUser,
  bigquery.dataViewer, bigquery.connectionUser, mcp.toolUser, serviceusage.serviceUsageConsumer,
  logging.logWriter, monitoring.metricWriter, cloudtrace.agent.
- The instance ID is saved locally in `hualin/.agent_runtime_id` (git-ignored).
