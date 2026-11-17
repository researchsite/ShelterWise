"""
Google-Managed BigQuery MCP Integration and Safe Query Execution.
Connects to BigQuery MCP endpoint or provides safe parameterized query execution.
"""
from typing import Dict, Any, List
from shelterwise_agent.config import PROJECT_ID, DATASET
from shelterwise_agent.db.bigquery_client import BQClient

import inspect
from typing import Optional

import google.auth
from google.auth.transport.requests import Request

BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"
_BQ_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def query_bigquery_mcp(sql_query: str) -> Dict[str, Any]:
    """
    Executes a read-only SQL query against the a4i_housing BigQuery dataset.
    Used by the coordinator agent for ad-hoc paralegal questions.
    """
    bq = BQClient()
    if not bq.client:
        return {"error": "BigQuery client unavailable"}
    
    # Enforce read-only safety guard
    sanitized = sql_query.strip()
    upper = sanitized.upper()
    if any(forbidden in upper for forbidden in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]):
        return {"error": "Modification statements are prohibited. Only SELECT queries are permitted."}

    try:
        results = [dict(r.items()) for r in bq.client.query(sanitized).result()]
        return {"row_count": len(results), "rows": results[:20]}
    except Exception as e:
        return {"error": str(e)}

def get_bigquery_mcp_toolset(project_id: Optional[str] = None):
    """Initializes and returns the Google-managed BigQuery MCPToolset with ADC auth."""
    try:
        from google.adk.tools import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
        
        adc_project = None
        try:
            _, adc_project = google.auth.default(scopes=_BQ_SCOPES)
        except Exception:
            pass
        resolved_project = (
            project_id or PROJECT_ID or adc_project or "qwiklabs-gcp-04-99fa355171e1"
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
    except Exception:
        class DummyMcpToolset:
            def __init__(self, pid=None):
                self.project_id = pid or PROJECT_ID
                self.url = BIGQUERY_MCP_URL
        return DummyMcpToolset(pid=project_id)
