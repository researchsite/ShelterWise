from shelterwise_agent.schemas import PolicyPack, PolicyRecord
from shelterwise_agent.db.bigquery_client import BQClient
from shelterwise_agent.config import METRO

def fetch_statutes_and_bulletins() -> dict:
    """Fetches statutes and rental relief bulletins for the metro area."""
    bq = BQClient()
    statutes, bulletins = bq.get_statutes_and_bulletins(METRO)
    
    statute_records = []
    for s in statutes:
        statute_records.append(PolicyRecord(
            title=s.ordinance_title,
            citation=s.code_citation,
            summary=s.raw_statute_text
        ))
        
    fund_records = []
    for b in bulletins:
        fund_records.append(PolicyRecord(
            title=b.program_name,
            citation=b.intake_url,
            summary=b.raw_bulletin_text,
            requires_open_habitability_case=b.requires_open_habitability_case
        ))
        
    pack = PolicyPack(
        applicable_statutes=statute_records,
        applicable_relief_funds=fund_records,
        pre_hearing_defenses_noted=True
    )
    return pack.model_dump()
