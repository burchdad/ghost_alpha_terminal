from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps.auth import CurrentUser
from app.core.config import settings
from app.db.models import CopilotConversationMessage, CopilotTelemetryEvent, User
from app.db.session import get_session
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine
from app.services.copilot_llm_service import copilot_llm_service
from app.services.execution_policy_service import execution_policy_service
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.mission_intelligence_service import mission_intelligence_service
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.execution_bridge import execution_bridge

router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotMessageItem(BaseModel):
    role: str
    text: str
    timestamp: str


class CopilotContextResponse(BaseModel):
    greeting: str
    first_name: str
    state: dict
    history: list[CopilotMessageItem] = Field(default_factory=list)
    copilot_mode: str = "rule-based"


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
    copilot_mode: str = "rule-based"
    parser_used: str = "rule"


class CopilotTelemetrySummaryResponse(BaseModel):
    window_days: int
    total_events: int
    mode_breakdown: dict[str, int]
    parser_breakdown: dict[str, int]
    action_breakdown: dict[str, int]
    success_rate: float
    confirmation_rate: float


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
    policy = execution_policy_service.status()

    return {
        "execution_mode": mode,
        "scan_auto_mode": bool(orchestrator.get("auto_mode", False)),
        "scan_auto_interval_seconds": int(orchestrator.get("auto_interval_seconds", 300)),
        "autonomous_enabled": bool(auto.get("enabled", False)),
        "autonomous_interval_seconds": int(auto.get("interval_seconds", 300)),
        "autonomous_cycles_run": int(auto.get("cycles_run", 0)),
        "trading_enabled": bool(control.get("trading_enabled", False)),
        "daily_loss_limit_pct": float(control.get("daily_loss_limit_pct", 0.05)),
        "max_drawdown_limit_pct": float(control.get("max_drawdown_limit_pct", 0.10)),
        "account_balance": round(capital, 2),
        "goal_enabled": bool(goal.get("enabled", False)),
        "goal_target_capital": goal.get("target_capital"),
        "goal_timeframe_days": goal.get("timeframe_days"),
        "goal_pressure_multiplier": goal.get("goal_pressure_multiplier"),
        "goal_success_probability": goal.get("success_probability"),
        "live_only_during_market_hours": bool(policy.get("live_only_during_market_hours", False)),
        "market_timezone": str(policy.get("market_timezone") or "America/New_York"),
        "market_open_hhmm": str(policy.get("market_open_hhmm") or "09:30"),
        "market_close_hhmm": str(policy.get("market_close_hhmm") or "16:00"),
    }


