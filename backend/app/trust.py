AUTHORITY_WEIGHT = {
    "customer_contract": 100,
    "current_sop": 90,
    "current_policy": 80,
    "ops_guide": 65,
    "structured_data": 85,
    "historical_ticket": 30,
    "deprecated_policy": 10,
}


def authority_score(authority: str) -> int:
    return AUTHORITY_WEIGHT.get(authority, 50)


def confidence_from_evidence(has_record: bool, source_count: int, conflict: bool, action: bool = False) -> str:
    if conflict:
        return "low"
    if has_record and source_count >= 2 and not action:
        return "high"
    if source_count >= 2 and not action:
        return "high"
    if source_count >= 1:
        return "medium"
    return "low"


def risk_tier(is_customer: bool, financial_or_sla: bool, conflict: bool, action: bool) -> str:
    if action or conflict:
        return "high"
    if is_customer and financial_or_sla:
        return "high"
    if financial_or_sla:
        return "medium"
    return "low"
