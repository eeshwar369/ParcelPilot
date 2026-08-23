from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json
import re
import uuid

from backend.app.schemas import PendingAction


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
STATE_FILE = PROCESSED_DIR / "state.json"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _demo_documents() -> list[dict[str, Any]]:
    return [
        {
            "id": "doc_policy_current",
            "name": "Support Policy v3 CURRENT",
            "source_type": "support_policy",
            "authority": "current_policy",
            "status": "current",
            "account_id": None,
            "page": 1,
            "text": "Current support policy: Enterprise accounts receive priority support. SLA review is required for high severity operational incidents. Historical ticket resolutions are context only and must not override current policy.",
        },
        {
            "id": "doc_policy_deprecated",
            "name": "Support Policy v2 DEPRECATED",
            "source_type": "support_policy",
            "authority": "deprecated_policy",
            "status": "deprecated",
            "account_id": None,
            "page": 1,
            "text": "Deprecated support policy: older cancellation and service credit rules may differ. Do not use this policy as the primary authority.",
        },
        {
            "id": "doc_cancel_sop",
            "name": "Cancellation and Service Credit SOP v4",
            "source_type": "sop",
            "authority": "current_sop",
            "status": "current",
            "account_id": None,
            "page": 2,
            "text": "Cancellation SOP v4: cancellation fee is waived when a qualifying enterprise agreement overrides the default fee, or when carrier fault causes a confirmed pickup delay of at least two hours. Service credit requires carrier fault, documented delay, and no customer-caused exception.",
        },
        {
            "id": "doc_known_issues",
            "name": "Product Operations Guide and Known Issues",
            "source_type": "operations_guide",
            "authority": "ops_guide",
            "status": "current",
            "account_id": None,
            "page": 4,
            "text": "Known issue: carrier webhook delays can show shipments as pending even after pickup. Operations should verify carrier event logs before denying a customer report.",
        },
        {
            "id": "doc_northstar_agreement",
            "name": "Northstar Logistics Enterprise Agreement",
            "source_type": "customer_agreement",
            "authority": "customer_contract",
            "status": "current",
            "account_id": "ACCT-001",
            "page": 3,
            "text": "Northstar enterprise agreement: Northstar may cancel priority shipments without cancellation fee when cancellation is requested before carrier dispatch or when ParcelPilot/carrier fault delays pickup by more than two hours. This customer agreement overrides general cancellation policy.",
        },
        {
            "id": "doc_lumenworks_agreement",
            "name": "LumenWorks Service Agreement",
            "source_type": "customer_agreement",
            "authority": "customer_contract",
            "status": "current",
            "account_id": "ACCT-002",
            "page": 2,
            "text": "LumenWorks service agreement: standard cancellation terms apply unless a support manager approves an exception. Service credits are capped at the shipment service fee.",
        },
    ]


def _demo_state() -> dict[str, Any]:
    snapshot = datetime(2026, 8, 22, 6, 30, tzinfo=timezone.utc)
    return {
        "snapshot_time": snapshot.isoformat(),
        "accounts": [
            {"id": "ACCT-001", "name": "Northstar Logistics", "tier": "enterprise"},
            {"id": "ACCT-002", "name": "LumenWorks", "tier": "growth"},
            {"id": "ACCT-003", "name": "Beacon Retail", "tier": "standard"},
            {"id": "ACCT-004", "name": "Axis Labs", "tier": "enterprise"},
        ],
        "orders": [
            {
                "id": "ORD-1001",
                "account_id": "ACCT-001",
                "carrier": "FastFreight",
                "service_level": "priority",
                "status": "pickup_delayed",
                "carrier_fault": True,
                "scheduled_pickup_at": (snapshot - timedelta(hours=4)).isoformat(),
                "actual_pickup_at": None,
                "cancellation_requested_at": (snapshot - timedelta(minutes=30)).isoformat(),
            },
            {
                "id": "ORD-2002",
                "account_id": "ACCT-002",
                "carrier": "MetroShip",
                "service_level": "standard",
                "status": "in_transit",
                "carrier_fault": False,
                "scheduled_pickup_at": (snapshot - timedelta(hours=1)).isoformat(),
                "actual_pickup_at": (snapshot - timedelta(minutes=45)).isoformat(),
                "cancellation_requested_at": None,
            },
        ],
        "tickets": [
            {
                "id": "TKT-501",
                "account_id": "ACCT-001",
                "order_id": "ORD-1001",
                "category": "pickup_delay",
                "severity": "high",
                "status": "open",
                "created_at": (snapshot - timedelta(hours=5)).isoformat(),
                "summary": "Pickup is more than three hours late; customer asks for cancellation fee waiver.",
            },
            {
                "id": "TKT-502",
                "account_id": "ACCT-002",
                "order_id": "ORD-2002",
                "category": "tracking_status",
                "severity": "medium",
                "status": "open",
                "created_at": (snapshot - timedelta(hours=2)).isoformat(),
                "summary": "Tracking page did not update after pickup.",
            },
            {
                "id": "TKT-503",
                "account_id": "ACCT-003",
                "order_id": None,
                "category": "tracking_status",
                "severity": "medium",
                "status": "open",
                "created_at": (snapshot - timedelta(hours=1)).isoformat(),
                "summary": "Carrier webhook pending status appears stale.",
            },
        ],
        "documents": _demo_documents(),
        "pending_actions": [],
        "escalations": [],
        "audit_events": [],
        "model_usage_events": [],
    }


