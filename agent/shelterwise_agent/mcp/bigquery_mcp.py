"""Managed BigQuery MCPToolset integration.

Connects to Google-managed BigQuery MCP server (https://bigquery.googleapis.com/mcp)
or provides tools for ad-hoc SQL queries and schema inspection.
"""

from typing import Optional
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from shelterwise_agent.config import get_settings

BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"

def get_bigquery_mcp_toolset(project_id: Optional[str] = None) -> McpToolset:
    """Initializes and returns the Google-managed BigQuery MCPToolset."""
    settings = get_settings()
    resolved_project = project_id or settings.project_id or "qwiklabs-gcp-04-99fa355171e1"
    params = StreamableHTTPConnectionParams(
        url=BIGQUERY_MCP_URL,
        headers={"X-Goog-User-Project": resolved_project}
    )
    return McpToolset(connection_params=params)
