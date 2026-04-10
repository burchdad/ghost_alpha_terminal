from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser
from app.db.models import User
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.execution_bridge import execution_bridge

router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotContextResponse(BaseModel):
    greeting: str
    first_name: str
    state: dict


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    confirm: bool = False
    pending_action: dict | None = None


class CopilotChatResponse(BaseModel):
    reply: str
    state: dict
    actions_applied: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_prompt: str | None = None
    pending_action: dict | None = None


@dataclass
class ParsedAction:
    action: str
    params: dict
    requires_confirmation: bool


def _first_name_from_email(email: str) -> str:
    local = (email or "").split("@", 1)[0].strip()
    if not local:
        return "Trader"
    token = re.split(r"[._\-+]+", local)[0].strip()
    if not token:
        return "Trader"
    return token[:1].upper() + token[1:].lower()


def _current_capital() -> float:
    portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot() or {}
    return float(portfolio.get("account_balance", 0.0) or 0.0)


def _state_snapshot() -> dict:
    control = control_engine.status()
    auto = autonomous_runner.status()
    orchestrator = master_orchestrator.status()
    mode = execution_bridge.get_mode()
    capital = _current_capital()
    goal = goal_engine.status(current_capital=capital)
    return {
        "execution_mode": mode,
        "scan_auto_mode": bool(orchestrator.get("auto_mode", False)),
        "scan_auto_interval_seconds": int(orchestrator.get("auto_interval_seconds", 300)),
        "autonomous_enabled": bool(auto.get("enabled", False)),
        "autonomous_interval_seconds": int(auto.get("interval_seconds", 300)),
        "autonomous_cycles_run": int(auto.get("cycles_run", 0)),
        "trading_enabled": bool(control.get("trading_enabled", False)),
        "account_balance": round(capital, 2),
        "goal_enabled": bool(goal.get("enabled", False)),
        "goal_target_capital": goal.get("target_capital"),
        "goal_timeframe_days": goal.get("timeframe_days"),
        "goal_pressure_multiplier": goal.get("goal_pressure_multiplier"),
        "goal_success_probability": goal.get("success_probability"),
    }


def _extract_target_and_days(text: str) -> tuple[float | None, int | None]:
    amount_match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text)
    amount = None
    if amount_match:
        amount = float(amount_match.group(1).replace(",", ""))

    days_match = re.search(r"(\d+)\s*(day|days|week|weeks|month|months)", text)
    days = None
    if days_match:
        n = int(days_match.group(1))
        unit = days_match.group(2)
        if unit.startswith("day"):
            days = n
        elif unit.startswith("week"):
            days = n * 7
        elif unit.startswith("month"):
            days = n * 30

    return amount, days


def _parse_action(message: str, state: dict) -> ParsedAction | None:
    text = message.lower()

    if "run once" in text or "run now" in text:
        return ParsedAction(action="run_autonomous_once", params={}, requires_confirmation=False)

    if ("auto execution" in text or "autonomous" in text) and any(x in text for x in ["on", "enable", "start"]):
        return ParsedAction(action="set_autonomous", params={"enabled": True}, requires_confirmation=True)
    if ("auto execution" in text or "autonomous" in text) and any(x in text for x in ["off", "disable", "stop"]):
        return ParsedAction(action="set_autonomous", params={"enabled": False}, requires_confirmation=False)

    if ("scan auto" in text or "auto intelligent" in text or "auto intelligence" in text) and any(x in text for x in ["on", "enable", "start"]):
        return ParsedAction(action="set_scan_auto", params={"enabled": True}, requires_confirmation=False)
    if ("scan auto" in text or "auto intelligent" in text or "auto intelligence" in text) and any(x in text for x in ["off", "disable", "stop"]):
        return ParsedAction(action="set_scan_auto", params={"enabled": False}, requires_confirmation=False)

    if "live mode" in text or "live trading" in text or "set mode live" in text:
        return ParsedAction(action="set_execution_mode", params={"mode": "LIVE_TRADING"}, requires_confirmation=True)
    if "paper mode" in text or "paper trading" in text or "set mode paper" in text:
        return ParsedAction(action="set_execution_mode", params={"mode": "PAPER_TRADING"}, requires_confirmation=False)
    if "simulation" in text or "insight only" in text:
        return ParsedAction(action="set_execution_mode", params={"mode": "SIMULATION"}, requires_confirmation=False)

    # Goal-oriented prompts: "need additional $X in Y days"
    if "need" in text and ("additional" in text or "extra" in text or "target" in text):
        amount, days = _extract_target_and_days(text)
        if amount is not None and days is not None:
            capital = float(state.get("account_balance", 0.0) or 0.0)
            target = max(1.0, capital + amount)
            return ParsedAction(
                action="set_goal",
                params={"start_capital": capital, "target_capital": round(target, 2), "timeframe_days": max(1, days)},
                requires_confirmation=True,
            )

    return None


