"""Data access. Two backends with the same interface:

* BigQueryRepo: production. Real AI.EMBED + VECTOR_SEARCH.
* LocalRepo:    repo parquet files + a keyword-similarity stand-in (offline dev/tests).

Firewall: no query or column list here ever selects `audit_*` columns.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any, Protocol

from . import config

COMPLAINT_COLS = [
    "request_id", "metro_area", "block_address", "census_tract_geoid", "property_type",
    "raw_complaint_type", "complaint_narrative", "inspection_status", "created_date",
    "closed_date", "latitude", "longitude", "data_provenance",
]
ACS_COLS = [  # deliberately excludes every audit_* column
    "census_tract_geoid", "metro_area", "county_name", "total_households", "renter_occupied_units",
    "median_household_income", "median_gross_rent", "renter_hh_rent_30_to_49_pct_count",
    "renter_hh_rent_50_pct_plus_count", "poverty_rate", "no_vehicle_rate", "latitude", "longitude",
    "data_provenance",
]
FILING_COLS = [
    "census_tract_geoid", "metro_area", "reporting_quarter", "nonpayment_filings_count",
    "holdover_or_no_fault_filings_count", "default_judgments_count", "data_provenance",
]
BULLETIN_COLS = [
    "bulletin_id", "metro_area", "program_name", "administering_agency", "funding_stream",
    "requires_open_habitability_case", "residential_tenants_only", "raw_bulletin_text", "intake_url",
    "effective_date",
]
STATUTE_COLS = [
    "statute_section_id", "metro_area", "jurisdiction", "code_citation", "ordinance_title", "raw_statute_text",
]


class Repo(Protocol):
    retrieval_mode: str

    def complaints(self) -> list[dict]: ...
    def acs(self) -> list[dict]: ...
    def filings_annual(self) -> dict[str, dict]: ...
    def bulletins(self) -> list[dict]: ...
    def statutes(self) -> list[dict]: ...
    def vector_candidates(self, query: str, top_k: int) -> list[dict]: ...


def _iso(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v)
    return None if s in ("", "NaT", "None", "nan") else s[:10]


def _clean_complaint(r: dict) -> dict:
    r = dict(r)
    r["census_tract_geoid"] = str(r["census_tract_geoid"])
    r["created_date"] = _iso(r.get("created_date"))
    r["closed_date"] = _iso(r.get("closed_date"))
    return r


def _aggregate_filings(rows: list[dict]) -> dict[str, dict]:
    """Sum the 4 quarterly rows per tract BEFORE anything joins to them (no 4x fan-out)."""
    out: dict[str, dict] = {}
    for r in rows:
        g = str(r["census_tract_geoid"])
        a = out.setdefault(g, {"census_tract_geoid": g, "quarters": 0, "annual_nonpayment": 0,
                               "annual_no_fault": 0, "annual_defaults": 0,
                               "data_provenance": r.get("data_provenance", "")})
        a["quarters"] += 1
        a["annual_nonpayment"] += int(r["nonpayment_filings_count"])
        a["annual_no_fault"] += int(r["holdover_or_no_fault_filings_count"])
        a["annual_defaults"] += int(r["default_judgments_count"])
    for a in out.values():
        a["annual_total"] = a["annual_nonpayment"] + a["annual_no_fault"]
    return out


# ---------------------------------------------------------------------------
# Local backend (offline)
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"[a-z]+")
_STOP = set("a an the and or of to in on at for with is are was were be been has have had this that it its "
            "from by as not no caller tenant unit".split())
# Small synonym map so the offline stand-in behaves roughly like semantic search.
_SYN = {"radiator": "heat", "radiators": "heat", "heater": "heat", "heating": "heat", "cold": "heat",
        "freezing": "heat", "boiler": "heat", "degrees": "heat", "leak": "water", "leaking": "water",
        "dripping": "water", "drip": "water", "flood": "water", "wet": "water", "fuse": "electrical",
        "breaker": "electrical", "wiring": "electrical", "outlet": "electrical", "outlets": "electrical",
        "electric": "electrical", "sparking": "electrical", "mould": "mold", "mildew": "mold",
        "roaches": "pests", "mice": "pests", "rats": "pests", "rodents": "pests", "bedbugs": "pests"}


def _tokens(text: str) -> Counter:
    words = [_SYN.get(w, w) for w in _TOKEN.findall((text or "").lower())]
    return Counter(w for w in words if w not in _STOP and len(w) > 2)


def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class LocalRepo:
    retrieval_mode = "local-keyword-standin (offline only, NOT vector search)"

    def __init__(self, data_dir=None, metro: str | None = None):
        self.dir = data_dir or config.LOCAL_DATA_DIR
        self.metro = metro or config.METRO

    def _read(self, name: str, cols: list[str]) -> list[dict]:
        import pandas as pd

        df = pd.read_parquet(self.dir / f"{name}.parquet", columns=cols)
        df = df[df["metro_area"] == self.metro]
        df = df.astype(object).where(df.notna(), None)
        return df.to_dict("records")

    @lru_cache(maxsize=1)
    def complaints(self) -> list[dict]:
        return [_clean_complaint(r) for r in self._read("municipal_311_housing_complaints", COMPLAINT_COLS)]

    @lru_cache(maxsize=1)
    def acs(self) -> list[dict]:
        rows = self._read("acs_tract_housing_tenure", ACS_COLS)
        for r in rows:
            r["census_tract_geoid"] = str(r["census_tract_geoid"])
        return rows

    @lru_cache(maxsize=1)
    def filings_annual(self) -> dict[str, dict]:
        return _aggregate_filings(self._read("court_eviction_filings", FILING_COLS))

    @lru_cache(maxsize=1)
    def bulletins(self) -> list[dict]:
        return self._read("rental_relief_program_bulletins", BULLETIN_COLS)

    @lru_cache(maxsize=1)
    def statutes(self) -> list[dict]:
        return self._read("municipal_housing_ordinance_statutes", STATUTE_COLS)

    def vector_candidates(self, query: str, top_k: int) -> list[dict]:
        q = _tokens(query)
        scored = []
        for r in self.complaints():
            sim = _cosine(q, _tokens(f"{r['complaint_narrative']} {r['raw_complaint_type']}"))
            scored.append({**r, "cosine_distance": round(1.0 - sim, 4)})
        scored.sort(key=lambda r: r["cosine_distance"])
        return scored[:top_k]


# ---------------------------------------------------------------------------
# BigQuery backend (production)
# ---------------------------------------------------------------------------
class BigQueryRepo:
    retrieval_mode = "bigquery AI.EMBED + VECTOR_SEARCH (cosine, brute force)"

    def __init__(self, project: str | None = None, dataset: str | None = None, metro: str | None = None):
        from google.cloud import bigquery

        self.bq = bigquery
        self.project = project or config.PROJECT
        self.dataset = dataset or config.DATASET          # shared source tables (read only)
        self.own_dataset = config.OWN_DATASET             # our embeddings
        self.metro = metro or config.METRO
        self.client = bigquery.Client(project=self.project or None, location=config.BQ_LOCATION)

    def _t(self, table: str) -> str:
        return f"`{self.project}.{self.dataset}.{table}`"

    def _own(self, table: str) -> str:
        return f"`{self.project}.{self.own_dataset}.{table}`"

    def _query(self, sql: str, params: list | None = None) -> list[dict]:
        job = self.client.query(sql, job_config=self.bq.QueryJobConfig(query_parameters=params or []))
        return [dict(r) for r in job.result()]

    def _metro_param(self):
        return [self.bq.ScalarQueryParameter("metro", "STRING", self.metro)]

    def _select(self, table: str, cols: list[str]) -> list[dict]:
        return self._query(f"SELECT {', '.join(cols)} FROM {self._t(table)} WHERE metro_area = @metro",
                           self._metro_param())

    @lru_cache(maxsize=1)
    def complaints(self) -> list[dict]:
        return [_clean_complaint(r) for r in self._select("municipal_311_housing_complaints", COMPLAINT_COLS)]

    @lru_cache(maxsize=1)
    def acs(self) -> list[dict]:
        rows = self._select("acs_tract_housing_tenure", ACS_COLS)
        for r in rows:
            r["census_tract_geoid"] = str(r["census_tract_geoid"])
        return rows

    @lru_cache(maxsize=1)
    def filings_annual(self) -> dict[str, dict]:
        return _aggregate_filings(self._select("court_eviction_filings", FILING_COLS))

    @lru_cache(maxsize=1)
    def bulletins(self) -> list[dict]:
        return self._select("rental_relief_program_bulletins", BULLETIN_COLS)

    @lru_cache(maxsize=1)
    def statutes(self) -> list[dict]:
        return self._select("municipal_housing_ordinance_statutes", STATUTE_COLS)

    def vector_candidates(self, query: str, top_k: int) -> list[dict]:
        # Pre-filter by metro only (scope, not eligibility). Eligibility rules run in Python
        # AFTER the search so excluded look-alikes keep their reasons.
        # Join back to the full 311 table so lat/lng and citation fields are always present.
        cols = ", ".join(f"c.{c}" for c in COMPLAINT_COLS)
        sql = f"""
        SELECT {cols}, vs.distance AS cosine_distance
        FROM VECTOR_SEARCH(
          (SELECT request_id, embedding FROM {self._own('complaints_embedded')} WHERE metro_area = @metro),
          'embedding',
          (SELECT AI.EMBED(@query, connection_id => '{config.VERTEX_CONNECTION}',
                           endpoint => '{config.EMBED_ENDPOINT}').result AS query_vec),
          query_column_to_search => 'query_vec',
          top_k => {int(top_k)},
          distance_type => 'COSINE',
          options => '{{"use_brute_force": true}}'
        ) AS vs
        JOIN {self._t('municipal_311_housing_complaints')} AS c ON c.request_id = vs.base.request_id
        ORDER BY vs.distance
        """
        params = self._metro_param() + [self.bq.ScalarQueryParameter("query", "STRING", query)]
        return [_clean_complaint(r) for r in self._query(sql, params)]


@lru_cache(maxsize=1)
def get_repo() -> Repo:
    return BigQueryRepo() if config.DATA_MODE == "bigquery" else LocalRepo()
