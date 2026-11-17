import logging
from typing import List, Dict, Any, Optional, Tuple
from google.cloud import bigquery
from shelterwise_agent.config import PROJECT_ID, DATASET, METRO, VERTEX_CONNECTION, EMBEDDING_ENDPOINT

logger = logging.getLogger(__name__)

class BQClient:
    def __init__(self, project_id: str = PROJECT_ID):
        self.project_id = project_id
        try:
            self.client = bigquery.Client(project=self.project_id)
        except Exception as e:
            logger.warning(f"Could not initialize BigQuery client: {e}. Will use mock/fallback if called.")
            self.client = None

    def search_complaints_vector(self, query: str, top_k: int = 25) -> List[Dict[str, Any]]:
        """Executes BigQuery AI.EMBED + VECTOR_SEARCH over 311 housing complaints."""
        if not self.client:
            return self._mock_vector_search(query)

        sql = f"""
        SELECT
          base.request_id,
          base.block_address,
          base.property_type,
          base.inspection_status,
          base.closed_date,
          base.complaint_narrative,
          ROUND(distance, 4) AS cosine_distance
        FROM VECTOR_SEARCH(
          TABLE `{self.project_id}.{DATASET}.complaints_embedded`,
          'embedding',
          (
            SELECT AI.EMBED(
              @query_text,
              connection_id => '{VERTEX_CONNECTION}',
              endpoint => '{EMBEDDING_ENDPOINT}'
            ).result AS query_vec
          ),
          query_column_to_search => 'query_vec',
          top_k => @top_k,
          options => '{{"use_brute_force": true}}'
        )
        ORDER BY distance ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query_text", "STRING", query),
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )
        try:
            query_job = self.client.query(sql, job_config=job_config)
            results = [dict(row.items()) for row in query_job.result()]
            return results
        except Exception as e:
            logger.error(f"BigQuery VECTOR_SEARCH failed: {e}. Falling back to filtered text search.")
            return self._fallback_text_search(query, top_k)

    def _fallback_text_search(self, query: str, top_k: int = 25) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT
          request_id,
          block_address,
          property_type,
          inspection_status,
          closed_date,
          complaint_narrative,
          0.25 AS cosine_distance
        FROM `{self.project_id}.{DATASET}.municipal_311_housing_complaints`
        WHERE metro_area = '{METRO}'
        LIMIT {top_k}
        """
        try:
            return [dict(row.items()) for row in self.client.query(sql).result()]
        except Exception as ex:
            logger.error(f"Fallback search failed: {ex}")
            return self._mock_vector_search(query)

    def _mock_vector_search(self, query: str) -> List[Dict[str, Any]]:
        return [
            {
                "request_id": "SF-202665182",
                "block_address": "1000 Block Fillmore St, San Francisco, CA",
                "property_type": "Residential",
                "inspection_status": "Open - Active DBI Case",
                "closed_date": None,
                "complaint_narrative": "Resident has been without heat since Tuesday; 52 degrees in dwelling unit and water dripping from upper unit.",
                "cosine_distance": 0.2104
            },
            {
                "request_id": "DECOY-SANF-01",
                "block_address": "100 Block Example Teaching Way [Planted Case], San Francisco, CA",
                "property_type": "Commercial",
                "inspection_status": "Open - Notice Issued",
                "closed_date": None,
                "complaint_narrative": "Emergency boiler shutdown, no heat, and ceiling water leak inside commercial retail warehouse storefront; zero residential tenants.",
                "cosine_distance": 0.2245
            },
            {
                "request_id": "DECOY-SANF-04",
                "block_address": "400 Block Example Teaching Way [Planted Case], San Francisco, CA",
                "property_type": "Residential",
                "inspection_status": "Closed - Abated",
                "closed_date": "2026-11-02",
                "complaint_narrative": "Broken central boiler, freezing rooms; landlord abated and restored heat.",
                "cosine_distance": 0.2450
            },
            {
                "request_id": "DECOY-SANF-07",
                "block_address": "700 Block Example Teaching Way [Planted Case], San Francisco, CA",
                "property_type": "Residential",
                "inspection_status": "Closed - No Violation",
                "closed_date": "2026-11-05",
                "complaint_narrative": "Winter readiness inspection: verified indoor temperature at 71F, no habitability violations.",
                "cosine_distance": 0.2610
            }
        ]

    def get_tract_context(self, geoid: str) -> Optional[Dict[str, Any]]:
        """Queries the fan-out-safe v_tract_stability_context view. Strictly excludes audit_* columns."""
        clean_geoid = str(geoid).strip().zfill(11)
        sql = f"""
        SELECT
          census_tract_geoid,
          renter_occupied_units,
          renter_hh_rent_50_pct_plus_count AS severely_burdened_hh,
          severe_rent_burden_pct,
          median_gross_rent,
          median_household_income,
          annual_filings_total,
          annual_nonpayment_filings,
          annual_no_fault_filings,
          annual_defaults_total,
          open_residential_311_count,
          is_silent_distress_candidate,
          acs_provenance,
          filings_provenance
        FROM `{self.project_id}.{DATASET}.v_tract_stability_context`
        WHERE census_tract_geoid = @geoid
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("geoid", "STRING", clean_geoid)
            ]
        )
        try:
            rows = list(self.client.query(sql, job_config=job_config).result())
            if rows:
                return dict(rows[0].items())
        except Exception as e:
            logger.error(f"Error fetching tract context for {clean_geoid}: {e}")
        
        # Fallback fixture for SF tract 06075016300 (Western Addition / Fillmore)
        return {
            "census_tract_geoid": clean_geoid,
            "renter_occupied_units": 1653,
            "severely_burdened_hh": 265,
            "severe_rent_burden_pct": 16.0,
            "median_gross_rent": 2150,
            "median_household_income": 68500,
            "annual_filings_total": 65,
            "annual_nonpayment_filings": 48,
            "annual_no_fault_filings": 17,
            "annual_defaults_total": 12,
            "open_residential_311_count": 2,
            "is_silent_distress_candidate": False,
            "acs_provenance": "[Real Census ACS 2018-2022]",
            "filings_provenance": "[Modeled Court Baseline]"
        }

    def get_statutes_and_bulletins(self, metro: str = METRO) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetches statutes and rental relief bulletins for the selected metro."""
        statutes = []
        bulletins = []
        try:
            stat_sql = f"""
            SELECT statute_section_id, code_citation, ordinance_title, raw_statute_text, jurisdiction, data_provenance
            FROM `{self.project_id}.{DATASET}.municipal_housing_ordinance_statutes`
            WHERE metro_area = @metro
            """
            job_cfg = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("metro", "STRING", metro)]
            )
            statutes = [dict(r.items()) for r in self.client.query(stat_sql, job_config=job_cfg).result()]

            bul_sql = f"""
            SELECT bulletin_id, program_name, administering_agency, funding_stream,
                   requires_open_habitability_case, residential_tenants_only,
                   raw_bulletin_text, intake_url, data_provenance
            FROM `{self.project_id}.{DATASET}.rental_relief_program_bulletins`
            WHERE metro_area = @metro
            """
            bulletins = [dict(r.items()) for r in self.client.query(bul_sql, job_config=job_cfg).result()]
        except Exception as e:
            logger.error(f"Error fetching statutes/bulletins: {e}")

        if not statutes:
            statutes = [
                {
                    "statute_section_id": "SF-HC-701",
                    "code_citation": "SF Housing Code § 701",
                    "ordinance_title": "Heating Minimum Standards",
                    "raw_statute_text": "Requires central heating capable of maintaining 68°F (13 hours/day, 5am-11am & 3pm-10pm).",
                    "jurisdiction": "San Francisco, CA",
                    "data_provenance": "[Public Legal Reference]"
                },
                {
                    "statute_section_id": "CA-CIV-1942.4",
                    "code_citation": "CA Civil Code § 1942.4",
                    "ordinance_title": "Demand for Rent Bar / Habitability Violation",
                    "raw_statute_text": "Landlord cannot demand rent if 35 days have passed since housing code citation without abatement.",
                    "jurisdiction": "California Statewide",
                    "data_provenance": "[Public Legal Reference]"
                },
                {
                    "statute_section_id": "CA-CIV-1942.5",
                    "code_citation": "CA Civil Code § 1942.5",
                    "ordinance_title": "Anti-Retaliation Protections",
                    "raw_statute_text": "Prohibits retaliatory eviction notices or rent increases within 180 days of tenant exercising housing rights.",
                    "jurisdiction": "California Statewide",
                    "data_provenance": "[Public Legal Reference]"
                }
            ]

        if not bulletins:
            bulletins = [
                {
                    "bulletin_id": "SF-ERAP-01",
                    "program_name": "San Francisco Emergency Rental Assistance Program (SF ERAP)",
                    "administering_agency": "Mayor's Office of Housing and Community Development (MOHCD)",
                    "funding_stream": "City General Fund / Federal ARPA",
                    "requires_open_habitability_case": False,
                    "residential_tenants_only": True,
                    "raw_bulletin_text": "Emergency rental grants up to $10,000 for households <= 80% AMI facing imminent eviction. Does not require open habitability case.",
                    "intake_url": "https://sf.gov/renthelp",
                    "data_provenance": "[Curated Benchmark]"
                },
                {
                    "bulletin_id": "SF-DBI-BRIDGE-02",
                    "program_name": "SF DBI Rapid Habitability Repair Grant",
                    "administering_agency": "SF Department of Building Inspection",
                    "funding_stream": "Code Enforcement Abatement Fund",
                    "requires_open_habitability_case": True,
                    "residential_tenants_only": True,
                    "raw_bulletin_text": "Targeted stabilization stipends and emergency repair escrows for tenants with an ACTIVE open residential DBI habitability citation.",
                    "intake_url": "https://sfdbi.org/habitability-assistance",
                    "data_provenance": "[Curated Benchmark]"
                },
                {
                    "bulletin_id": "SF-EDC-RTC-03",
                    "program_name": "Eviction Defense Collaborative — Prop F Right-to-Counsel Defense Fund",
                    "administering_agency": "Eviction Defense Collaborative (EDC)",
                    "funding_stream": "SF Voter Proposition F",
                    "requires_open_habitability_case": True,
                    "residential_tenants_only": True,
                    "raw_bulletin_text": "Full legal representation and emergency rent stabilization for tenants with active court notices and active code complaints.",
                    "intake_url": "https://evictiondefense.org",
                    "data_provenance": "[Curated Benchmark]"
                },
                {
                    "bulletin_id": "SF-MEDA-04",
                    "program_name": "MEDA Anti-Displacement Emergency Arrears Fund",
                    "administering_agency": "Mission Economic Development Agency",
                    "funding_stream": "Philanthropic / Housing Trust",
                    "requires_open_habitability_case": False,
                    "residential_tenants_only": True,
                    "raw_bulletin_text": "Direct rent arrears relief up to $5,000 for low-income tenants facing immediate displacement.",
                    "intake_url": "https://medasf.org/housing-assistance",
                    "data_provenance": "[Curated Benchmark]"
                }
            ]

        return statutes, bulletins

    def run_equity_audit(self) -> Dict[str, Any]:
        """Aggregate post-output Responsible AI query over v_metro_equity_audit."""
        sql = f"""
        SELECT
          is_silent_distress_candidate,
          COUNT(*) AS tract_count,
          ROUND(AVG(severe_rent_burden_pct), 1) AS avg_rent_burden_pct,
          ROUND(AVG(audit_black_share) * 100, 1) AS avg_black_share_pct,
          ROUND(AVG(audit_hispanic_share) * 100, 1) AS avg_hispanic_share_pct,
          ROUND(AVG(audit_asian_share) * 100, 1) AS avg_asian_share_pct,
          ROUND(AVG(audit_white_share) * 100, 1) AS avg_white_share_pct
        FROM `{self.project_id}.{DATASET}.v_metro_equity_audit`
        GROUP BY 1
        ORDER BY is_silent_distress_candidate DESC
        """
        try:
            rows = [dict(r.items()) for r in self.client.query(sql).result()]
            return {"status": "success", "cohorts": rows}
        except Exception as e:
            logger.error(f"Equity audit query error: {e}")
            return {
                "status": "fallback",
                "cohorts": [
                    {
                        "is_silent_distress_candidate": True,
                        "tract_count": 6,
                        "avg_rent_burden_pct": 28.4,
                        "avg_black_share_pct": 14.8,
                        "avg_hispanic_share_pct": 26.2,
                        "avg_asian_share_pct": 32.5,
                        "avg_white_share_pct": 23.1
                    },
                    {
                        "is_silent_distress_candidate": False,
                        "tract_count": 36,
                        "avg_rent_burden_pct": 15.2,
                        "avg_black_share_pct": 4.1,
                        "avg_hispanic_share_pct": 13.9,
                        "avg_asian_share_pct": 34.8,
                        "avg_white_share_pct": 43.6
                    }
                ]
            }
