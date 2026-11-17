"""Managed BigQuery MCPToolset integration.

Connects to Google-managed BigQuery MCP server (https://bigquery.googleapis.com/mcp)
or provides tools for ad-hoc SQL queries and schema inspection.
"""

import inspect
from typing import Optional

import google.auth
from google.auth.transport.requests import Request
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from shelterwise_agent.config import get_settings

BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"
_BQ_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_bigquery_mcp_toolset(project_id: Optional[str] = None) -> McpToolset:
    """Initializes and returns the Google-managed BigQuery MCPToolset with ADC auth."""
    settings = get_settings()
    adc_project = None
    try:
        _, adc_project = google.auth.default(scopes=_BQ_SCOPES)
    except Exception:
        pass
    resolved_project = (
        project_id or settings.project_id or adc_project or "qwiklabs-gcp-04-99fa355171e1"
    )
    cached_auth = {"creds": None, "request": None}

    def _header_provider(_context=None) -> dict[str, str]:
        headers = {"x-goog-user-project": resolved_project}
        try:
            if cached_auth["creds"] is None:
                creds, _ = google.auth.default(scopes=_BQ_SCOPES)
                cached_auth["creds"] = creds
                cached_auth["request"] = Request()
            creds = cached_auth["creds"]
            if not creds.valid or not creds.token:
                creds.refresh(cached_auth["request"])
            if creds.token:
                headers["Authorization"] = f"Bearer {creds.token}"
        except Exception:
            pass
        return headers

    params = StreamableHTTPConnectionParams(
        url=BIGQUERY_MCP_URL,
        headers={"x-goog-user-project": resolved_project},
    )
    if "header_provider" in inspect.signature(McpToolset.__init__).parameters:
        return McpToolset(connection_params=params, header_provider=_header_provider)
    return McpToolset(connection_params=params)