def _apply_action(parsed: ParsedAction) -> list[str]:
    actions: list[str] = []

    if parsed.action == "set_autonomous":
        enabled = bool(parsed.params.get("enabled", False))
        autonomous_runner.configure(enabled=enabled)
        master_orchestrator.set_auto_mode(enabled=enabled)
        actions.append(f"Autonomous execution {'enabled' if enabled else 'disabled'}")
        actions.append(f"Scan auto mode {'enabled' if enabled else 'disabled'}")
        return actions

    if parsed.action == "set_scan_auto":
        enabled = bool(parsed.params.get("enabled", False))
        master_orchestrator.set_auto_mode(enabled=enabled)
        actions.append(f"Scan auto mode {'enabled' if enabled else 'disabled'}")
        return actions

    if parsed.action == "set_execution_mode":
        mode = str(parsed.params.get("mode", "SIMULATION"))
        execution_bridge.set_mode(mode)
        actions.append(f"Execution mode set to {mode}")
        return actions

    if parsed.action == "run_autonomous_once":
        autonomous_runner.trigger_run_once()
        actions.append("Triggered one autonomous cycle")
        return actions

    if parsed.action == "set_goal":
        goal_engine.configure(
            start_capital=float(parsed.params["start_capital"]),
            target_capital=float(parsed.params["target_capital"]),
            timeframe_days=int(parsed.params["timeframe_days"]),
        )
        actions.append(
            "Goal updated to "
            f"${float(parsed.params['target_capital']):,.2f} in {int(parsed.params['timeframe_days'])} days"
        )
        return actions

    return actions


@router.get("/context", response_model=CopilotContextResponse)
def copilot_context(user: User = CurrentUser) -> CopilotContextResponse:
    first_name = _first_name_from_email(str(user.email))
    state = _state_snapshot()
    return CopilotContextResponse(
        greeting=(
            f"Hey {first_name}, what would you like to do today? "
            "Anything we need to adjust, or are you comfortable with the current track? I'm all ears."
        ),
        first_name=first_name,
        state=state,
    )


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest, user: User = CurrentUser) -> CopilotChatResponse:
    del user
    state_before = _state_snapshot()

    parsed: ParsedAction | None = None
    if payload.confirm and payload.pending_action:
        parsed = ParsedAction(
            action=str(payload.pending_action.get("action", "")),
            params=dict(payload.pending_action.get("params", {}) or {}),
            requires_confirmation=False,
        )
    else:
        parsed = _parse_action(payload.message, state_before)

    if parsed is None:
        return CopilotChatResponse(
            reply=(
                "I can help with: enabling/disabling autonomous execution, toggling scan auto mode, "
                "switching execution mode (simulation/paper/live), running one autonomous cycle, "
                "or setting a capital goal like 'need an additional $5,000 in 30 days'."
            ),
            state=state_before,
            actions_applied=[],
        )

    if parsed.requires_confirmation and not payload.confirm:
        if parsed.action == "set_execution_mode" and parsed.params.get("mode") == "LIVE_TRADING":
            prompt = "This will switch to LIVE_TRADING. Confirm you want real-money execution mode."
        elif parsed.action == "set_autonomous" and parsed.params.get("enabled"):
            prompt = "This enables autonomous execution and scan auto mode. Confirm to proceed."
        elif parsed.action == "set_goal":
            prompt = (
                "This updates your goal to "
                f"${float(parsed.params['target_capital']):,.2f} in {int(parsed.params['timeframe_days'])} days. "
                "Confirm this target."
            )
        else:
            prompt = "Please confirm this control change."

        return CopilotChatResponse(
            reply=prompt,
            state=state_before,
            actions_applied=[],
            requires_confirmation=True,
            confirmation_prompt=prompt,
            pending_action={"action": parsed.action, "params": parsed.params},
        )

    actions = _apply_action(parsed)
    state_after = _state_snapshot()

    if not actions:
        return CopilotChatResponse(
            reply="I understood your request but couldn't apply a supported action yet.",
            state=state_after,
            actions_applied=[],
        )

    return CopilotChatResponse(
        reply="Done. " + " | ".join(actions),
        state=state_after,
        actions_applied=actions,
    )
