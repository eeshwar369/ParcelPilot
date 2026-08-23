from __future__ import annotations

from datetime import datetime
from typing import Any
import math
import uuid

from backend.app.auth import require_account_access, require_action
from backend.app.data_store import DataStore
from backend.app.schemas import PendingAction, Source, ToolTrace, UserContext
from backend.app.trust import authority_score
from backend.app.vector_store import create_vector_store, tokenize


class Tools:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.vector_store = create_vector_store()

    def document_search(self, ctx: UserContext, query: str, include_deprecated: bool = False) -> tuple[list[Source], ToolTrace]:
        allowed_documents = []
        query_terms = set(tokenize(query))
        results: list[Source] = []
        for doc in self.store.documents():
            if doc.get("account_id") and doc["account_id"] not in ctx.allowed_account_ids:
                continue
            if doc["status"] == "deprecated" and not include_deprecated:
                continue
            allowed_documents.append(doc)
        for doc, vector_score in self.vector_store.search(allowed_documents, query, limit=8):
            terms = set(tokenize(doc["text"] + " " + doc["name"]))
            overlap = len(query_terms & terms)
            score = vector_score + (overlap / 10) + authority_score(doc["authority"]) / 100
            results.append(
                Source(
                    name=doc["name"],
                    source_type=doc["source_type"],
                    authority=doc["authority"],
                    status=doc["status"],
                    page=doc.get("page"),
                    account_id=doc.get("account_id"),
                    score=score,
                    excerpt=doc["text"][:500],
                )
            )
        results.sort(key=lambda src: src.score, reverse=True)
        provider = getattr(self.vector_store, "provider_name", "vector")
        return results[:5], ToolTrace("document_search", "ok", f"Found {len(results[:5])} relevant document chunks with {provider} retrieval.")

    def lookup_order(self, ctx: UserContext, order_id: str) -> tuple[dict[str, Any] | None, ToolTrace]:
        order = self.store.get_order(order_id)
        if not order:
            return None, ToolTrace("lookup_order", "not_found", f"Order {order_id} was not found.")
        require_account_access(ctx, order["account_id"])
        return order, ToolTrace("lookup_order", "ok", f"Loaded order {order_id} for {self.store.account_name(order['account_id'])}.")

    def lookup_ticket(self, ctx: UserContext, ticket_id: str) -> tuple[dict[str, Any] | None, ToolTrace]:
        ticket = self.store.get_ticket(ticket_id)
        if not ticket:
            return None, ToolTrace("lookup_ticket", "not_found", f"Ticket {ticket_id} was not found.")
        require_account_access(ctx, ticket["account_id"])
        return ticket, ToolTrace("lookup_ticket", "ok", f"Loaded ticket {ticket_id}.")

    def search_tickets(self, ctx: UserContext, severity: str | None = None) -> tuple[list[dict[str, Any]], ToolTrace]:
        tickets = [t for t in self.store.tickets() if t["account_id"] in ctx.allowed_account_ids]
        if severity:
            tickets = [t for t in tickets if t["severity"].lower() == severity.lower()]
        return tickets, ToolTrace("search_tickets", "ok", f"Found {len(tickets)} authorized tickets.")

    def calculate_policy_outcome(self, ctx: UserContext, order: dict[str, Any] | None) -> tuple[dict[str, Any], ToolTrace]:
        if not order:
            return {"eligible": None, "reason": "Order was not found."}, ToolTrace("calculate_policy_outcome", "skipped", "Missing order.")
        require_account_access(ctx, order["account_id"])
        snapshot = self.store.snapshot_time()
        scheduled_raw = order.get("scheduled_pickup_at")
        delay_hours = 0.0
        if scheduled_raw:
            scheduled = self._parse_like_snapshot(scheduled_raw, snapshot)
            delay_hours = max(0.0, (snapshot - scheduled).total_seconds() / 3600)
        carrier_fault = bool(order.get("carrier_fault"))
        service_credit_eligible = carrier_fault and delay_hours >= 2

        status = str(order.get("status") or "").upper()
        booked_not_picked_up = status == "BOOKED" and not order.get("actual_pickup_at")
        agreement_waives_cancellation = order.get("account_id") == "ACCT-001" and booked_not_picked_up
        cancellation_requested = self._parse_like_snapshot(order.get("cancellation_requested_at"), snapshot) if order.get("cancellation_requested_at") else None
        booked_at = self._parse_like_snapshot(order.get("booked_at"), snapshot) if order.get("booked_at") else None
        cancellation_minutes_after_booking = None
        if cancellation_requested and booked_at:
            cancellation_minutes_after_booking = (cancellation_requested - booked_at).total_seconds() / 60
        within_standard_free_window = cancellation_minutes_after_booking is not None and cancellation_minutes_after_booking <= 30
        cancellation_fee_waiver = booked_not_picked_up and (agreement_waives_cancellation or within_standard_free_window)
        if agreement_waives_cancellation:
            cancellation_reason = "Customer agreement waives cancellation fee for Northstar BOOKED shipments before pickup."
        elif within_standard_free_window:
            cancellation_reason = "SOP allows no-fee cancellation within 30 minutes of booking before pickup."
        elif booked_not_picked_up:
            cancellation_reason = "Booked shipment can be cancelled, but standard fee may apply unless an agreement waives it."
        else:
            cancellation_reason = "Shipment is not in a simple booked-before-pickup cancellation state."

        result = {
            "pickup_delay_hours": round(delay_hours, 2),
            "carrier_fault": carrier_fault,
            "service_credit_eligible": service_credit_eligible,
            "cancellation_fee_waiver_likely": cancellation_fee_waiver,
            "booked_not_picked_up": booked_not_picked_up,
            "agreement_waives_cancellation": agreement_waives_cancellation,
            "cancellation_minutes_after_booking": round(cancellation_minutes_after_booking, 2) if cancellation_minutes_after_booking is not None else None,
            "cancellation_reason": cancellation_reason,
        }
        return result, ToolTrace("calculate_policy_outcome", "ok", f"Calculated pickup delay of {result['pickup_delay_hours']} hours.")

    def _parse_like_snapshot(self, value: str | None, snapshot: datetime) -> datetime:
        if not value:
            return snapshot
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None and snapshot.tzinfo is not None:
            parsed = parsed.replace(tzinfo=snapshot.tzinfo)
        return parsed

    def prepare_escalation(self, ctx: UserContext, account_id: str, reason: str, ticket_id: str | None = None, priority: str = "medium") -> tuple[PendingAction, ToolTrace]:
        require_account_access(ctx, account_id)
        require_action(ctx, "create_escalation")
        action = PendingAction(
            id=f"act_{uuid.uuid4().hex[:12]}",
            action_type="create_escalation",
            account_id=account_id,
            created_by=ctx.user_id,
            payload={"ticket_id": ticket_id, "reason": reason, "priority": priority},
            summary=f"Create {priority} escalation for {self.store.account_name(account_id)}: {reason}",
        )
        self.store.add_pending_action(action)
        return action, ToolTrace("prepare_escalation", "needs_confirmation", "Prepared escalation. User confirmation required.")

    def confirm_action(self, ctx: UserContext, action_id: str) -> dict[str, Any]:
        pending = self.store.get_pending_action(action_id)
        if not pending:
            raise ValueError("Pending action was not found or already executed.")
        require_account_access(ctx, pending["account_id"])
        require_action(ctx, pending["action_type"])
        if pending["action_type"] == "create_escalation":
            return self.store.create_escalation(pending)
        raise ValueError("Unsupported action type.")
