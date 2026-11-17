-- Hualin's ShelterWise version: one-time BigQuery setup.
--
-- SEPARATION: reads the team's shared source tables in `a4i_housing` (read only) and
-- writes ONLY to our own dataset `hualin_shelterwise`. Never creates or replaces
-- anything in a4i_housing, so teammates' tables and views are untouched.
--
-- Run:  bq query --use_legacy_sql=false < hualin/sql/setup.sql

CREATE SCHEMA IF NOT EXISTS `hualin_shelterwise` OPTIONS (location = 'US',
  description = "Hualin's ShelterWise version (embeddings + views). Team source data stays in a4i_housing.");

-- 1. Our own embeddings (174 SF rows, pennies). The agent joins back to
--    a4i_housing.municipal_311_housing_complaints on request_id for every other field.
CREATE OR REPLACE TABLE `hualin_shelterwise.complaints_embedded` AS
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
LEFT JOIN `hualin_shelterwise.complaints_embedded` e USING (request_id)
WHERE e.request_id IS NULL;

-- 2. Fan-out-safe tract view (idea from Shiva's design). 4 quarters summed BEFORE the join;
--    NO audit_* columns.
CREATE OR REPLACE VIEW `hualin_shelterwise.v_tract_stability_context` AS
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
SELECT COUNTIF(LENGTH(census_tract_geoid) != 11) AS bad_geoids FROM `a4i_housing.acs_tract_housing_tenure`;
SELECT MIN(quarters) AS min_q, MAX(quarters) AS max_q, SUM(annual_filings_modeled) AS sf_total
FROM `hualin_shelterwise.v_tract_stability_context`;  -- expect 4, 4, 2359