def _assign_mode(user_id: str) -> str:
    if not settings.copilot_openai_enabled or settings.copilot_openai_rollout_pct <= 0:
        return "rule-based"

    bucket = int(hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < settings.copilot_openai_rollout_pct and copilot_llm_service.is_available():
        return "hybrid"
    return "rule-based"


def _log_message(user_id: str, role: str, message: str) -> None:
    with get_session() as session:
        session.add(
            CopilotConversationMessage(
                user_id=str(user_id),
                role=role,
                message=message,
            )
        )


def _log_telemetry(
    *,
    user_id: str,
    mode_assigned: str,
    parser_used: str,
    action_detected: bool,
    action_name: str | None,
    action_applied: bool,
    requires_confirmation: bool,
    success: bool,
    latency_ms: int | None,
    error: str | None,
    message: str,
) -> None:
    try:
        with get_session() as session:
            session.add(
                CopilotTelemetryEvent(
                    user_id=str(user_id),
                    mode_assigned=mode_assigned,
                    parser_used=parser_used,
                    action_detected=action_detected,
                    action_name=action_name,
                    action_applied=action_applied,
                    requires_confirmation=requires_confirmation,
                    success=success,
                    latency_ms=latency_ms,
                    error=error,
                    message_excerpt=message[:512],
                )
            )
    except Exception:
        pass


def _recent_history(user_id: str, limit: int = 24) -> list[CopilotMessageItem]:
    with get_session() as session:
        rows = (
            session.execute(
                select(CopilotConversationMessage)
                .where(CopilotConversationMessage.user_id == str(user_id))
                .order_by(CopilotConversationMessage.created_at.desc())
                .limit(max(1, min(limit, 100)))
            )
            .scalars()
            .all()
        )
    rows = list(reversed(rows))
    return [
        CopilotMessageItem(
            role=str(row.role),
            text=str(row.message),
            timestamp=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]


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


def _extract_contribution_plan(text: str) -> tuple[float | None, int | None]:
    amount_match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:per\s*week|weekly)", text)
    duration_match = re.search(r"for\s*(\d+)\s*(week|weeks|month|months)", text)

    if not amount_match or not duration_match:
        return None, None

    weekly_amount = float(amount_match.group(1).replace(",", ""))
    n = int(duration_match.group(1))
    unit = duration_match.group(2)
    weeks = n if unit.startswith("week") else n * 4
    return weekly_amount, weeks


def _extract_percent(text: str, key: str) -> float | None:
    if key == "daily_loss_limit_pct":
        patterns = [
            r"daily\s*(?:risk|loss)[^0-9]{0,12}(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%[^a-zA-Z]{0,6}daily\s*(?:risk|loss)",
        ]
    else:
        patterns = [
            r"max\s*drawdown[^0-9]{0,12}(\d+(?:\.\d+)?)\s*%",
            r"drawdown[^0-9]{0,12}(\d+(?:\.\d+)?)\s*%",
        ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return float(m.group(1))
    return None


def _extract_market_window(text: str) -> tuple[str | None, str | None]:
    m = re.search(r"between\s*(\d{1,2}:\d{2})\s*(?:and|to)\s*(\d{1,2}:\d{2})", text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def _build_simulation_summary(sim: dict) -> str:
    required_daily = float(sim.get("required_daily_return", 0.0) or 0.0) * 100.0
    pressure = float(sim.get("implied_goal_pressure", 1.0) or 1.0)
    style = str(sim.get("recommended_mission_style", "balanced") or "balanced")
    message = str(sim.get("message", "Scenario generated."))
    return (
        f"Simulation complete: required daily return {required_daily:.2f}% | "
        f"implied pressure {pressure:.2f}x | recommended style {style}. {message}"
    )


def _rule_parse_action(message: str, state: dict) -> ParsedAction | None:
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

    # Mission scenario simulation requests.
    if any(token in text for token in ["simulate", "simulation", "scenario"]) and any(
        token in text for token in ["goal", "target", "capital", "timeframe", "days", "weeks", "months"]
    ):
        amount, days = _extract_target_and_days(text)
        if amount is not None and days is not None:
            capital = float(state.get("account_balance", 0.0) or 0.0)
            target = max(1.0, capital + amount)
            return ParsedAction(
                action="simulate_mission",
                params={"start_capital": capital, "target_capital": round(target, 2), "timeframe_days": max(1, days)},
                requires_confirmation=False,
            )

    if "simulation" in text or "insight only" in text:
        return ParsedAction(action="set_execution_mode", params={"mode": "SIMULATION"}, requires_confirmation=False)

    if "market hours" in text and any(k in text for k in ["only", "restrict", "limit"]):
        open_hhmm, close_hhmm = _extract_market_window(text)
        params: dict = {"live_only_during_market_hours": True}
        if open_hhmm and close_hhmm:
            params["market_open_hhmm"] = open_hhmm
            params["market_close_hhmm"] = close_hhmm
        return ParsedAction(action="set_execution_policy", params=params, requires_confirmation=True)

    if "market hours" in text and any(k in text for k in ["disable", "remove", "24/7", "any time", "anytime"]):
        return ParsedAction(action="set_execution_policy", params={"live_only_during_market_hours": False}, requires_confirmation=False)

    daily_pct = _extract_percent(text, "daily_loss_limit_pct")
    dd_pct = _extract_percent(text, "max_drawdown_limit_pct")
    if daily_pct is not None or dd_pct is not None:
        params: dict = {}
        if daily_pct is not None:
            params["daily_loss_limit_pct"] = max(0.1, min(50.0, daily_pct)) / 100.0
        if dd_pct is not None:
            params["max_drawdown_limit_pct"] = max(0.1, min(50.0, dd_pct)) / 100.0
        return ParsedAction(action="set_risk_limits", params=params, requires_confirmation=False)

    weekly_amount, weeks = _extract_contribution_plan(text)
    if weekly_amount is not None and weeks is not None:
        capital = float(state.get("account_balance", 0.0) or 0.0)
        target = max(1.0, capital + (weekly_amount * weeks))
        return ParsedAction(
            action="set_goal",
            params={
                "start_capital": capital,
                "target_capital": round(target, 2),
                "timeframe_days": max(1, weeks * 7),
                "plan_note": f"Weekly contribution plan assumed: ${weekly_amount:,.2f}/week for {weeks} weeks.",
            },
            requires_confirmation=True,
        )

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


def _apply_confirmation_contract(parsed: ParsedAction, state_before: dict) -> ParsedAction:
    if parsed.action == "set_execution_mode" and str(parsed.params.get("mode")) == "LIVE_TRADING":
        parsed.requires_confirmation = True

    if parsed.action == "set_autonomous" and bool(parsed.params.get("enabled", False)):
        parsed.requires_confirmation = True

    if parsed.action == "set_goal":
        parsed.requires_confirmation = True

    if parsed.action == "simulate_mission":
        parsed.requires_confirmation = False

    if parsed.action == "set_execution_policy" and bool(parsed.params.get("live_only_during_market_hours", False)):
        parsed.requires_confirmation = True

    if parsed.action == "set_risk_limits":
        current_daily = float(state_before.get("daily_loss_limit_pct", 0.05) or 0.05)
        current_dd = float(state_before.get("max_drawdown_limit_pct", 0.10) or 0.10)
        next_daily = parsed.params.get("daily_loss_limit_pct")
        next_dd = parsed.params.get("max_drawdown_limit_pct")
        if (next_daily is not None and float(next_daily) > current_daily) or (next_dd is not None and float(next_dd) > current_dd):
            parsed.requires_confirmation = True

    return parsed


def _parse_action(message: str, state: dict, *, mode_assigned: str, user_id: str) -> tuple[ParsedAction | None, str, str | None, int | None]:
    parser_used = "rule"
    assistant_hint: str | None = None
    latency_ms: int | None = None

    if mode_assigned == "hybrid":
        history = [{"role": item.role, "text": item.text} for item in _recent_history(user_id, limit=8)]
        llm = copilot_llm_service.infer_action(message=message, state=state, history=history)
        latency_ms = llm.latency_ms
        if llm.reply:
            assistant_hint = llm.reply
        if llm.action:
            parser_used = "llm"
            return _apply_confirmation_contract(
                ParsedAction(action=str(llm.action), params=dict(llm.params), requires_confirmation=bool(llm.requires_confirmation)),
                state,
            ), parser_used, assistant_hint, latency_ms
        parser_used = "rule-fallback"

    parsed = _rule_parse_action(message, state)
    if parsed is not None:
        parsed = _apply_confirmation_contract(parsed, state)
    return parsed, parser_used, assistant_hint, latency_ms


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

    if parsed.action == "simulate_mission":
        if parsed.params.get("target_capital") is None or parsed.params.get("timeframe_days") is None:
            return actions
        simulation = mission_intelligence_service.simulate_mission(
            target_capital=float(parsed.params["target_capital"]),
            timeframe_days=int(parsed.params["timeframe_days"]),
            start_capital=float(parsed.params.get("start_capital")) if parsed.params.get("start_capital") is not None else None,
        )
        actions.append(_build_simulation_summary(simulation))
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
        if parsed.params.get("plan_note"):
            actions.append(str(parsed.params.get("plan_note")))
        return actions

    if parsed.action == "set_risk_limits":
        result = control_engine.set_limits(
            daily_loss_limit_pct=parsed.params.get("daily_loss_limit_pct"),
            max_drawdown_limit_pct=parsed.params.get("max_drawdown_limit_pct"),
        )
        actions.append(
            "Risk limits updated "
            f"(daily loss {(float(result['daily_loss_limit_pct']) * 100):.1f}% | max drawdown {(float(result['max_drawdown_limit_pct']) * 100):.1f}%)"
        )
        return actions

    if parsed.action == "set_execution_policy":
        status = execution_policy_service.configure(
            live_only_during_market_hours=parsed.params.get("live_only_during_market_hours"),
            market_open_hhmm=parsed.params.get("market_open_hhmm"),
            market_close_hhmm=parsed.params.get("market_close_hhmm"),
        )
        if status.get("live_only_during_market_hours"):
            actions.append(
                "Execution policy updated: live orders allowed only during market hours "
                f"({status.get('market_open_hhmm')}-{status.get('market_close_hhmm')} {status.get('market_timezone')})."
            )
        else:
            actions.append("Execution policy updated: live orders are no longer restricted to market hours.")
        return actions

    return actions


@router.get("/context", response_model=CopilotContextResponse)
def copilot_context(user: User = CurrentUser) -> CopilotContextResponse:
    first_name = _first_name_from_email(str(user.email))
    state = _state_snapshot()
    mode_assigned = _assign_mode(str(user.id))
    state["copilot_mode_assigned"] = mode_assigned
    history = _recent_history(str(user.id))
    return CopilotContextResponse(
        greeting=(
            f"Hey {first_name}, what would you like to do today? "
            "Anything we need to adjust, or are you comfortable with the current track? I'm all ears."
        ),
        first_name=first_name,
        state=state,
        history=history,
        copilot_mode=mode_assigned,
    )


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest, user: User = CurrentUser) -> CopilotChatResponse:
    state_before = _state_snapshot()
    mode_assigned = _assign_mode(str(user.id))
    state_before["copilot_mode_assigned"] = mode_assigned

    parsed: ParsedAction | None = None
    parser_used = "rule"
    assistant_hint: str | None = None
    latency_ms: int | None = None

    if payload.confirm and payload.pending_action:
        parsed = ParsedAction(
            action=str(payload.pending_action.get("action", "")),
            params=dict(payload.pending_action.get("params", {}) or {}),
            requires_confirmation=False,
        )
        parser_used = "confirmation"
        _log_message(str(user.id), "user", "[CONFIRM ACTION]")
    else:
        parsed, parser_used, assistant_hint, latency_ms = _parse_action(
            payload.message,
            state_before,
            mode_assigned=mode_assigned,
            user_id=str(user.id),
        )
        _log_message(str(user.id), "user", payload.message)

    if parsed is None:
        reply = assistant_hint or (
            "I can help with: enabling/disabling autonomous execution, toggling scan auto mode, "
            "switching execution mode (simulation/paper/live), running one autonomous cycle, "
            "running mission simulations like 'simulate additional $5,000 in 30 days', "
            "setting goals like 'need an additional $5,000 in 30 days', contribution plans like "
            "'$300 weekly for 12 weeks', risk limits like 'set daily risk to 2% and max drawdown to 10%', "
            "and policy controls like 'only run live during market hours'."
        )
        _log_message(str(user.id), "assistant", reply)
        _log_telemetry(
            user_id=str(user.id),
            mode_assigned=mode_assigned,
            parser_used=parser_used,
            action_detected=False,
            action_name=None,
            action_applied=False,
            requires_confirmation=False,
            success=True,
            latency_ms=latency_ms,
            error=None,
            message=payload.message,
        )
        return CopilotChatResponse(
            reply=reply,
            state=state_before,
            actions_applied=[],
            copilot_mode=mode_assigned,
            parser_used=parser_used,
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
        elif parsed.action == "set_execution_policy" and parsed.params.get("live_only_during_market_hours"):
            prompt = "This restricts LIVE_TRADING orders to configured market hours. Confirm policy update."
        elif parsed.action == "set_risk_limits":
            prompt = "This loosens one or more risk limits. Confirm policy update."
        elif parsed.action == "simulate_mission":
            prompt = "Running simulation scenario." 
        else:
            prompt = "Please confirm this control change."

        _log_message(str(user.id), "assistant", prompt)
        _log_telemetry(
            user_id=str(user.id),
            mode_assigned=mode_assigned,
            parser_used=parser_used,
            action_detected=True,
            action_name=parsed.action,
            action_applied=False,
            requires_confirmation=True,
            success=True,
            latency_ms=latency_ms,
            error=None,
            message=payload.message,
        )
        return CopilotChatResponse(
            reply=prompt,
            state=state_before,
            actions_applied=[],
            requires_confirmation=True,
            confirmation_prompt=prompt,
            pending_action={"action": parsed.action, "params": parsed.params},
            copilot_mode=mode_assigned,
            parser_used=parser_used,
        )

    actions = _apply_action(parsed)
    state_after = _state_snapshot()
    state_after["copilot_mode_assigned"] = mode_assigned

    if not actions:
        reply = "I understood your request but couldn't apply a supported action yet."
        _log_message(str(user.id), "assistant", reply)
        _log_telemetry(
            user_id=str(user.id),
            mode_assigned=mode_assigned,
            parser_used=parser_used,
            action_detected=True,
            action_name=parsed.action,
            action_applied=False,
            requires_confirmation=False,
            success=False,
            latency_ms=latency_ms,
            error="Unsupported action",
            message=payload.message,
        )
        return CopilotChatResponse(
            reply=reply,
            state=state_after,
            actions_applied=[],
            copilot_mode=mode_assigned,
            parser_used=parser_used,
        )

    reply = assistant_hint if (assistant_hint and len(assistant_hint.strip()) > 0) else ("Done. " + " | ".join(actions))
    _log_message(str(user.id), "assistant", reply)
    _log_telemetry(
        user_id=str(user.id),
        mode_assigned=mode_assigned,
        parser_used=parser_used,
        action_detected=True,
        action_name=parsed.action,
        action_applied=True,
        requires_confirmation=False,
        success=True,
        latency_ms=latency_ms,
        error=None,
        message=payload.message,
    )
    return CopilotChatResponse(
        reply=reply,
        state=state_after,
        actions_applied=actions,
        copilot_mode=mode_assigned,
        parser_used=parser_used,
    )


@router.get("/telemetry/summary", response_model=CopilotTelemetrySummaryResponse)
def copilot_telemetry_summary(days: int = 7, user: User = CurrentUser) -> CopilotTelemetrySummaryResponse:
    window_days = max(1, min(days, 30))
    since = datetime.now(tz=timezone.utc) - timedelta(days=window_days)

    with get_session() as session:
        rows = (
            session.execute(
                select(CopilotTelemetryEvent)
                .where(CopilotTelemetryEvent.user_id == str(user.id))
                .where(CopilotTelemetryEvent.created_at >= since)
                .order_by(CopilotTelemetryEvent.created_at.desc())
                .limit(5000)
            )
            .scalars()
            .all()
        )

    mode_breakdown: dict[str, int] = {}
    parser_breakdown: dict[str, int] = {}
    action_breakdown: dict[str, int] = {}
    success_count = 0
    confirm_count = 0

    for row in rows:
        mode_breakdown[row.mode_assigned] = mode_breakdown.get(row.mode_assigned, 0) + 1
        parser_breakdown[row.parser_used] = parser_breakdown.get(row.parser_used, 0) + 1
        key = row.action_name or "none"
        action_breakdown[key] = action_breakdown.get(key, 0) + 1
        if row.success:
            success_count += 1
        if row.requires_confirmation:
            confirm_count += 1

    total = len(rows)
    return CopilotTelemetrySummaryResponse(
        window_days=window_days,
        total_events=total,
        mode_breakdown=mode_breakdown,
        parser_breakdown=parser_breakdown,
        action_breakdown=action_breakdown,
        success_rate=(success_count / total) if total else 0.0,
        confirmation_rate=(confirm_count / total) if total else 0.0,
    )
