"""BigQuery analytical + VECTOR_SEARCH client with automatic offline SF fixture fallback.

Guarantees:
1. Genuine BigQuery `AI.EMBED` + `VECTOR_SEARCH` (`use_brute_force: true`) joined to
   `municipal_311_housing_complaints` on `request_id` so `created_date`, `jurisdiction`,
   `agency_code`, and `data_provenance` are always preserved.
2. 4x quarterly eviction join trap prevented via pre-aggregated CTE (`GROUP BY census_tract_geoid`).
3. 11-character leading-zero string GEOIDs (`'06075...'`) enforced in both SQL and Python.
4. Zero `audit_*` demographic columns ever queried in runtime case methods.
"""

import math
import re
from abc import ABC, abstractmethod
from typing import Any, Literal

from ..config import (
    ShelterWiseSettings,
    get_settings,
    normalize_geoid_11,
    resolve_metro_name,
)

_SAFE_IDENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_sql_identifier(value: str, name: str) -> str:
    if not value or not _SAFE_IDENT_RE.fullmatch(value):
        raise ValueError(f"Unsafe or empty SQL identifier for {name}: {value!r}")
    return value


class HousingRepository(ABC):
    """Interface shared by Live BigQuery and Offline SF Fixture repositories."""

    @property
    @abstractmethod
    def backend_mode(self) -> Literal["bigquery_live", "offline_sf_fixture"]:
        raise NotImplementedError

    @abstractmethod
    def vector_search_311_candidates(
        self, metro: str, semantic_query: str, top_k: int = 25
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_statutes(self, metro: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_relief_bulletins(self, metro: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_tract_and_metro_baseline(
        self,
        metro: str,
        census_tract_geoid: str = "",
        block_address_hint: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        raise NotImplementedError


class BigQueryHousingRepository(HousingRepository):
    """Production BigQuery repository executing parameterized SQL and VECTOR_SEARCH."""

    def __init__(self, settings: ShelterWiseSettings | None = None) -> None:
        from google.cloud import bigquery  # type: ignore[import-not-found]

        self._bigquery = bigquery
        self._settings = settings or get_settings()
        project = self._settings.project_id or None
        self._client = bigquery.Client(
            project=project, location=self._settings.location
        )
        resolved_project = self._settings.project_id or self._client.project
        if not resolved_project:
            raise RuntimeError(
                "Could not determine GCP project ID. Set GOOGLE_CLOUD_PROJECT."
            )
        self._project = _validate_sql_identifier(resolved_project, "project_id")
        self._dataset = _validate_sql_identifier(self._settings.dataset, "dataset")
        self._embedded_table = _validate_sql_identifier(
            self._settings.complaints_embedded_table, "complaints_embedded_table"
        )
        self._vertex_conn = _validate_sql_identifier(
            self._settings.vertex_connection, "vertex_connection"
        )
        self._embed_model = _validate_sql_identifier(
            self._settings.embedding_endpoint, "embedding_endpoint"
        )

    @property
    def backend_mode(self) -> Literal["bigquery_live", "offline_sf_fixture"]:
        return "bigquery_live"

    @property
    def _ds(self) -> str:
        return f"{self._project}.{self._dataset}"

    def vector_search_311_candidates(
        self, metro: str, semantic_query: str, top_k: int = 25
    ) -> list[dict[str, Any]]:
        bq = self._bigquery
        metro_canonical = resolve_metro_name(metro)
        bounded_k = max(5, min(int(top_k), 50))

        # Joins VECTOR_SEARCH over `complaints_embedded` back to `municipal_311_housing_complaints`
        # on `request_id` so `created_date`, `jurisdiction`, `agency_code`, `latitude`,
        # `longitude`, and `data_provenance` are guaranteed present even when Data Lane used
        # Notebook Section 13's minimal `CREATE TABLE complaints_embedded` snippet.
        sql = f"""
        SELECT
            m.request_id,
            m.state_code,
            m.metro_area,
            IFNULL(m.jurisdiction, '') AS jurisdiction,
            IFNULL(m.agency_code, '') AS agency_code,
            m.block_address,
            LPAD(CAST(m.census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
            m.property_type,
            m.raw_complaint_type,
            m.inspection_status,
            CAST(m.created_date AS STRING) AS created_date,
            CAST(m.closed_date AS STRING) AS closed_date,
            m.latitude,
            m.longitude,
            m.complaint_narrative,
            IFNULL(m.data_provenance, '') AS data_provenance,
            ROUND(vs.distance, 4) AS cosine_distance
        FROM VECTOR_SEARCH(
            (
                SELECT *
                FROM `{self._ds}.{self._embedded_table}`
                WHERE metro_area = @metro
            ),
            'embedding',
            (
                SELECT AI.EMBED(
                    @query_text,
                    connection_id => '{self._vertex_conn}',
                    endpoint => '{self._embed_model}'
                ).result AS query_vec
            ),
            query_column_to_search => 'query_vec',
            top_k => @top_k,
            options => '{{"use_brute_force":true}}'
        ) AS vs
        JOIN `{self._ds}.municipal_311_housing_complaints` AS m
          ON m.request_id = vs.base.request_id
         AND m.metro_area = @metro
        ORDER BY vs.distance ASC
        """
        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("metro", "STRING", metro_canonical),
                bq.ScalarQueryParameter("query_text", "STRING", semantic_query),
                bq.ScalarQueryParameter("top_k", "INT64", bounded_k),
            ]
        )
        rows = self._client.query(sql, job_config=job_config).result()
        return [dict(row.items()) for row in rows]

    def fetch_statutes(self, metro: str) -> list[dict[str, Any]]:
        bq = self._bigquery
        metro_canonical = resolve_metro_name(metro)
        sql = f"""
        SELECT
            statute_section_id,
            state_code,
            metro_area,
            jurisdiction,
            code_citation,
            ordinance_title,
            raw_statute_text,
            IFNULL(data_provenance, '[Public Legal Reference]') AS data_provenance
        FROM `{self._ds}.municipal_housing_ordinance_statutes`
        WHERE metro_area = @metro
        ORDER BY statute_section_id ASC
        """
        cfg = bq.QueryJobConfig(
            query_parameters=[bq.ScalarQueryParameter("metro", "STRING", metro_canonical)]
        )
        return [dict(r.items()) for r in self._client.query(sql, job_config=cfg).result()]

    def fetch_relief_bulletins(self, metro: str) -> list[dict[str, Any]]:
        bq = self._bigquery
        metro_canonical = resolve_metro_name(metro)
        sql = f"""
        SELECT
            bulletin_id,
            state_code,
            metro_area,
            service_region,
            program_name,
            administering_agency,
            funding_stream,
            CAST(requires_open_habitability_case AS BOOL) AS requires_open_habitability_case,
            CAST(residential_tenants_only AS BOOL) AS residential_tenants_only,
            raw_bulletin_text,
            intake_url,
            CAST(effective_date AS STRING) AS effective_date,
            IFNULL(data_provenance, '[Curated Benchmark]') AS data_provenance
        FROM `{self._ds}.rental_relief_program_bulletins`
        WHERE metro_area = @metro
        ORDER BY bulletin_id ASC
        """
        cfg = bq.QueryJobConfig(
            query_parameters=[bq.ScalarQueryParameter("metro", "STRING", metro_canonical)]
        )
        return [dict(r.items()) for r in self._client.query(sql, job_config=cfg).result()]

    def fetch_tract_and_metro_baseline(
        self,
        metro: str,
        census_tract_geoid: str = "",
        block_address_hint: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        bq = self._bigquery
        metro_canonical = resolve_metro_name(metro)
        clean_geoid = normalize_geoid_11(census_tract_geoid) if census_tract_geoid else ""
        resolution_method = "explicit_geoid" if clean_geoid else "metro_top_hotspot_fallback"

        # If tract GEOID was not supplied, try resolving from 100-block hint in 311 table
        if not clean_geoid and block_address_hint.strip():
            block_sql = f"""
            SELECT LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS geoid, COUNT(*) AS n
            FROM `{self._ds}.municipal_311_housing_complaints`
            WHERE metro_area = @metro
              AND LOWER(block_address) LIKE CONCAT('%', LOWER(@block_hint), '%')
              AND request_id NOT LIKE 'DECOY-%'
            GROUP BY 1
            ORDER BY n DESC
            LIMIT 1
            """
            b_cfg = bq.QueryJobConfig(
                query_parameters=[
                    bq.ScalarQueryParameter("metro", "STRING", metro_canonical),
                    bq.ScalarQueryParameter(
                        "block_hint", "STRING", block_address_hint.strip()
                    ),
                ]
            )
            b_rows = list(self._client.query(block_sql, job_config=b_cfg).result())
            if b_rows and b_rows[0]["geoid"]:
                clean_geoid = normalize_geoid_11(b_rows[0]["geoid"])
                resolution_method = "inferred_from_block_311"

        # Self-contained fan-out-safe CTE: pre-aggregates 4 quarters of `court_eviction_filings`
        # BEFORE joining `acs_tract_housing_tenure`, and strictly omits all `audit_*` columns!
        sql = f"""
        WITH annual_filings AS (
            SELECT
                LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
                SUM(nonpayment_filings_count) AS annual_nonpayment_filings,
                SUM(holdover_or_no_fault_filings_count) AS annual_no_fault_filings,
                SUM(nonpayment_filings_count + holdover_or_no_fault_filings_count) AS annual_filings_total,
                SUM(default_judgments_count) AS annual_defaults_total,
                ROUND(AVG(median_claimed_arrears_usd), 0) AS avg_claimed_arrears_usd,
                ANY_VALUE(data_provenance) AS filings_provenance
            FROM `{self._ds}.court_eviction_filings`
            WHERE metro_area = @metro
            GROUP BY 1
        ),
        open_res_311 AS (
            SELECT
                LPAD(CAST(census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
                COUNT(*) AS open_residential_311_count
            FROM `{self._ds}.municipal_311_housing_complaints`
            WHERE metro_area = @metro
              AND property_type = 'Residential'
              AND closed_date IS NULL
              AND NOT STARTS_WITH(LOWER(inspection_status), 'closed')
              AND request_id NOT LIKE 'DECOY-%'
            GROUP BY 1
        ),
        joined_tracts AS (
            SELECT
                LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') AS census_tract_geoid,
                a.county_name,
                a.metro_area,
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
                a.latitude AS tract_lat,
                a.longitude AS tract_lon,
                IFNULL(a.data_provenance, 'US Census ACS 5-Year') AS acs_provenance,
                IFNULL(f.filings_provenance, '[Modeled] Quarterly Civil Eviction Baseline') AS filings_provenance
            FROM `{self._ds}.acs_tract_housing_tenure` AS a
            LEFT JOIN annual_filings AS f
              ON LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') = f.census_tract_geoid
            LEFT JOIN open_res_311 AS c
              ON LPAD(CAST(a.census_tract_geoid AS STRING), 11, '0') = c.census_tract_geoid
            WHERE a.metro_area = @metro
        )
        SELECT * FROM joined_tracts
        ORDER BY open_residential_311_count DESC, annual_filings_total DESC
        """
        cfg = bq.QueryJobConfig(
            query_parameters=[bq.ScalarQueryParameter("metro", "STRING", metro_canonical)]
        )
        tracts = [dict(r.items()) for r in self._client.query(sql, job_config=cfg).result()]
        if not tracts:
            raise RuntimeError(f"No census tracts loaded in BigQuery for metro={metro_canonical!r}")

        return _summarize_tract_and_metro(tracts, clean_geoid, resolution_method, metro_canonical)


def _summarize_tract_and_metro(
    tracts: list[dict[str, Any]],
    clean_geoid: str,
    resolution_method: str,
    metro_canonical: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute metro-wide summary and pick requested tract (zero `audit_*` fields)."""
    total_renters = sum(int(t["renter_occupied_units"]) for t in tracts)
    total_sev = sum(int(t["renter_hh_rent_50_pct_plus_count"]) for t in tracts)
    metro_sev_pct = round((total_sev / max(total_renters, 1)) * 100.0, 1)

    rents = sorted(float(t["median_gross_rent"]) for t in tracts if t.get("median_gross_rent") is not None)
    filings_list = sorted(float(t["annual_filings_total"]) for t in tracts)
    mid = len(tracts) // 2
    median_rent = round(rents[len(rents) // 2], 0) if rents else 0.0
    median_filings = round(filings_list[mid], 1) if filings_list else 0.0

    metro_baseline = {
        "metro_area": metro_canonical,
        "tract_count": len(tracts),
        "total_renter_occupied_units": total_renters,
        "metro_severe_rent_burden_pct": metro_sev_pct,
        "metro_median_gross_rent": median_rent,
        "metro_annual_modeled_filings_total": sum(int(t["annual_filings_total"]) for t in tracts),
        "metro_median_tract_annual_filings": median_filings,
        "metro_open_residential_311_total": sum(int(t["open_residential_311_count"]) for t in tracts),
    }

    selected = None
    if clean_geoid:
        for t in tracts:
            if normalize_geoid_11(t["census_tract_geoid"]) == clean_geoid:
                selected = t
                break
        if selected is None:
            resolution_method = "metro_top_hotspot_fallback"

    if selected is None:
        selected = tracts[0]

    sev_pct = float(selected["severe_rent_burden_pct"])
    ann_filings = int(selected["annual_filings_total"])
    open_311 = int(selected["open_residential_311_count"])

    tract_ctx = {
        "census_tract_geoid": normalize_geoid_11(selected["census_tract_geoid"]),
        "resolution_method": resolution_method,
        "county_name": selected["county_name"],
        "metro_area": metro_canonical,
        "renter_occupied_units": int(selected["renter_occupied_units"]),
        "median_household_income": float(selected["median_household_income"]),
        "median_gross_rent": float(selected["median_gross_rent"]),
        "moderate_rent_burden_30_49_count": int(selected["renter_hh_rent_30_to_49_pct_count"]),
        "severe_rent_burden_50_plus_count": int(selected["renter_hh_rent_50_pct_plus_count"]),
        "severe_rent_burden_pct": sev_pct,
        "poverty_pct": float(selected["poverty_pct"]),
        "no_vehicle_pct": float(selected["no_vehicle_pct"]),
        "annual_nonpayment_filings": int(selected["annual_nonpayment_filings"]),
        "annual_no_fault_filings": int(selected["annual_no_fault_filings"]),
        "annual_filings_total": ann_filings,
        "annual_defaults_total": int(selected["annual_defaults_total"]),
        "avg_claimed_arrears_usd": float(selected["avg_claimed_arrears_usd"]),
        "open_residential_311_count": open_311,
        "tract_vs_metro_rent_burden_ratio": round(
            sev_pct / max(metro_sev_pct, 0.1), 2
        ),
        "tract_vs_metro_filings_ratio": round(
            ann_filings / max(median_filings, 0.1), 2
        ),
        "is_silent_distress_candidate": bool(open_311 <= 1 and sev_pct >= 20.0),
        "tract_lat": selected.get("tract_lat"),
        "tract_lon": selected.get("tract_lon"),
        "acs_provenance": selected["acs_provenance"],
        "filings_provenance": selected["filings_provenance"],
    }
    return tract_ctx, metro_baseline


# ---------------------------------------------------------------------------
# Offline San Francisco Fixture Repository (for instant local dev & pytest)
# Clearly badged as `offline_sf_fixture` so mock state is never misrepresented.
# Includes real-shaped SF 100-block cases + ALL 9 planted DECOY-* traps (3+3+3).
# ---------------------------------------------------------------------------

_SF_FIXTURE_311: list[dict[str, Any]] = [
    # --- 3 Commercial Open DECOYs (DECOY-SF-01..03) ---
    {
        "request_id": "DECOY-SF-01",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "400 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075012401",
        "property_type": "Commercial",
        "raw_complaint_type": "Commercial Boiler & Electrical Hazard",
        "inspection_status": "Open - Assigned",
        "created_date": "2026-11-10",
        "closed_date": None,
        "latitude": 37.7844,
        "longitude": -122.4139,
        "complaint_narrative": (
            "Commercial warehouse steam boiler off since Tuesday; radiators stone cold and roof "
            "water dripping near electrical breaker panel. Zero residential tenants on premises."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Commercial Property",
    },
    {
        "request_id": "DECOY-SF-02",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "500 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075012401",
        "property_type": "Commercial",
        "raw_complaint_type": "Commercial Mold & Water Intrusion",
        "inspection_status": "Open - Under Investigation",
        "created_date": "2026-11-08",
        "closed_date": None,
        "latitude": 37.7840,
        "longitude": -122.4150,
        "complaint_narrative": (
            "Retail storefront storage basement has black mold and water leak near fuse box; "
            "commercial lease only, no residential units."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Commercial Property",
    },
    {
        "request_id": "DECOY-SF-03",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DPH",
        "block_address": "600 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075017601",
        "property_type": "Commercial",
        "raw_complaint_type": "Sewage Backup - Commercial",
        "inspection_status": "Open - Assigned",
        "created_date": "2026-11-12",
        "closed_date": None,
        "latitude": 37.7782,
        "longitude": -122.4112,
        "complaint_narrative": (
            "Office building ground-floor restroom raw sewage backup and no hot water; commercial occupancy only."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Commercial Property",
    },
    # --- 3 Residential Closed - Abated DECOYs (DECOY-SF-04..06) ---
    {
        "request_id": "DECOY-SF-04",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "400 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075012401",
        "property_type": "Residential",
        "raw_complaint_type": "Inadequate Heat / Boiler Failure",
        "inspection_status": "Closed - Abated",
        "created_date": "2026-02-11",
        "closed_date": "2026-02-28",
        "latitude": 37.7848,
        "longitude": -122.4135,
        "complaint_narrative": (
            "Apartment radiators ice cold for two weeks and ceiling leak near kitchen electrical panel; "
            "boiler replaced and leak fully abated, verified by DBI inspector."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Closed Abated",
    },
    {
        "request_id": "DECOY-SF-05",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "700 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075017601",
        "property_type": "Residential",
        "raw_complaint_type": "Mold & Dampness",
        "inspection_status": "Closed - Abated",
        "created_date": "2026-04-03",
        "closed_date": "2026-05-01",
        "latitude": 37.7785,
        "longitude": -122.4120,
        "complaint_narrative": (
            "Severe black mold in residential bedroom; remediation completed and case closed."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Closed Abated",
    },
    {
        "request_id": "DECOY-SF-06",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "800 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075022801",
        "property_type": "Residential",
        "raw_complaint_type": "Plumbing / Sewage",
        "inspection_status": "Closed - Abated",
        "created_date": "2026-06-10",
        "closed_date": "2026-06-25",
        "latitude": 37.7590,
        "longitude": -122.4105,
        "complaint_narrative": (
            "Residential drain backup repaired and sanitized; final sign-off issued."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - Closed Abated",
    },
    # --- 3 Residential Closed - No Violation DECOYs (DECOY-SF-07..09) ---
    {
        "request_id": "DECOY-SF-07",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "400 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075012401",
        "property_type": "Residential",
        "raw_complaint_type": "Routine Habitability Clearance",
        "inspection_status": "Closed - No Violation",
        "created_date": "2026-09-01",
        "closed_date": "2026-09-03",
        "latitude": 37.7842,
        "longitude": -122.4142,
        "complaint_narrative": (
            "Proactive residential inspection: radiators operating above 68F minimum, no water leaks "
            "near kitchen fuse box, no mold, and zero habitability defects found."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - No Violation",
    },
    {
        "request_id": "DECOY-SF-08",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "900 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075017601",
        "property_type": "Residential",
        "raw_complaint_type": "Electrical Inspection",
        "inspection_status": "Closed - No Violation",
        "created_date": "2026-08-19",
        "closed_date": "2026-08-21",
        "latitude": 37.7779,
        "longitude": -122.4128,
        "complaint_narrative": (
            "Inspector checked breaker box and ceiling moisture meter: dry, no electrical hazard, no violation."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - No Violation",
    },
    {
        "request_id": "DECOY-SF-09",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DPH",
        "block_address": "1000 Block Example Teaching Way [Planted Case]",
        "census_tract_geoid": "06075022801",
        "property_type": "Residential",
        "raw_complaint_type": "Sanitation Check",
        "inspection_status": "Closed - No Violation",
        "created_date": "2026-07-14",
        "closed_date": "2026-07-16",
        "latitude": 37.7595,
        "longitude": -122.4110,
        "complaint_narrative": (
            "Annual residential check found no sewage leaks, no pests, and zero code violations."
        ),
        "data_provenance": "Planted Eligibility Decoy [Planted Case] - No Violation",
    },
    # --- Open Real-Shaped Residential 311 Habitability Records (Eligible!) ---
    {
        "request_id": "SF-311-2026-88412",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "400 Block Ellis St",
        "census_tract_geoid": "06075012401",
        "property_type": "Residential",
        "raw_complaint_type": "No Heat / Defective Steam Radiator",
        "inspection_status": "Open - Notice of Violation Issued",
        "created_date": "2026-11-06",
        "closed_date": None,
        "latitude": 37.7846,
        "longitude": -122.4132,
        "complaint_narrative": (
            "Multi-unit residential building on 400 Block Ellis St: central steam boiler cycling off, "
            "dwelling unit [REDACTED UNIT] radiators completely cold below 58 degrees for over 10 days."
        ),
        "data_provenance": "data.sfgov.org SF 311 / DBI Housing Complaints (100-Block Redacted)",
    },
    {
        "request_id": "SF-311-2026-88905",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "400 Block Ellis St",
        "census_tract_geoid": "06075012401",
        "property_type": "Residential",
        "raw_complaint_type": "Water Intrusion / Electrical Arcing Hazard",
        "inspection_status": "Open - Emergency Inspection Scheduled",
        "created_date": "2026-11-12",
        "closed_date": None,
        "latitude": 37.7847,
        "longitude": -122.4134,
        "complaint_narrative": (
            "Upstairs plumbing leak penetrating kitchen ceiling plaster directly above residential "
            "fuse/breaker subpanel on 400 Block Ellis St; active dripping near wiring."
        ),
        "data_provenance": "data.sfgov.org SF 311 / DBI Housing Complaints (100-Block Redacted)",
    },
    {
        "request_id": "SF-311-2026-87219",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DPH",
        "block_address": "1400 Block Mission St",
        "census_tract_geoid": "06075017601",
        "property_type": "Residential",
        "raw_complaint_type": "Severe Dampness & Mold",
        "inspection_status": "Open - Assigned",
        "created_date": "2026-10-29",
        "closed_date": None,
        "latitude": 37.7748,
        "longitude": -122.4165,
        "complaint_narrative": (
            "Chronic window and wall water intrusion causing heavy black mold growth across residential "
            "bedroom wall in apartment [REDACTED UNIT] on 1400 Block Mission St."
        ),
        "data_provenance": "data.sfgov.org SF 311 / DBI Housing Complaints (100-Block Redacted)",
    },
    {
        "request_id": "SF-311-2026-89104",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "agency_code": "DBI",
        "block_address": "2100 Block Bryant St",
        "census_tract_geoid": "06075022801",
        "property_type": "Residential",
        "raw_complaint_type": "Sewage / Plumbing Overflow",
        "inspection_status": "Open - Assigned",
        "created_date": "2026-11-14",
        "closed_date": None,
        "latitude": 37.7598,
        "longitude": -122.4099,
        "complaint_narrative": (
            "Main waste stack backing up greywater into ground-floor residential tub and hallway."
        ),
        "data_provenance": "data.sfgov.org SF 311 / DBI Housing Complaints (100-Block Redacted)",
    },
]

_SF_FIXTURE_STATUTES: list[dict[str, Any]] = [
    {
        "statute_section_id": "STAT-CA-01",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "State of California",
        "code_citation": "Cal. Civ. Code §§ 1941.1 & 1942.4; Cal. Code Civ. Proc. § 1174.2",
        "ordinance_title": "California Implied Warranty of Habitability & Statutory Bar on Rent Demand",
        "raw_statute_text": (
            "Requires residential landlords to maintain weatherproofing, working heating facilities, "
            "safe electrical wiring, hot/cold water, and sanitary plumbing. Under Civ. Code § 1942.4, "
            "bars landlords from demanding rent or serving a 3-day pay-or-quit notice when an official "
            "code citation for untenantable residential conditions remains unabated; CCP § 1174.2 provides "
            "an affirmative habitability defense and rent abatement in unlawful detainer proceedings."
        ),
        "data_provenance": "Public Statutory & Program Policy Text: Summarized Municipal/State Ordinances (2025-2026)",
    },
    {
        "statute_section_id": "STAT-CA-02",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "City and County of San Francisco",
        "code_citation": "SF Admin. Code §§ 37.9(a)(1), 37.2(r) & SF Housing Code § 701",
        "ordinance_title": "San Francisco Rent Ordinance Habitability Defense & Minimum Heat Mandate",
        "raw_statute_text": (
            "Mandates residential heating capable of maintaining 68°F (SF Housing Code § 701) and treats "
            "substantial habitability reductions (heat loss, active leaks, unsafe electrical systems) as a "
            "defense to nonpayment unlawful detainer actions and grounds for Rent Board decrease-in-services "
            "petitions under SF Admin. Code § 37.9."
        ),
        "data_provenance": "Public Statutory & Program Policy Text: Summarized Municipal/State Ordinances (2025-2026)",
    },
    {
        "statute_section_id": "STAT-CA-03",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "jurisdiction": "State of California & City and County of San Francisco",
        "code_citation": "Cal. Civ. Code § 1942.5; SF Admin. Code § 37.9(d)",
        "ordinance_title": "180-Day Anti-Retaliation Protection After 311 / DBI Habitability Complaint",
        "raw_statute_text": (
            "Prohibits a residential landlord from evicting, increasing rent, decreasing services, or "
            "threatening a tenant within 180 days of the tenant notifying the landlord of uninhabitable "
            "conditions or filing a complaint with SF 311 / Department of Building Inspection (DBI)."
        ),
        "data_provenance": "Public Statutory & Program Policy Text: Summarized Municipal/State Ordinances (2025-2026)",
    },
]

_SF_FIXTURE_BULLETINS: list[dict[str, Any]] = [
    {
        "bulletin_id": "REL-SF-01",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "service_region": "City and County of San Francisco",
        "program_name": "SF Emergency Habitability & Code-Enforcement Stabilization Grant",
        "administering_agency": "SF Mayor's Office of Housing & Community Development (MOHCD)",
        "funding_stream": "Municipal Habitability Stabilization Fund",
        "requires_open_habitability_case": True,
        "residential_tenants_only": True,
        "raw_bulletin_text": (
            "Provides up to $8,500 in emergency rent stabilization or temporary safety assistance for "
            "low-income San Francisco residential renters (<=80% AMI) facing eviction where an active, "
            "unclosed SF 311 or DBI residential habitability complaint (heat, electrical, water, mold, sewage) "
            "is documented on the property/block."
        ),
        "intake_url": "https://www.sf.gov/departments--mayors-office-housing-and-community-development",
        "effective_date": "2026-01-15",
        "data_provenance": "[Curated Benchmark] Summarized Municipal Emergency Rental Relief Guidelines",
    },
    {
        "bulletin_id": "REL-SF-02",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "service_region": "City and County of San Francisco",
        "program_name": "SF Tenant Right-to-Counsel Habitability Escrow & Repair Bridge",
        "administering_agency": "SF Eviction Defense Collaborative (EDC) / MOHCD",
        "funding_stream": "Prop F Right-to-Counsel & Habitability Defense Reserve",
        "requires_open_habitability_case": True,
        "residential_tenants_only": True,
        "raw_bulletin_text": (
            "Pairs expedited legal-aid unlawful detainer representation with up to $6,000 in court-ready "
            "arrears cure funds for residential households with active unlawful detainer notices AND "
            "open municipal code/311 habitability violations."
        ),
        "intake_url": "https://sfrtc.org/",
        "effective_date": "2026-02-01",
        "data_provenance": "[Curated Benchmark] Summarized Municipal Emergency Rental Relief Guidelines",
    },
    {
        "bulletin_id": "REL-SF-03",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "service_region": "City and County of San Francisco",
        "program_name": "San Francisco Emergency Rental Assistance Program (SF ERAP)",
        "administering_agency": "SF Human Services Agency (SFHSA) & Community Partners",
        "funding_stream": "Local General Fund Homelessness Prevention",
        "requires_open_habitability_case": False,
        "residential_tenants_only": True,
        "raw_bulletin_text": (
            "Covers back-rent arrears (up to $10,000) for income-eligible SF residential renters (<=80% AMI) "
            "with a 3-day pay-or-quit notice or unlawful detainer summons. Does NOT require an open 311 "
            "or DBI habitability violation; prioritized by court deadline urgency."
        ),
        "intake_url": "https://www.sfhsa.org/services/housing/emergency-rental-assistance",
        "effective_date": "2026-01-01",
        "data_provenance": "[Curated Benchmark] Summarized Municipal Emergency Rental Relief Guidelines",
    },
    {
        "bulletin_id": "REL-SF-04",
        "state_code": "CA",
        "metro_area": "San Francisco",
        "service_region": "Bay Area / San Francisco County",
        "program_name": "Season of Sharing Rapid Housing Stabilization Fund",
        "administering_agency": "Crankstart / Catholic Charities SF Intake Network",
        "funding_stream": "Philanthropic Emergency Prevention Pool",
        "requires_open_habitability_case": False,
        "residential_tenants_only": True,
        "raw_bulletin_text": (
            "One-time crisis grant (up to $5,000) for families with children, seniors, or medically "
            "vulnerable residential tenants experiencing sudden income shock or urgent eviction notice. "
            "No open 311 habitability ticket required."
        ),
        "intake_url": "https://seasonofsharing.org/get-assistance/",
        "effective_date": "2026-01-01",
        "data_provenance": "[Curated Benchmark] Summarized Municipal Emergency Rental Relief Guidelines",
    },
]

_SF_FIXTURE_TRACTS: list[dict[str, Any]] = [
    {
        "census_tract_geoid": "06075012401",
        "county_name": "San Francisco County",
        "metro_area": "San Francisco",
        "renter_occupied_units": 2410,
        "median_household_income": 34200.0,
        "median_gross_rent": 1680.0,
        "renter_hh_rent_30_to_49_pct_count": 690,
        "renter_hh_rent_50_pct_plus_count": 785,
        "severe_rent_burden_pct": 32.6,
        "poverty_pct": 29.4,
        "no_vehicle_pct": 74.2,
        "annual_nonpayment_filings": 96,
        "annual_no_fault_filings": 22,
        "annual_filings_total": 118,
        "annual_defaults_total": 29,
        "avg_claimed_arrears_usd": 4650.0,
        "open_residential_311_count": 9,
        "tract_lat": 37.7845,
        "tract_lon": -122.4136,
        "acs_provenance": "US Census Bureau ACS 5-Year (B25070 & B19013)",
        "filings_provenance": "[Modeled] Quarterly Tract Eviction Filings (2025-Q3..2026-Q2)",
    },
    {
        "census_tract_geoid": "06075017601",
        "county_name": "San Francisco County",
        "metro_area": "San Francisco",
        "renter_occupied_units": 3120,
        "median_household_income": 48900.0,
        "median_gross_rent": 2190.0,
        "renter_hh_rent_30_to_49_pct_count": 780,
        "renter_hh_rent_50_pct_plus_count": 745,
        "severe_rent_burden_pct": 23.9,
        "poverty_pct": 21.8,
        "no_vehicle_pct": 66.5,
        "annual_nonpayment_filings": 78,
        "annual_no_fault_filings": 18,
        "annual_filings_total": 96,
        "annual_defaults_total": 21,
        "avg_claimed_arrears_usd": 5120.0,
        "open_residential_311_count": 6,
        "tract_lat": 37.7762,
        "tract_lon": -122.4148,
        "acs_provenance": "US Census Bureau ACS 5-Year (B25070 & B19013)",
        "filings_provenance": "[Modeled] Quarterly Tract Eviction Filings (2025-Q3..2026-Q2)",
    },
    {
        # Silent distress tract: high severe rent burden & high filings, 0 open residential 311s!
        "census_tract_geoid": "06075023102",
        "county_name": "San Francisco County",
        "metro_area": "San Francisco",
        "renter_occupied_units": 1640,
        "median_household_income": 39500.0,
        "median_gross_rent": 1890.0,
        "renter_hh_rent_30_to_49_pct_count": 430,
        "renter_hh_rent_50_pct_plus_count": 510,
        "severe_rent_burden_pct": 31.1,
        "poverty_pct": 26.7,
        "no_vehicle_pct": 41.0,
        "annual_nonpayment_filings": 74,
        "annual_no_fault_filings": 15,
        "annual_filings_total": 89,
        "annual_defaults_total": 26,
        "avg_claimed_arrears_usd": 4890.0,
        "open_residential_311_count": 0,
        "tract_lat": 37.7341,
        "tract_lon": -122.3885,
        "acs_provenance": "US Census Bureau ACS 5-Year (B25070 & B19013)",
        "filings_provenance": "[Modeled] Quarterly Tract Eviction Filings (2025-Q3..2026-Q2)",
    },
]


def _token_cosine_distance(query: str, doc: str) -> float:
    """Deterministic lexical-synonym cosine distance for offline unit tests."""
    synonyms = {
        "cold": "heat",
        "ice": "heat",
        "freezing": "heat",
        "radiator": "heat",
        "radiators": "heat",
        "boiler": "heat",
        "steam": "heat",
        "heating": "heat",
        "dripping": "leak",
        "leaking": "leak",
        "water": "leak",
        "ceiling": "leak",
        "fuse": "electrical",
        "breaker": "electrical",
        "wiring": "electrical",
        "subpanel": "electrical",
        "panel": "electrical",
        "mildew": "mold",
        "dampness": "mold",
        "sewer": "sewage",
        "greywater": "sewage",
        "drain": "sewage",
    }

    def _vec(text: str) -> dict[str, float]:
        counts: dict[str, float] = {}
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            if len(tok) < 3:
                continue
            canon = synonyms.get(tok, tok)
            counts[canon] = counts.get(canon, 0.0) + 1.0
        return counts

    vq, vd = _vec(query), _vec(doc)
    if not vq or not vd:
        return 0.85
    dot = sum(vq[k] * vd.get(k, 0.0) for k in vq)
    norm_q = math.sqrt(sum(v * v for v in vq.values()))
    norm_d = math.sqrt(sum(v * v for v in vd.values()))
    sim = dot / max(norm_q * norm_d, 1e-9)
    return round(max(0.05, min(0.95, 1.0 - sim)), 4)


class SanFranciscoFixtureRepository(HousingRepository):
    """Deterministic offline San Francisco repository for local dev and CI tests."""

    @property
    def backend_mode(self) -> Literal["bigquery_live", "offline_sf_fixture"]:
        return "offline_sf_fixture"

    def vector_search_311_candidates(
        self, metro: str, semantic_query: str, top_k: int = 25
    ) -> list[dict[str, Any]]:
        metro_canonical = resolve_metro_name(metro)
        scored: list[dict[str, Any]] = []
        for row in _SF_FIXTURE_311:
            item = dict(row)
            # Re-tag metro in fixture mode if another official metro is tested offline
            if metro_canonical != "San Francisco":
                item["metro_area"] = metro_canonical
            doc_text = f"{item['raw_complaint_type']} {item['complaint_narrative']}"
            item["cosine_distance"] = _token_cosine_distance(semantic_query, doc_text)
            scored.append(item)
        scored.sort(key=lambda r: (r["cosine_distance"], r["request_id"]))
        return scored[: max(5, min(int(top_k), 50))]

    def fetch_statutes(self, metro: str) -> list[dict[str, Any]]:
        metro_canonical = resolve_metro_name(metro)
        out = []
        for s in _SF_FIXTURE_STATUTES:
            copy = dict(s)
            copy["metro_area"] = metro_canonical
            out.append(copy)
        return out

    def fetch_relief_bulletins(self, metro: str) -> list[dict[str, Any]]:
        metro_canonical = resolve_metro_name(metro)
        out = []
        for b in _SF_FIXTURE_BULLETINS:
            copy = dict(b)
            copy["metro_area"] = metro_canonical
            out.append(copy)
        return out

    def fetch_tract_and_metro_baseline(
        self,
        metro: str,
        census_tract_geoid: str = "",
        block_address_hint: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        metro_canonical = resolve_metro_name(metro)
        clean_geoid = normalize_geoid_11(census_tract_geoid) if census_tract_geoid else ""
        resolution_method = "explicit_geoid" if clean_geoid else "metro_top_hotspot_fallback"

        if not clean_geoid and block_address_hint.strip():
            hint_lower = block_address_hint.strip().lower()
            for row in _SF_FIXTURE_311:
                if (
                    not row["request_id"].startswith("DECOY-")
                    and hint_lower in row["block_address"].lower()
                ):
                    clean_geoid = normalize_geoid_11(row["census_tract_geoid"])
                    resolution_method = "inferred_from_block_311"
                    break

        tracts = [dict(t, metro_area=metro_canonical) for t in _SF_FIXTURE_TRACTS]
        tract_ctx, baseline = _summarize_tract_and_metro(
            tracts, clean_geoid, resolution_method, metro_canonical
        )
        # Align metro-level SF summary totals to official starter pack counts when in SF fixture mode
        if metro_canonical == "San Francisco":
            baseline.update(
                {
                    "tract_count": 42,
                    "total_renter_occupied_units": 66252,
                    "metro_severe_rent_burden_pct": 17.5,
                    "metro_annual_modeled_filings_total": 2359,
                    "metro_median_tract_annual_filings": 52.0,
                    "metro_open_residential_311_total": 140,
                }
            )
            tract_ctx["tract_vs_metro_rent_burden_ratio"] = round(
                tract_ctx["severe_rent_burden_pct"] / 17.5, 2
            )
            tract_ctx["tract_vs_metro_filings_ratio"] = round(
                tract_ctx["annual_filings_total"] / 52.0, 2
            )
        return tract_ctx, baseline


def get_housing_repository(
    settings: ShelterWiseSettings | None = None,
) -> HousingRepository:
    """Resolve Live BigQuery repository or Offline SF Fixture repository."""
    cfg = settings or get_settings()
    if cfg.backend_mode == "fixture":
        return SanFranciscoFixtureRepository()
    if cfg.backend_mode == "bigquery":
        return BigQueryHousingRepository(cfg)

    # "auto" mode: prefer Live BigQuery when GCP project & library are available
    if cfg.project_id:
        try:
            return BigQueryHousingRepository(cfg)
        except Exception:
            return SanFranciscoFixtureRepository()

    try:
        import google.auth  # type: ignore[import-not-found]
        from google.cloud import bigquery  # noqa: F401  # type: ignore[import-not-found]

        _, detected_project = google.auth.default()
        if detected_project:
            return BigQueryHousingRepository(cfg)
    except Exception:
        pass

    return SanFranciscoFixtureRepository()
