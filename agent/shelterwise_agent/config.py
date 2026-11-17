"""Configuration, metro registry, and ADK ToolContext bridge for ShelterWise."""

import os
from dataclasses import dataclass, field
from typing import Any

# Bridge ADK ToolContext cleanly: uses exact google.adk.tools.ToolContext at runtime
# while allowing local pytest / schema imports before google-adk is installed.
try:
    from google.adk.tools import ToolContext  # type: ignore[import-not-found]
except ImportError:

    @dataclass
    class ToolContext:  # type: ignore[no-redef]
        """Lightweight fallback matching google.adk.tools.ToolContext.state for local tests."""

        state: dict[str, Any] = field(default_factory=dict)


# Official 6-metro registry from A4I2026-challenge-housing:
# metro_name -> (state_code, state_fips_2char, metro_slug, default_courthouse_name, ch_lat, ch_lon)
OFFICIAL_METROS: dict[str, tuple[str, str, str, str, float, float]] = {
    "San Francisco": (
        "CA",
        "06",
        "san-francisco",
        "San Francisco Civic Center Courthouse (400 McAllister St, San Francisco, CA 94102)",
        37.7808,
        -122.4175,
    ),
    "Chicago": (
        "IL",
        "17",
        "chicago",
        "Richard J. Daley Center (50 W Washington St, Chicago, IL 60602)",
        41.8837,
        -87.6302,
    ),
    "New York": (
        "NY",
        "36",
        "new-york",
        "New York County Housing Court (111 Centre St, New York, NY 10013)",
        40.7165,
        -74.0014,
    ),
    "Austin": (
        "TX",
        "48",
        "austin",
        "Travis County Civil & Family Courts Facility (1700 Guadalupe St, Austin, TX 78701)",
        30.2797,
        -97.7445,
    ),
    "Baton Rouge": (
        "LA",
        "22",
        "baton-rouge",
        "Baton Rouge City Court (233 St Louis St, Baton Rouge, LA 70802)",
        30.4465,
        -91.1874,
    ),
    "Cincinnati": (
        "OH",
        "39",
        "cincinnati",
        "Hamilton County Courthouse (1000 Main St, Cincinnati, OH 45202)",
        39.1072,
        -84.5105,
    ),
}

_METRO_ALIASES: dict[str, str] = {
    "sf": "San Francisco",
    "sfo": "San Francisco",
    "san francisco": "San Francisco",
    "san-francisco": "San Francisco",
    "chicago": "Chicago",
    "chi": "Chicago",
    "new york": "New York",
    "new-york": "New York",
    "nyc": "New York",
    "ny": "New York",
    "austin": "Austin",
    "atx": "Austin",
    "baton rouge": "Baton Rouge",
    "baton-rouge": "Baton Rouge",
    "cincinnati": "Cincinnati",
}

AUDIT_FORBIDDEN_COLUMNS: frozenset[str] = frozenset(
    {
        "audit_black_share",
        "audit_hispanic_share",
        "audit_asian_share",
        "audit_indigenous_share",
        "audit_white_share",
        "audit_black_pct",
        "audit_hispanic_pct",
        "audit_asian_pct",
        "audit_indigenous_pct",
        "audit_white_pct",
    }
)


@dataclass(frozen=True)
class ShelterWiseSettings:
    """Runtime settings resolved from environment variables."""

    project_id: str
    dataset: str
    location: str
    default_metro: str
    vertex_connection: str
    embedding_endpoint: str
    complaints_embedded_table: str
    tract_view_name: str
    backend_mode: str  # "auto" | "bigquery" | "fixture"
    model_name: str

    @property
    def dataset_fqn(self) -> str:
        if self.project_id:
            return f"{self.project_id}.{self.dataset}"
        return self.dataset


def get_settings() -> ShelterWiseSettings:
    """Load current settings from environment."""
    return ShelterWiseSettings(
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip(),
        dataset=os.environ.get("A4I_DATASET", "a4i_housing").strip(),
        location=os.environ.get("A4I_LOCATION", "US").strip(),
        default_metro=resolve_metro_name(
            os.environ.get("SHELTERWISE_METRO", "San Francisco")
        ),
        vertex_connection=os.environ.get(
            "A4I_VERTEX_CONNECTION", "us.a4i-vertex"
        ).strip(),
        embedding_endpoint=os.environ.get(
            "A4I_EMBEDDING_MODEL", "gemini-embedding-2"
        ).strip(),
        complaints_embedded_table=os.environ.get(
            "A4I_COMPLAINTS_EMBEDDED_TABLE", "complaints_embedded"
        ).strip(),
        tract_view_name=os.environ.get(
            "A4I_TRACT_VIEW", "v_tract_stability_context"
        ).strip(),
        backend_mode=os.environ.get("SHELTERWISE_BACKEND", "auto").strip().lower(),
        model_name=os.environ.get("SHELTERWISE_MODEL", "gemini-2.5-flash").strip(),
    )


def resolve_metro_name(raw_metro: str | None) -> str:
    """Normalize a metro name or alias to one of the 6 canonical challenge metros."""
    if not raw_metro or not raw_metro.strip():
        return "San Francisco"
    cleaned = raw_metro.strip()
    if cleaned in OFFICIAL_METROS:
        return cleaned
    lowered = cleaned.lower().replace("_", "-")
    if lowered in _METRO_ALIASES:
        return _METRO_ALIASES[lowered]
    # Check partial match like "San Francisco, CA"
    base = lowered.split(",")[0].strip()
    if base in _METRO_ALIASES:
        return _METRO_ALIASES[base]
    raise ValueError(
        f"Unsupported metro {raw_metro!r}. Must be one of: {list(OFFICIAL_METROS.keys())}"
    )


def get_metro_metadata(raw_metro: str | None) -> dict[str, Any]:
    """Return canonical metadata for a metro."""
    metro = resolve_metro_name(raw_metro)
    state_code, state_fips, slug, courthouse, ch_lat, ch_lon = OFFICIAL_METROS[metro]
    return {
        "metro": metro,
        "state_code": state_code,
        "state_fips": state_fips,
        "metro_slug": slug,
        "courthouse_name": courthouse,
        "courthouse_lat": ch_lat,
        "courthouse_lon": ch_lon,
    }


def normalize_geoid_11(raw_geoid: str | int | None) -> str:
    """Preserve 11-character string census tract GEOIDs (including SF '06' leading zero).

    Returns empty string if raw_geoid is None or blank.
    Raises ValueError if non-empty input is non-numeric or exceeds 11 digits.
    """
    if raw_geoid is None:
        return ""
    s = str(raw_geoid).strip()
    if not s:
        return ""
    if not s.isdigit():
        raise ValueError(
            f"Invalid census_tract_geoid {raw_geoid!r}: expected digits only (11-char FIPS string)."
        )
    if len(s) > 11:
        raise ValueError(
            f"Invalid census_tract_geoid {raw_geoid!r}: expected at most 11 digits, got {len(s)}."
        )
    if len(s) < 10:
        raise ValueError(
            f"Invalid census_tract_geoid {raw_geoid!r}: expected 10 or 11 digits, got {len(s)}."
        )
    return s.zfill(11)
