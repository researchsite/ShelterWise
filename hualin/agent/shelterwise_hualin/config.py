"""Runtime configuration. Everything is overridable by environment variables."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # hualin/agent/shelterwise_hualin/config.py

# --- Google Cloud -----------------------------------------------------------
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
# Shared team source tables: READ ONLY, never written by this version.
DATASET = os.getenv("A4I_DATASET", "a4i_housing")
# Hualin's own dataset for everything this version creates (embeddings, views).
# Keeps us from overwriting teammates' objects in the shared project.
OWN_DATASET = os.getenv("HUALIN_DATASET", "hualin_shelterwise")
# Prefix for every Cloud Run / Agent Runtime resource this version deploys.
DEPLOY_PREFIX = os.getenv("HUALIN_DEPLOY_PREFIX", "hualin-shelterwise")
BQ_LOCATION = os.getenv("A4I_LOCATION", "US")
VERTEX_CONNECTION = os.getenv("A4I_VERTEX_CONNECTION", "us.a4i-vertex")
EMBED_ENDPOINT = os.getenv("A4I_EMBED_ENDPOINT", "gemini-embedding-2")

# --- Scope --------------------------------------------------------------------
METRO = os.getenv("SHELTERWISE_METRO", "San Francisco")

# "bigquery" = real AI.EMBED + VECTOR_SEARCH (required for the demo).
# "local"    = repo parquet files + a keyword-similarity stand-in, for offline
#              development and tests only. Every result is labeled with its mode.
DATA_MODE = os.getenv("SHELTERWISE_DATA", "local").lower()
LOCAL_DATA_DIR = Path(os.getenv("SHELTERWISE_LOCAL_DATA", str(REPO_ROOT / "data")))

# --- Models ------------------------------------------------------------------
MODEL_FAST = os.getenv("SHELTERWISE_MODEL_FAST", "gemini-2.5-flash")
MODEL_STRONG = os.getenv("SHELTERWISE_MODEL_STRONG", "gemini-2.5-pro")

# --- Retrieval rules ---------------------------------------------------------
RADIUS_M = float(os.getenv("SHELTERWISE_RADIUS_M", "400"))
TOP_K = int(os.getenv("SHELTERWISE_TOP_K", "50"))
KEEP_MAX = int(os.getenv("SHELTERWISE_KEEP_MAX", "5"))
URGENT_HEARING_DAYS = int(os.getenv("SHELTERWISE_URGENT_DAYS", "7"))

# --- Optional integrations ---------------------------------------------------
ENABLE_MCP = os.getenv("SHELTERWISE_ENABLE_MCP", "false").lower() == "true"
BIGQUERY_MCP_URL = os.getenv("BIGQUERY_MCP_URL", "https://bigquery.googleapis.com/mcp")
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


def today() -> date:
    """Intake date. SHELTERWISE_TODAY=YYYY-MM-DD pins it for demos and tests."""
    pinned = os.getenv("SHELTERWISE_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()
