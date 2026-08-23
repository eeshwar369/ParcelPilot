from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.schemas import UserContext
from backend.app.data_store import DataStore


def issue_dashboard(store: DataStore, ctx: UserContext) -> dict[str, Any]:
    tickets = [t for t in store.tickets() if t["account_id"] in ctx.allowed_account_ids]
    snapshot = store.snapshot_time()

    sla_risk = []
    for ticket in tickets:
        created = datetime.fromisoformat(ticket["created_at"])
        age_hours = (snapshot - created).total_seconds() / 3600
        if ticket["status"] == "open" and (ticket["severity"] == "high" or age_hours >= 4):
            sla_risk.append({**ticket, "age_hours": round(age_hours, 2), "account_name": store.account_name(ticket["account_id"])})

    categories: dict[str, list[dict[str, Any]]] = {}
    for ticket in tickets:
        categories.setdefault(ticket["category"], []).append(ticket)

    recurring = [
        {
            "category": category,
            "count": len(items),
            "accounts": sorted({store.account_name(item["account_id"]) for item in items}),
            "example": items[0]["summary"],
        }
        for category, items in categories.items()
        if len(items) >= 2
    ]

    return {
        "snapshot_time": snapshot.isoformat(),
        "sla_risk": sorted(sla_risk, key=lambda item: item["age_hours"], reverse=True),
        "recurring_issues": recurring,
        "summary": {
            "open_tickets": len([t for t in tickets if t["status"] == "open"]),
            "high_severity": len([t for t in tickets if t["severity"] == "high"]),
            "recurring_issue_groups": len(recurring),
        },
    }
