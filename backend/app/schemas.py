from dataclasses import dataclass, field
from typing import Any, Literal


Role = Literal[
    "customer",
    "customer_admin",
    "support_agent",
    "ops_manager",
    "read_only_analyst",
    "platform_admin",
]


@dataclass(frozen=True)
class UserContext:
    user_id: str
    display_name: str
    role: Role
    tenant_id: str
    account_id: str | None
    allowed_account_ids: tuple[str, ...]
    allowed_actions: tuple[str, ...]


@dataclass
class Source:
    name: str
    source_type: str
    authority: str
    status: str
    page: int | None
    account_id: str | None
    score: float
    excerpt: str


@dataclass
class ToolTrace:
    name: str
    status: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PendingAction:
    id: str
    action_type: str
    account_id: str
    created_by: str
    payload: dict[str, Any]
    summary: str
    status: str = "pending"


@dataclass
class AgentAnswer:
    answer: str
    confidence: Literal["high", "medium", "low"]
    sources: list[Source]
    tool_trace: list[ToolTrace]
    pending_action: PendingAction | None = None
    model_trace: list[dict[str, Any]] = field(default_factory=list)

