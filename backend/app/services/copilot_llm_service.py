from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class LLMActionResult:
    action: str | None
    params: dict[str, Any]
    requires_confirmation: bool
    reply: str | None
    raw_json: dict[str, Any]
    latency_ms: int | None
    error: str | None


class CopilotLLMService:
    def _client(self):
        if not settings.openai_api_key:
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None
        return OpenAI(api_key=settings.openai_api_key)

    def is_available(self) -> bool:
        return self._client() is not None

    def infer_action(
        self,
        *,
        message: str,
        state: dict,
        history: list[dict[str, str]] | None = None,
    ) -> LLMActionResult:
        client = self._client()
        if client is None:
            return LLMActionResult(
                action=None,
                params={},
                requires_confirmation=False,
                reply=None,
                raw_json={},
                latency_ms=None,
                error="OpenAI client unavailable",
            )

        schema = {
            "name": "copilot_intent",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "none",
                            "set_autonomous",
                            "set_scan_auto",
                            "set_execution_mode",
                            "run_autonomous_once",
                            "simulate_mission",
                            "set_goal",
                            "set_risk_limits",
                            "set_execution_policy",
                        ],
                    },
                    "params": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "requires_confirmation": {"type": "boolean"},
                    "assistant_reply": {"type": "string"},
                },
                "required": ["action", "params", "requires_confirmation", "assistant_reply"],
            },
            "strict": True,
        }

        system = (
            "You are a trading control copilot. Extract one action at most from the user's message. "
            "Use only the allowed action enums and include params keys matching the action. "
            "If no clear action, set action='none'. Keep assistant_reply concise and conversational."
        )

        payload = {
            "state": state,
            "recent_history": history or [],
            "user_message": message,
            "action_param_contract": {
                "set_autonomous": {"enabled": "boolean"},
                "set_scan_auto": {"enabled": "boolean"},
                "set_execution_mode": {"mode": "SIMULATION|PAPER_TRADING|LIVE_TRADING"},
                "run_autonomous_once": {},
                "simulate_mission": {
                    "target_capital": "number",
                    "timeframe_days": "int",
                    "start_capital": "number optional",
                },
                "set_goal": {"start_capital": "number", "target_capital": "number", "timeframe_days": "int"},
                "set_risk_limits": {"daily_loss_limit_pct": "0..1 optional", "max_drawdown_limit_pct": "0..1 optional"},
                "set_execution_policy": {
                    "live_only_during_market_hours": "boolean",
                    "market_open_hhmm": "HH:MM optional",
                    "market_close_hhmm": "HH:MM optional",
                },
            },
        }

        start = time.perf_counter()
        try:
            completion = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                response_format={"type": "json_schema", "json_schema": schema},
            )
            latency_ms = int((time.perf_counter() - start) * 1000)
            content = completion.choices[0].message.content or "{}"
            data = json.loads(content)
            action = str(data.get("action") or "none")
            if action == "none":
                action = None
            params = data.get("params") if isinstance(data.get("params"), dict) else {}
            requires_confirmation = bool(data.get("requires_confirmation", False))
            reply = str(data.get("assistant_reply") or "")
            return LLMActionResult(
                action=action,
                params=params,
                requires_confirmation=requires_confirmation,
                reply=reply,
                raw_json=data,
                latency_ms=latency_ms,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - start) * 1000)
            return LLMActionResult(
                action=None,
                params={},
                requires_confirmation=False,
                reply=None,
                raw_json={},
                latency_ms=latency_ms,
                error=str(exc),
            )


copilot_llm_service = CopilotLLMService()
