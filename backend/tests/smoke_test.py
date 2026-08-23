from backend.app.agent import SupportAgent
from backend.app.data_store import DataStore


def main() -> None:
    agent = SupportAgent(DataStore())

    answer = agent.answer("northstar_user", "Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.")
    assert "ORD-1001" in answer.answer
    assert answer.sources
    assert any(trace.name == "lookup_order" for trace in answer.tool_trace)
    assert answer.confidence in {"high", "medium", "low"}

    denied = agent.answer("northstar_user", "Can I see LumenWorks order ORD-2002?")
    assert "cannot access" in denied.answer.lower()

    escalation = agent.answer("support_agent", "Escalate ticket TKT-501 because it is high severity and near SLA breach.")
    assert escalation.pending_action is not None
    store = agent.store
    executed = agent.confirm_action("support_agent", escalation.pending_action.id)
    assert executed["id"].startswith("ESC-")
    response = store.respond_escalation(executed["id"], "support_agent", "Reviewed and responded to the customer.")
    assert response["status"] == "responded"
    assert response["response"]

    print("smoke tests passed")


if __name__ == "__main__":
    main()
