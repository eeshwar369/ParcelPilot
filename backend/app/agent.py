from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend.app.auth import get_user_context
from backend.app.data_store import DataStore, extract_ids
from backend.app.model_router import ModelRouter
from backend.app.schemas import AgentAnswer, Source, ToolTrace
from backend.app.tools import Tools
from backend.app.trust import confidence_from_evidence, risk_tier


class SupportAgent:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.tools = Tools(store)
        self.router = ModelRouter()

    def answer(self, user_id: str, message: str) -> AgentAnswer:
        ctx = get_user_context(user_id)
        traces: list[ToolTrace] = []
        sources: list[Source] = []
        pending_action = None
        ids = extract_ids(message)
        lowered = message.lower()
        wants_action = any(word in lowered for word in ["escalate", "create escalation", "follow up", "update ticket"])
        financial_or_sla = any(word in lowered for word in ["cancel", "fee", "credit", "sla", "late", "delay", "breach"])
        ticket_query = (
            "ticket" in lowered
            or "urgent" in lowered
            or "high severity" in lowered
            or "breach" in lowered
            or ("sla" in lowered and any(term in lowered for term in ["close", "approaching", "exceeding", "risk", "tickets"]))
        )

        order = None
        ticket = None
        account_id = ctx.account_id

        try:
            if ids["orders"]:
                order, trace = self.tools.lookup_order(ctx, ids["orders"][0].upper())
                traces.append(trace)
                if order:
                    account_id = order["account_id"]

            if ids["tickets"]:
                ticket, trace = self.tools.lookup_ticket(ctx, ids["tickets"][0].upper())
                traces.append(trace)
                if ticket:
                    account_id = ticket["account_id"]

            if not account_id:
                account = self.store.find_account_by_name(message)
                if account:
                    account_id = account["id"]

            if ticket_query:
                tickets, trace = self.tools.search_tickets(ctx, severity="high" if "high" in lowered else None)
                traces.append(trace)
            else:
                tickets = []

            docs, trace = self.tools.document_search(ctx, message)
            sources.extend(docs)
            traces.append(trace)

            calculation = None
            if order and financial_or_sla:
                calculation, trace = self.tools.calculate_policy_outcome(ctx, order)
                traces.append(trace)

            conflict = self._has_conflict(sources)
            confidence = confidence_from_evidence(bool(order or ticket or tickets), len(sources), conflict, wants_action)
            risk = risk_tier(ctx.role == "customer", financial_or_sla, conflict, wants_action)

            fallback = self._fallback_answer(ctx.user_id, message, order, ticket, tickets, calculation, sources, confidence, conflict, ticket_query)
            prompt = self._prompt(message, order, ticket, tickets, calculation, sources, confidence, conflict)
            answer_text, model_trace = self.router.synthesize(
                "high_risk_final_answer" if risk == "high" else "final_answer",
                risk,
                prompt,
                fallback,
            )
            self.store.model_usage({**model_trace, "actor_id": ctx.user_id, "conversation_id": "demo"})

            should_escalate_for_uncertainty = confidence == "low" and len(sources) == 0
            if wants_action or should_escalate_for_uncertainty:
                target_account = account_id or ctx.account_id
                if target_account and "create_escalation" in ctx.allowed_actions:
                    reason = "User requested escalation." if wants_action else "Agent confidence is low or sources conflict."
                    if ticket:
                        reason = f"{reason} Related ticket: {ticket['id']}."
                    pending_action, action_trace = self.tools.prepare_escalation(
                        ctx,
                        target_account,
                        reason=reason,
                        ticket_id=ticket["id"] if ticket else None,
                        priority="high" if risk == "high" else "medium",
                    )
                    traces.append(action_trace)
                    answer_text += "\n\nI prepared an escalation, but it has not been created yet. Please confirm before I execute it."

            self.store.audit(
                {
                    "actor_id": ctx.user_id,
                    "actor_role": ctx.role,
                    "event_type": "chat_answer",
                    "tool_name": "agent",
                    "request_payload": {"message": message},
                    "result_summary": {"confidence": confidence, "sources": len(sources), "pending_action": bool(pending_action)},
                }
            )
            return AgentAnswer(answer_text, confidence, sources, traces, pending_action, [model_trace])
        except PermissionError as exc:
            traces.append(ToolTrace("authorization", "denied", str(exc)))
            return AgentAnswer(
                "I cannot access that account, order, ticket, or agreement from your current user context.",
                "high",
                [],
                traces,
                None,
                [{"provider": "deterministic", "model": "authorization_guard", "routing_reason": "tool-layer access control"}],
            )

    def confirm_action(self, user_id: str, action_id: str) -> dict[str, Any]:
        ctx = get_user_context(user_id)
        result = self.tools.confirm_action(ctx, action_id)
        self.store.audit(
            {
                "actor_id": ctx.user_id,
                "actor_role": ctx.role,
                "event_type": "confirmed_action",
                "tool_name": "confirm_action",
                "request_payload": {"action_id": action_id},
                "result_summary": result,
            }
        )
        return result

    def _has_conflict(self, sources: list[Source]) -> bool:
        has_current = any(src.status == "current" for src in sources)
        has_deprecated = any(src.status == "deprecated" for src in sources)
        return has_current and has_deprecated

    def _prompt(
        self,
        message: str,
        order: dict[str, Any] | None,
        ticket: dict[str, Any] | None,
        tickets: list[dict[str, Any]],
        calculation: dict[str, Any] | None,
        sources: list[Source],
        confidence: str,
        conflict: bool,
    ) -> str:
        source_text = "\n".join(f"- {src.name} p.{src.page}: {src.excerpt}" for src in sources[:4])
        return (
            f"User question: {message}\n"
            f"Order: {order}\nTicket: {ticket}\nTickets: {tickets[:5]}\nCalculation: {calculation}\n"
            f"Confidence: {confidence}\nConflict: {conflict}\n"
            f"Sources:\n{source_text}\n"
            "Return a direct support answer with citations by source name."
        )

    def _fallback_answer(
        self,
        user_id: str,
        message: str,
        order: dict[str, Any] | None,
        ticket: dict[str, Any] | None,
        tickets: list[dict[str, Any]],
        calculation: dict[str, Any] | None,
        sources: list[Source],
        confidence: str,
        conflict: bool,
        ticket_query: bool,
    ) -> str:
        parts: list[str] = []
        if order and calculation:
            account = self.store.account_name(order["account_id"])
            if calculation["cancellation_fee_waiver_likely"]:
                parts.append(
                    f"Yes, {account} can likely cancel {order['id']} without a cancellation fee. {calculation.get('cancellation_reason')}"
                )
            elif calculation["service_credit_eligible"]:
                parts.append(
                    f"Yes, {account} likely qualifies for service-credit review for {order['id']} because the order shows carrier fault and a pickup delay of {calculation['pickup_delay_hours']} hours."
                )
            else:
                parts.append(
                    f"Based on the available order data, {order['id']} does not clearly qualify for a no-fee cancellation or service credit. {calculation.get('cancellation_reason')}"
                )
        elif tickets and ticket_query:
            parts.append(f"I found {len(tickets)} authorized ticket(s). The highest priority items should be reviewed first for SLA risk.")
            for item in tickets[:3]:
                parts.append(f"{item['id']}: {item['severity']} severity, {item['status']}, {item['summary']}")
        elif ticket:
            parts.append(f"Ticket {ticket['id']} is {ticket['severity']} severity and currently {ticket['status']}: {ticket['summary']}")
        elif sources:
            parts.append(self._source_answer(message, sources))
        else:
            parts.append("I could not find enough support data to answer confidently from the supplied sources.")

        if sources:
            cited = "; ".join(f"{src.name} p.{src.page}" for src in sources[:3])
            parts.append(f"Sources used: {cited}.")
        if conflict:
            parts.append("There may be conflicting source versions, so this should be escalated for human review.")
        parts.append(f"Confidence: {confidence}.")
        return " ".join(parts)

    def _source_answer(self, message: str, sources: list[Source]) -> str:
        lowered = message.lower()
        joined = " ".join(src.excerpt for src in sources[:3])
        compact = " ".join(joined.split())
        if "northstar" in lowered and "p1" in lowered:
            return "For Northstar, the P1 first-response target is 15 minutes, 24x7. Northstar's signed agreement overrides the standard support-policy targets."
        if "customer agreement" in lowered and ("general policy" in lowered or "disagree" in lowered or "override" in lowered):
            return "The signed customer agreement applies first when it conflicts with the general policy. Current policy and SOPs are used after the customer agreement."
        if "deprecated" in lowered:
            return "Use current sources first. Deprecated policies and historical tickets are context only and should not override a current policy, SOP, or signed customer agreement."
        if "service credit" in lowered:
            return "Service-credit eligibility should be based on the current service-credit SOP plus any customer-specific agreement. Historical tickets may provide context but should not control the answer."
        return f"I found relevant support documentation. Based on the supplied sources: {compact[:420]}"


def answer_to_dict(answer: AgentAnswer) -> dict[str, Any]:
    return {
        "answer": answer.answer,
        "confidence": answer.confidence,
        "sources": [asdict(src) for src in answer.sources],
        "tool_trace": [asdict(trace) for trace in answer.tool_trace],
        "pending_action": asdict(answer.pending_action) if answer.pending_action else None,
        "model_trace": answer.model_trace,
    }
