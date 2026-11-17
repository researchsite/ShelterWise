"""
Google-Managed BigQuery MCP Integration and Safe Query Execution.
Connects to BigQuery MCP endpoint or provides safe parameterized query execution.
"""
from typing import Dict, Any, List
from shelterwise_agent.config import PROJECT_ID, DATASET
from shelterwise_agent.db.bigquery_client import BQClient

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

def get_bigquery_mcp_toolset(project_id: str = None):
    """Initializes and returns the Google-managed BigQuery MCPToolset or fallback."""
    try:
        from google.adk.tools import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
        resolved = project_id or PROJECT_ID or "qwiklabs-gcp-04-99fa355171e1"
        params = StreamableHTTPConnectionParams(
            url="https://bigquery.googleapis.com/mcp",
            headers={"X-Goog-User-Project": resolved}
        )
        return McpToolset(connection_params=params)
    except Exception:
        class DummyMcpToolset:
            def __init__(self, pid=None):
                self.project_id = pid or PROJECT_ID
                self.url = "https://bigquery.googleapis.com/mcp"
        return DummyMcpToolset(pid=project_id)
