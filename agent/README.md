# Your agent goes here

This folder is empty on purpose.

We built the on-ramp: real American Community Survey housing tenure counts, 100-block municipal 311 complaint narratives across six metros, modeled quarterly eviction baselines, public statutes and emergency rental relief bulletins, and a validation suite that tells you plainly whether any of it is wrong. We did not build the vehicle. The design decisions in your agent are what you will be judged on.

## What has to be true of what you build here

- **An ADK agent**, in Python.
- **At least one tool you built yourself.** A Python function tool or one you defined in MCP Toolbox both count. The obvious candidate wraps your semantic search query, while the more valuable one holds the logic that is not a single query: turning a tenant intake narrative into a targeted search string, enforcing residential and open-case eligibility rules, cross-checking statutory protections, and assembling the Tenant Stabilization Brief. Consuming only prebuilt generic tools and calling that your design does not count.
- **At least one Google-managed MCP server, consumed.** Do not author your own from scratch. Use BigQuery's built-in MCP server or the [MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox).
- **Deployed to Google Cloud**, on Agent Runtime or Cloud Run (your choice).
- **Your required differentiator: BigQuery Vector Search.** Your agent must genuinely call semantic search (`AI.EMBED` + `VECTOR_SEARCH`) over complaint narratives or relief bulletins. Filtering on categories or `LIKE '%no heat%'` does not count, and it is the most common way a team misses the point while appearing to hit it.

## The thing worth remembering while you build

Vector search is a **candidate generator, not an answer**. Every metro in your corpus contains nine planted near-miss decoys (`DECOY-*`): commercial warehouses with broken heaters, closed historical mold repairs, and proactive clearance inspections that semantically resemble an active crisis. What you do *after* the search (enforcing `property_type = 'Residential'`, checking `closed_date IS NULL`, matching program rules in `rental_relief_program_bulletins`, and avoiding the 4x quarterly join inflation on `court_eviction_filings`) is where this agent becomes useful instead of merely clever.

See Section 13 of [`notebooks/c_housing_01_load_explore.ipynb`](../notebooks/c_housing_01_load_explore.ipynb) for the connection setup, query shape, and syntax rules.
