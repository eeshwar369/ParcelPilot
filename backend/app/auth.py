from backend.app.schemas import UserContext


DEMO_USERS: dict[str, UserContext] = {
    "northstar_user": UserContext(
        user_id="northstar_user",
        display_name="Northstar Customer",
        role="customer",
        tenant_id="parcelpilot-demo",
        account_id="ACCT-001",
        allowed_account_ids=("ACCT-001",),
        allowed_actions=("create_escalation",),
    ),
    "lumenworks_user": UserContext(
        user_id="lumenworks_user",
        display_name="LumenWorks Customer",
        role="customer",
        tenant_id="parcelpilot-demo",
        account_id="ACCT-002",
        allowed_account_ids=("ACCT-002",),
        allowed_actions=("create_escalation",),
    ),
    "support_agent": UserContext(
        user_id="support_agent",
        display_name="ParcelPilot Support Agent",
        role="support_agent",
        tenant_id="parcelpilot-demo",
        account_id=None,
        allowed_account_ids=("ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"),
        allowed_actions=("create_escalation", "create_follow_up_task", "update_ticket"),
    ),
    "ops_manager": UserContext(
        user_id="ops_manager",
        display_name="ParcelPilot Ops Manager",
        role="ops_manager",
        tenant_id="parcelpilot-demo",
        account_id=None,
        allowed_account_ids=("ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"),
        allowed_actions=("create_escalation", "create_follow_up_task", "update_ticket"),
    ),
    "read_only_analyst": UserContext(
        user_id="read_only_analyst",
        display_name="Read Only Analyst",
        role="read_only_analyst",
        tenant_id="parcelpilot-demo",
        account_id=None,
        allowed_account_ids=("ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"),
        allowed_actions=(),
    ),
}


def get_user_context(user_id: str) -> UserContext:
    return DEMO_USERS.get(user_id, DEMO_USERS["northstar_user"])


def can_access_account(ctx: UserContext, account_id: str) -> bool:
    return account_id in ctx.allowed_account_ids


def require_account_access(ctx: UserContext, account_id: str) -> None:
    if not can_access_account(ctx, account_id):
        raise PermissionError("This user is not authorized to access that account.")


def require_action(ctx: UserContext, action: str) -> None:
    if action not in ctx.allowed_actions:
        raise PermissionError("This user is not authorized to perform that action.")
