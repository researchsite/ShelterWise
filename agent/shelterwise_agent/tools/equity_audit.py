from typing import Dict, Any
from shelterwise_agent.db.bigquery_client import BQClient

def run_metro_equity_audit() -> Dict[str, Any]:
    """
    Executes aggregate post-output Responsible AI cohort query on v_metro_equity_audit.
    Compares 311-reporting tracts against silent distress candidate tracts
    joined to census demographic shares and vehicle access rates.
    
    FIREWALL RULE: This tool is strictly aggregated across tracts and NEVER
    processes individual tenant identities or scores individuals.
    """
    bq = BQClient()
    return bq.run_equity_audit()
