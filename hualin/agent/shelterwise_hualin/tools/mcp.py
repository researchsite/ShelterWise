"""BigQuery remote MCP server (Google-managed), read-only, with an audit_* firewall.

Endpoint confirmed in Google docs: https://bigquery.googleapis.com/mcp
(enabled with the BigQuery API; OAuth scope .../auth/bigquery).
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from .. import config

READ_ONLY_TOOLS = ["execute_sql_readonly", "list_dataset_ids", "list_table_ids",
                   "get_dataset_info", "get_table_info"]
_SCOPES = ["https://www.googleapis.com/auth/bigquery"]


def _auth_headers(_ctx=None) -> dict[str, str]:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=_SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}
    if config.PROJECT:
        headers["x-goog-user-project"] = config.PROJECT
    return headers


def firewall_reason(tool_name: str, args: dict[str, Any]) -> Optional[str]:
    """Why a BigQuery MCP call must be blocked, or None if it is allowed."""
    if tool_name not in READ_ONLY_TOOLS:
        return f"Tool '{tool_name}' is not on the read-only allow list."
    sql = json.dumps(args).lower()
    if "audit_" in sql:
        return "Race / ethnicity (audit_*) columns are only used in the offline equity audit."
    if "acs_tract_housing_tenure" in sql and re.search(r"select\s+(\w+\.)?\*", sql):
        return "SELECT * on acs_tract_housing_tenure would return audit_* columns; list columns explicitly."
    return None


def mcp_firewall_callback(tool, args: dict[str, Any], tool_context) -> Optional[dict]:
    """ADK before_tool_callback: returning a dict skips the tool call."""
    try:
        from google.adk.tools.mcp_tool import McpTool
    except ImportError:
        return None
    if not isinstance(tool, McpTool):
        return None  # our own function tools pass through
    reason = firewall_reason(tool.name, args)
    return {"error": f"Blocked by ShelterWise policy: {reason}"} if reason else None


def build_bigquery_mcp_toolset():
    if not config.ENABLE_MCP:
        return None
    from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=config.BIGQUERY_MCP_URL, timeout=30.0),
        tool_filter=READ_ONLY_TOOLS,
        header_provider=_auth_headers,
    )
