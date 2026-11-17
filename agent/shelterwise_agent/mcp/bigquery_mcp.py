"""Managed BigQuery MCPToolset integration.

Connects to Google-managed BigQuery MCP server (https://bigquery.googleapis.com/mcp)
or provides fallback tools for ad-hoc SQL queries and schema inspection.
"""

from typing import Optional
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from shelterwise_agent.config import PROJECT_ID

BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"

def get_bigquery_mcp_toolset() -> McpToolset:
    """Initializes and returns the Google-managed BigQuery MCPToolset."""
    params = StreamableHTTPConnectionParams(
        url=BIGQUERY_MCP_URL,
        headers={"X-Goog-User-Project": PROJECT_ID}
    )
    return McpToolset(connection_params=params)