class DataStore:
    def __init__(self) -> None:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        if not STATE_FILE.exists():
            self.state = _demo_state()
            self.save()
        else:
            self.state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    def save(self) -> None:
        STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def snapshot_time(self) -> datetime:
        raw = str(self.state["snapshot_time"])
        if raw.endswith(" Asia/Kolkata"):
            naive = datetime.fromisoformat(raw.replace(" Asia/Kolkata", ""))
            return naive.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        return datetime.fromisoformat(raw)

    def account_name(self, account_id: str) -> str:
        account = self.get_account(account_id)
        return (account.get("name") or account.get("account_name") or account_id) if account else account_id

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        return next((a for a in self.state["accounts"] if a["id"] == account_id or a.get("account_id") == account_id), None)

    def find_account_by_name(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower()
        return next((a for a in self.state["accounts"] if (a.get("name") or a.get("account_name") or "").lower().split()[0] in lowered or (a.get("id") or a.get("account_id") or "").lower() in lowered), None)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return next((o for o in self.state["orders"] if o["id"].lower() == order_id.lower()), None)

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        return next((t for t in self.state["tickets"] if t["id"].lower() == ticket_id.lower()), None)

    def tickets(self) -> list[dict[str, Any]]:
        return list(self.state["tickets"])

    def documents(self) -> list[dict[str, Any]]:
        return list(self.state["documents"])

    def add_pending_action(self, action: PendingAction) -> None:
        self.state["pending_actions"].append(asdict(action))
        self.save()

    def get_pending_action(self, action_id: str) -> dict[str, Any] | None:
        return next((a for a in self.state["pending_actions"] if a["id"] == action_id and a["status"] == "pending"), None)

    def create_escalation(self, pending: dict[str, Any]) -> dict[str, Any]:
        escalation = {
            "id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
            "ticket_id": pending["payload"].get("ticket_id"),
            "account_id": pending["account_id"],
            "reason": pending["payload"].get("reason"),
            "priority": pending["payload"].get("priority", "medium"),
            "created_by": pending["created_by"],
            "created_at": utcnow().isoformat(),
            "status": "open",
        }
        self.state["escalations"].append(escalation)
        for item in self.state["pending_actions"]:
            if item["id"] == pending["id"]:
                item["status"] = "executed"
        self.save()
        return escalation

    def escalations(self) -> list[dict[str, Any]]:
        return list(self.state.get("escalations", []))

    def pending_actions(self) -> list[dict[str, Any]]:
        return list(self.state.get("pending_actions", []))

    def verify_escalation(self, escalation_id: str, verifier_id: str, status: str = "verified") -> dict[str, Any]:
        escalation = next((item for item in self.state["escalations"] if item["id"] == escalation_id), None)
        if not escalation:
            raise ValueError("Escalation was not found.")
        escalation["status"] = status
        escalation["verified_by"] = verifier_id
        escalation["verified_at"] = utcnow().isoformat()
        self.save()
        return escalation

    def respond_escalation(self, escalation_id: str, responder_id: str, message: str) -> dict[str, Any]:
        escalation = next((item for item in self.state["escalations"] if item["id"] == escalation_id), None)
        if not escalation:
            raise ValueError("Escalation was not found.")
        if not message.strip():
            raise ValueError("Response message is required.")
        escalation["status"] = "responded"
        escalation["response"] = message.strip()
        escalation["responded_by"] = responder_id
        escalation["responded_at"] = utcnow().isoformat()
        self.save()
        return escalation

    def audit(self, event: dict[str, Any]) -> None:
        event.setdefault("id", uuid.uuid4().hex)
        event.setdefault("created_at", utcnow().isoformat())
        self.state["audit_events"].append(event)
        self.save()

    def model_usage(self, event: dict[str, Any]) -> None:
        event.setdefault("id", uuid.uuid4().hex)
        event.setdefault("created_at", utcnow().isoformat())
        self.state["model_usage_events"].append(event)
        self.save()


def extract_ids(text: str) -> dict[str, list[str]]:
    return {
        "orders": sorted(set(re.findall(r"\bORD-\d+\b", text, flags=re.I))),
        "tickets": sorted(set(re.findall(r"\bTK[CT]-\d+\b", text, flags=re.I))),
    }
