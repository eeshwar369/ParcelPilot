from __future__ import annotations

from threading import RLock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.agent import SupportAgent, answer_to_dict
from backend.app.auth import DEMO_USERS, get_user_context
from backend.app.config import settings
from backend.app.dashboard import issue_dashboard
from backend.app.data_store import DataStore
from backend.app.ingest import ingest_available_files


settings.validate_production()


def build_store() -> DataStore:
    hydrated_store = DataStore(use_demo_fallback=not settings.is_production)
    ingest_result = ingest_available_files(hydrated_store)
    if settings.is_production:
        validate_real_data(hydrated_store, ingest_result)
    return hydrated_store


def validate_real_data(hydrated_store: DataStore, ingest_result: dict[str, Any]) -> None:
    if ingest_result.get("status") != "ok":
        raise RuntimeError("Production requires real files in data/raw; demo fallback is disabled.")
    if ingest_result.get("skipped"):
        raise RuntimeError(f"Production ingestion skipped required files: {ingest_result['skipped']}")
    required = {
        "accounts": hydrated_store.state.get("accounts", []),
        "orders": hydrated_store.state.get("orders", []),
        "tickets": hydrated_store.state.get("tickets", []),
        "documents": hydrated_store.state.get("documents", []),
    }
    empty = [name for name, value in required.items() if not value]
    if empty:
        raise RuntimeError(f"Production ingestion did not populate: {', '.join(empty)}")


store = build_store()
agent = SupportAgent(store)
store_lock = RLock()

app = FastAPI(
    title="ParcelPilot AI Support API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-User-Id"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ConfirmActionRequest(BaseModel):
    user_id: str
    action_id: str


class VerifyEscalationRequest(BaseModel):
    user_id: str
    status: str = "verified"


class RespondEscalationRequest(BaseModel):
    user_id: str
    message: str


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "parcelpilot-ai-support",
        "environment": settings.app_env,
        "retrieval_provider": settings.retrieval_provider,
        "data_source": store.state.get("data_source", "unknown"),
        "data_counts": {
            "accounts": len(store.state.get("accounts", [])),
            "orders": len(store.state.get("orders", [])),
            "tickets": len(store.state.get("tickets", [])),
            "documents": len(store.state.get("documents", [])),
        },
    }


@app.get("/api/users")
def users() -> dict[str, Any]:
    return {
        "users": [
            {
                "user_id": user.user_id,
                "display_name": user.display_name,
                "role": user.role,
                "account_id": user.account_id,
            }
            for user in DEMO_USERS.values()
        ]
    }


@app.get("/api/dashboard")
def dashboard(x_user_id: str = Header(default="support_agent")) -> dict[str, Any]:
    with store_lock:
        return issue_dashboard(store, get_user_context(x_user_id))


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    with store_lock:
        return answer_to_dict(agent.answer(request.user_id, request.message))


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            user_id = str(payload.get("user_id", "")).strip()
            message = str(payload.get("message", "")).strip()
            if not user_id or not message:
                await websocket.send_json({"type": "error", "error": "user_id and message are required"})
                continue
            await websocket.send_json({"type": "status", "message": "Checking account scope, records, and trusted documents..."})
            try:
                with store_lock:
                    response = answer_to_dict(agent.answer(user_id, message))
                await websocket.send_json({"type": "answer", "response": response})
            except Exception as exc:
                await websocket.send_json({"type": "error", "error": str(exc)})
    except WebSocketDisconnect:
        return


@app.post("/api/actions/confirm")
def confirm_action(request: ConfirmActionRequest) -> dict[str, Any]:
    try:
        with store_lock:
            return {"executed": agent.confirm_action(request.user_id, request.action_id)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/escalations")
def escalations(x_user_id: str = Header(default="support_agent")) -> dict[str, Any]:
    ctx = get_user_context(x_user_id)
    with store_lock:
        items = [item for item in store.escalations() if item.get("account_id") in ctx.allowed_account_ids]
        pending = [
            item
            for item in store.pending_actions()
            if item.get("account_id") in ctx.allowed_account_ids and item.get("status") == "pending"
        ]
        return {"escalations": items, "pending_actions": pending}


@app.post("/api/escalations/{escalation_id}/verify")
def verify_escalation(escalation_id: str, request: VerifyEscalationRequest) -> dict[str, Any]:
    ctx = get_user_context(request.user_id)
    if ctx.role not in {"support_agent", "ops_manager", "platform_admin"}:
        raise HTTPException(status_code=403, detail="User is not authorized to verify escalations.")
    try:
        with store_lock:
            escalation = store.verify_escalation(escalation_id, request.user_id, request.status)
            return {"escalation": escalation}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/escalations/{escalation_id}/respond")
def respond_escalation(escalation_id: str, request: RespondEscalationRequest) -> dict[str, Any]:
    ctx = get_user_context(request.user_id)
    if ctx.role not in {"support_agent", "ops_manager", "platform_admin"}:
        raise HTTPException(status_code=403, detail="User is not authorized to respond to escalations.")
    try:
        with store_lock:
            escalation = store.respond_escalation(escalation_id, request.user_id, request.message)
            return {"escalation": escalation}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/ingest")
def ingest() -> dict[str, Any]:
    with store_lock:
        return ingest_available_files(store)
