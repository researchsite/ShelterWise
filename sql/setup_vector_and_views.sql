-- ==============================================================================
-- ShelterWise — BigQuery Vector Table & Fan-Out-Safe View Setup
-- Agents for Impact 2026: Affordable Housing Stability & Eviction Prevention
-- Default Metro: San Francisco, CA (state_fips: '06')
-- ==============================================================================

-- 1. Materialize 311 embeddings once using Vertex AI connection us.a4i-vertex
-- Uses gemini-embedding-2 via CLOUD_RESOURCE connection
CREATE OR REPLACE TABLE `a4i_housing.complaints_embedded` AS
SELECT
  request_id,
  state_code,
  metro_area,
  LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
  block_address,
  property_type,
  raw_complaint_type,
  inspection_status,
  closed_date,
  complaint_narrative,
  embedded.result AS embedding
FROM (
  SELECT *,
    AI.EMBED(
      complaint_narrative,
      connection_id => 'us.a4i-vertex',
      endpoint => 'gemini-embedding-2'
    ) AS embedded
  FROM `a4i_housing.municipal_311_housing_complaints`
)
WHERE embedded.status = '';

-- 2. Fan-out-safe Tract Stability View
-- Pre-aggregates 4 quarters of eviction filings to prevent 4x join inflation
-- Structurally excludes all audit_* columns (Responsible AI firewall)
CREATE OR REPLACE VIEW `a4i_housing.v_tract_stability_context` AS
WITH annual_filings AS (
  SELECT
    LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
    SUM(nonpayment_filings_count) AS annual_nonpayment_filings,
    SUM(holdover_or_no_fault_filings_count) AS annual_no_fault_filings,
    SUM(nonpayment_filings_count + holdover_or_no_fault_filings_count) AS annual_filings_total,
    SUM(default_judgments_count) AS annual_defaults_total,
    ROUND(AVG(median_claimed_arrears_usd), 0) AS avg_claimed_arrears_usd,
    ANY_VALUE(data_provenance) AS filings_provenance
  FROM `a4i_housing.court_eviction_filings`
  GROUP BY 1
),
open_res_311 AS (
  SELECT
    LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
    COUNT(*) AS open_residential_311_count
  FROM `a4i_housing.municipal_311_housing_complaints`
  WHERE property_type = 'Residential'
    AND closed_date IS NULL
    AND NOT STARTS_WITH(LOWER(inspection_status), 'closed')
  GROUP BY 1
)
SELECT
  LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
  a.state_code,
  a.metro_area,
  a.county_name,
  a.renter_occupied_units,
  a.median_household_income,
  a.median_gross_rent,
  a.renter_hh_rent_30_to_49_pct_count,
  a.renter_hh_rent_50_pct_plus_count,
  ROUND(SAFE_DIVIDE(a.renter_hh_rent_50_pct_plus_count, a.renter_occupied_units) * 100, 1) AS severe_rent_burden_pct,
  ROUND(a.poverty_rate * 100, 1) AS poverty_pct,
  ROUND(a.no_vehicle_rate * 100, 1) AS no_vehicle_pct,
  COALESCE(f.annual_nonpayment_filings, 0) AS annual_nonpayment_filings,
  COALESCE(f.annual_no_fault_filings, 0) AS annual_no_fault_filings,
  COALESCE(f.annual_filings_total, 0) AS annual_filings_total,
  COALESCE(f.annual_defaults_total, 0) AS annual_defaults_total,
  COALESCE(f.avg_claimed_arrears_usd, 0) AS avg_claimed_arrears_usd,
  COALESCE(c.open_residential_311_count, 0) AS open_residential_311_count,
  (COALESCE(c.open_residential_311_count, 0) <= 1
   AND SAFE_DIVIDE(a.renter_hh_rent_50_pct_plus_count, a.renter_occupied_units) >= 0.20) AS is_silent_distress_candidate,
  a.latitude AS tract_lat,
  a.longitude AS tract_lon,
  a.data_provenance AS acs_provenance,
  f.filings_provenance
FROM `a4i_housing.acs_tract_housing_tenure` AS a
LEFT JOIN annual_filings AS f
  ON LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') = f.census_tract_geoid
LEFT JOIN open_res_311 AS c
  ON LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') = c.census_tract_geoid;

-- 3. Post-Output Metro Equity Audit View (Cohort-level only, isolated from individual case triage)
CREATE OR REPLACE VIEW `a4i_housing.v_metro_equity_audit` AS
SELECT
  v.census_tract_geoid,
  v.metro_area,
  v.is_silent_distress_candidate,
  v.open_residential_311_count,
  v.severe_rent_burden_pct,
  a.audit_black_share,
  a.audit_hispanic_share,
  a.audit_asian_share,
  a.audit_indigenous_share,
  a.audit_white_share
FROM `a4i_housing.v_tract_stability_context` v
JOIN `a4i_housing.acs_tract_housing_tenure` a
  ON v.census_tract_geoid = LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0');
