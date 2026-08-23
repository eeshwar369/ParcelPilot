from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import time
from typing import Any, Literal
from urllib import request
import json


TaskType = Literal["intent", "query_rewrite", "internal_summary", "final_answer", "high_risk_final_answer"]


@dataclass
class ModelDecision:
    provider: str
    model: str
    task_type: str
    routing_reason: str
    estimated_cost_usd: float
    latency_ms: int


class ModelRouter:
    def __init__(self) -> None:
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.mode = os.getenv("MODEL_ROUTING_MODE", "cost_aware")
        self.daily_budget = float(os.getenv("OPENAI_DAILY_BUDGET_USD", "5") or "5")

    def choose(self, task_type: TaskType, risk: str) -> tuple[str, str, str]:
        if risk in {"high", "critical"} and self.openai_key:
            return "openai", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "high risk requires premium reasoning"
        if task_type in {"intent", "query_rewrite", "internal_summary"} and self.hf_token:
            return "huggingface", os.getenv("HF_TEXT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3"), "cheap auxiliary model path"
        if self.openai_key and task_type in {"final_answer", "high_risk_final_answer"}:
            return "openai", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "final answer reliability path"
        return "deterministic", "rules-template", "no provider key or low-risk deterministic path"

    def synthesize(self, task_type: TaskType, risk: str, prompt: str, fallback: str) -> tuple[str, dict[str, Any]]:
        provider, model, reason = self.choose(task_type, risk)
        started = time.perf_counter()
        text = fallback
        estimated_cost = 0.0

        if provider == "openai":
            text, estimated_cost = self._try_openai(model, prompt, fallback)
        elif provider == "huggingface":
            text, estimated_cost = self._try_huggingface(model, prompt, fallback)

        latency_ms = int((time.perf_counter() - started) * 1000)
        decision = ModelDecision(
            provider=provider,
            model=model,
            task_type=task_type,
            routing_reason=reason,
            estimated_cost_usd=estimated_cost,
            latency_ms=latency_ms,
        )
        return text, asdict(decision)

    def _try_openai(self, model: str, prompt: str, fallback: str) -> tuple[str, float]:
        try:
            payload = json.dumps(
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Answer using only the supplied context. Be concise and cite uncertainty."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                }
            ).encode("utf-8")
            req = request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip(), 0.002
        except Exception:
            return fallback, 0.0

    def _try_huggingface(self, model: str, prompt: str, fallback: str) -> tuple[str, float]:
        try:
            payload = json.dumps({"inputs": prompt, "parameters": {"max_new_tokens": 300, "temperature": 0.2}}).encode("utf-8")
            req = request.Request(
                f"https://api-inference.huggingface.co/models/{model}",
                data=payload,
                headers={"Authorization": f"Bearer {self.hf_token}", "Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"].replace(prompt, "").strip() or fallback, 0.0002
            return fallback, 0.0
        except Exception:
            return fallback, 0.0
