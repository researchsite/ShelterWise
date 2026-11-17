from shelterwise_agent.schemas import StabilizationBrief, IntakeFacts, EvidencePack, PolicyPack, TractContext

def reconcile_gaps_and_generate_brief(
    intake: dict, 
    evidence: dict, 
    policy: dict, 
    tract: dict
) -> dict:
    """Synthesizes parallel outputs into the final Tenant Stabilization Brief."""
    gaps = []
    recommended_funds = []
    
    # Filter funds based on 311 habitability requirement
    has_311 = evidence.get("has_open_residential_311", False)
    for fund in policy.get("applicable_relief_funds", []):
        if fund.get("requires_open_habitability_case") and not has_311:
            gaps.append(f"Fund {fund.get('title')} requires an open 311 case, but none found. Suggest filing 311.")
        else:
            recommended_funds.append(fund)
            
    brief = StabilizationBrief(
        tenant_reported_facts=intake.get("reported_facts", []),
        verified_evidence=evidence.get("corroborating_records", []),
        evidence_gaps=gaps,
        applicable_statutes=policy.get("applicable_statutes", []),
        recommended_relief_funds=recommended_funds,
        tract_context_summary=f"Eviction Activity: {tract.get('annual_filings_total', 0)} annual filings in tract.",
        human_review_flags=[
            "Intake indicates hearing within 72h. Emergency lawyer review required."
        ] if intake.get("hearing_within_72h") else []
    )
    
    return brief.model_dump()
