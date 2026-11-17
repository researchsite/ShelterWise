-- ShelterWise one-time BigQuery setup. Run after `bash scripts/load.sh san-francisco`
-- and after creating the `us.a4i-vertex` CLOUD_RESOURCE connection (notebook Section 13, Step A).
-- Replace a4i_housing if you changed the dataset.

-- 1. Embeddings, materialized once. The agent joins back to municipal_311_housing_complaints
--    on request_id for every other field (lat/lng, dates, citations).
CREATE OR REPLACE TABLE `a4i_housing.complaints_embedded` AS
SELECT request_id, metro_area, embedded.result AS embedding
FROM (
  SELECT request_id, metro_area,
    AI.EMBED(complaint_narrative, connection_id => 'us.a4i-vertex', endpoint => 'gemini-embedding-2') AS embedded
  FROM `a4i_housing.municipal_311_housing_complaints`
)
WHERE embedded.status = '';

-- Sanity check: every complaint embedded (expect 0 missing).
SELECT COUNT(*) AS missing_embeddings
FROM `a4i_housing.municipal_311_housing_complaints` c
LEFT JOIN `a4i_housing.complaints_embedded` e USING (request_id)
WHERE e.request_id IS NULL;

-- 2. Fan-out-safe tract view (idea from Shiva's design). 4 quarters summed BEFORE the join;
--    NO audit_* columns. For the deck and the BigQuery MCP; the agent computes the same in Python.
CREATE OR REPLACE VIEW `a4i_housing.v_tract_stability_context` AS
WITH annual_filings AS (
  SELECT census_tract_geoid,
    COUNT(*) AS quarters,
    SUM(nonpayment_filings_count) AS annual_nonpayment_modeled,
    SUM(holdover_or_no_fault_filings_count) AS annual_no_fault_modeled,
    SUM(nonpayment_filings_count + holdover_or_no_fault_filings_count) AS annual_filings_modeled
  FROM `a4i_housing.court_eviction_filings`
  GROUP BY census_tract_geoid
),
open_res_311 AS (
  SELECT census_tract_geoid, COUNT(*) AS open_residential_311
  FROM `a4i_housing.municipal_311_housing_complaints`
  WHERE property_type = 'Residential' AND closed_date IS NULL
  GROUP BY census_tract_geoid
)
SELECT a.census_tract_geoid, a.metro_area, a.renter_occupied_units, a.renter_hh_rent_50_pct_plus_count,
  ROUND(100 * SAFE_DIVIDE(a.renter_hh_rent_50_pct_plus_count, a.renter_occupied_units), 1) AS severe_rent_burden_pct,
  a.median_household_income, a.median_gross_rent, a.no_vehicle_rate,
  f.quarters, f.annual_nonpayment_modeled, f.annual_no_fault_modeled, f.annual_filings_modeled,
  COALESCE(c.open_residential_311, 0) AS open_residential_311
FROM `a4i_housing.acs_tract_housing_tenure` a
LEFT JOIN annual_filings f USING (census_tract_geoid)
LEFT JOIN open_res_311 c USING (census_tract_geoid);

-- 3. Checks for the Rigor slide.
-- GEOIDs are STRING with the leading zero (expect STRING / 11 / 0 bad rows):
SELECT data_type FROM `a4i_housing.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'acs_tract_housing_tenure' AND column_name = 'census_tract_geoid';
SELECT COUNTIF(LENGTH(census_tract_geoid) != 11) AS bad_geoids FROM `a4i_housing.acs_tract_housing_tenure`;
-- No 4x fan-out (expect quarters = 4 everywhere; SF total 2359):
SELECT MIN(quarters), MAX(quarters), SUM(annual_filings_modeled) FROM `a4i_housing.v_tract_stability_context`;
