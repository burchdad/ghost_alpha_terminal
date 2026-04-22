from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter

from app.api.deps.auth import HighTrustUser
from app.core.config import settings
from app.db.models import User
from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.context_intelligence import context_intelligence
from app.services.control_engine import control_engine
from app.services.decision_audit_store import decision_audit_store
from app.services.explainability import build_explainability
from app.models.schemas import ExecuteTradeRequest, ExecuteTradeResponse
from app.services.goal_engine import goal_engine
from app.services.historical_data_service import historical_data_service
from app.services.portfolio_manager import portfolio_manager
from app.services.portfolio_risk_governor import portfolio_risk_governor
from app.services.regime_detector import regime_detector
from app.services.risk_engine import risk_engine
from app.services.lightweight_metrics import lightweight_metrics
from app.services.notification_service import notification_service

router = APIRouter(prefix="/execute", tags=["execute"])


def _derive_market_context(symbol: str, timeframe: str = "1d") -> tuple[Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"], float]:
    """Infer regime and realized volatility from recent historical candles."""
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=90)
    try:
        df = historical_data_service.load_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        detected_regime = regime_detector.detect_from_dataframe(df).regime
        closes = [float(v) for v in df["close"].tolist() if float(v) > 0]
        if len(closes) < 3:
            return detected_regime, 0.02
        returns: list[float] = []
        for idx in range(1, len(closes)):
            prev = closes[idx - 1]
            curr = closes[idx]
            if prev <= 0:
                continue
            returns.append((curr / prev) - 1.0)
        if len(returns) < 2:
            return detected_regime, 0.02
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        stdev = variance ** 0.5
        return detected_regime, max(0.001, min(stdev, 0.25))
    except Exception:
        return "RANGE_BOUND", 0.02


@router.post("", response_model=ExecuteTradeResponse)
def execute_trade(payload: ExecuteTradeRequest, user: User = HighTrustUser) -> ExecuteTradeResponse:
    portfolio_manager.configure(balance=payload.account_balance)
    portfolio_state = portfolio_manager.snapshot()
    control_state = control_engine.status()
    goal_pressure = goal_engine.current_pressure(
        current_capital=float(portfolio_state["account_balance"])
    )
    context = context_intelligence.get_context(payload.symbol)

    risk_level = "HIGH" if payload.confidence < 0.58 else "MEDIUM" if payload.confidence < 0.70 else "LOW"
    inferred_regime, realized_volatility_pct = _derive_market_context(payload.symbol)
    allocation = capital_allocator.compute(
        AllocationInput(
            account_balance=payload.account_balance,
            current_price=payload.entry_price,
            confidence=payload.confidence,
            regime=inferred_regime,
            risk_level=risk_level,
            agent_agreement=0.66,
            drawdown_pct=float(control_state["rolling_drawdown_pct"]),
            current_exposure_pct=float(portfolio_state["risk_exposure_pct"]),
            realized_volatility_pct=realized_volatility_pct,
            goal_pressure_multiplier=goal_pressure * float(context["modifiers"]["risk_modifier"]),
        )
    )

    max_notional_by_risk = payload.account_balance * payload.risk_per_trade / max(allocation["stop_loss_pct"], 0.001)
    bounded_notional = min(float(allocation["recommended_notional"]), max_notional_by_risk)
    bounded_qty = round(bounded_notional / max(payload.entry_price, 0.01), 4)
    governor = portfolio_risk_governor.evaluate(
        symbol=payload.symbol,
        proposed_notional=bounded_notional,
        proposed_qty=bounded_qty,
        account_balance=payload.account_balance,
        current_exposure_pct=float(portfolio_state["risk_exposure_pct"]),
        drawdown_pct=float(control_state["rolling_drawdown_pct"]),
        sector_concentration=dict(portfolio_state.get("sector_concentration", {})),
    )
    if governor.decision == "BLOCK":
        bounded_notional = 0.0
        bounded_qty = 0.0
    elif governor.decision == "RESIZE":
        bounded_notional = float(governor.adjusted_notional)
        bounded_qty = float(governor.adjusted_qty)
    max_loss_amount = round(bounded_notional * float(allocation["stop_loss_pct"]), 2)

    risk = risk_engine.evaluate_trade(
        entry_price=payload.entry_price,
        stop_loss_pct=float(allocation["stop_loss_pct"]),
        take_profit_pct=payload.take_profit_pct,
        confidence=payload.confidence,
        max_loss_amount=max_loss_amount,
        account_balance=payload.account_balance,
    )

    if governor.decision == "BLOCK" or not risk["approved"] or not allocation["accepted"]:
        reason = risk["reason"] if not risk["approved"] else allocation["reason"]
        if governor.decision == "BLOCK":
            reason = governor.reason
        explainability = build_explainability(
            reasoning=reason,
            confidence=payload.confidence,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            accepted=False,
            safeguards=["risk_engine", "capital_allocator", "portfolio_risk_governor"],
            inputs={
                "regime": inferred_regime,
                "goal_pressure_multiplier": goal_pressure,
                "realized_volatility_pct": realized_volatility_pct,
                "context": context,
            },
        )
        decision_audit_store.record(
            decision_type="EXECUTE",
            symbol=payload.symbol,
            status="REJECTED",
            cycle_id=None,
            goal_snapshot=goal_engine.status(current_capital=float(portfolio_state["account_balance"])),
            context_snapshot=context,
            allocation_snapshot=allocation,
            governor_snapshot=governor.__dict__,
            execution_snapshot={"submitted": False, "reason": reason},
            explainability_snapshot=explainability,
        )
        return ExecuteTradeResponse(
            accepted=False,
            reason=reason,
            position_size=bounded_qty,
            max_loss_amount=max_loss_amount,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
            target_pct=float(allocation["target_pct"]),
            position_notional=round(bounded_notional, 2),
            governor_decision=governor.decision,
            governor_reason=governor.reason,
            explainability=explainability,
        )

    control_ok, control_reason = control_engine.validate_trade(
        symbol=payload.symbol,
        confidence=payload.confidence,
        expected_value=risk["expected_value"],
        risk_reward_ratio=risk["risk_reward_ratio"],
        position_size=bounded_qty,
        position_notional=round(bounded_notional, 2),
        account_balance=payload.account_balance,
    )
    if not control_ok:
        explainability = build_explainability(
            reasoning=control_reason,
            confidence=payload.confidence,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            accepted=False,
            safeguards=["control_engine", "kill_switch", "drawdown_limits", "portfolio_risk_governor"],
            inputs={
                "regime": inferred_regime,
                "goal_pressure_multiplier": goal_pressure,
                "realized_volatility_pct": realized_volatility_pct,
                "context": context,
            },
        )
        decision_audit_store.record(
            decision_type="EXECUTE",
            symbol=payload.symbol,
            status="REJECTED",
            cycle_id=None,
            goal_snapshot=goal_engine.status(current_capital=float(portfolio_state["account_balance"])),
            context_snapshot=context,
            allocation_snapshot=allocation,
            governor_snapshot=governor.__dict__,
            execution_snapshot={"submitted": False, "reason": control_reason},
            explainability_snapshot=explainability,
        )
        return ExecuteTradeResponse(
            accepted=False,
            reason=control_reason,
            position_size=bounded_qty,
            max_loss_amount=max_loss_amount,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
            target_pct=float(allocation["target_pct"]),
            position_notional=round(bounded_notional, 2),
            governor_decision=governor.decision,
            governor_reason=governor.reason,
            explainability=explainability,
        )

    opened = portfolio_manager.open_position(
        symbol=payload.symbol,
        strategy=payload.strategy,
        side=payload.side,
        entry_price=payload.entry_price,
        units=bounded_qty,
    )

    if not opened["accepted"]:
        explainability = build_explainability(
            reasoning=opened["reason"],
            confidence=payload.confidence,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            accepted=False,
            safeguards=["portfolio_concentration_limits"],
            inputs={
                "regime": inferred_regime,
                "goal_pressure_multiplier": goal_pressure,
                "realized_volatility_pct": realized_volatility_pct,
                "context": context,
            },
        )
        decision_audit_store.record(
            decision_type="EXECUTE",
            symbol=payload.symbol,
            status="REJECTED",
            cycle_id=None,
            goal_snapshot=goal_engine.status(current_capital=float(portfolio_state["account_balance"])),
            context_snapshot=context,
            allocation_snapshot=allocation,
            governor_snapshot=governor.__dict__,
            execution_snapshot={"submitted": False, "reason": opened["reason"]},
            explainability_snapshot=explainability,
        )
        return ExecuteTradeResponse(
            accepted=False,
            reason=opened["reason"],
            position_size=bounded_qty,
            max_loss_amount=max_loss_amount,
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
            target_pct=float(allocation["target_pct"]),
            position_notional=round(bounded_notional, 2),
            governor_decision=governor.decision,
            governor_reason=governor.reason,
            explainability=explainability,
        )

    explainability = build_explainability(
        reasoning="Trade approved by risk, control, and portfolio gates.",
        confidence=payload.confidence,
        risk_level=risk["risk_level"],
        expected_value=risk["expected_value"],
        accepted=True,
        safeguards=["risk_engine", "control_engine", "portfolio_manager"],
        inputs={
            "regime": inferred_regime,
            "goal_pressure_multiplier": goal_pressure,
            "realized_volatility_pct": realized_volatility_pct,
            "position_notional": round(bounded_notional, 2),
            "context": context,
        },
    )

    decision_audit_store.record(
        decision_type="EXECUTE",
        symbol=payload.symbol,
        status="ACCEPTED",
        cycle_id=None,
        goal_snapshot=goal_engine.status(current_capital=float(portfolio_state["account_balance"])),
        context_snapshot=context,
        allocation_snapshot=allocation,
        governor_snapshot=governor.__dict__,
        execution_snapshot={"submitted": True, "reason": "Order accepted in execute route."},
        explainability_snapshot=explainability,
    )

    try:
        lightweight_metrics.record_trade(payload.strategy)
    except Exception:
        # Logging must stay non-blocking for the execution path.
        pass

    try:
        notification_service.trade_executed(
            symbol=payload.symbol,
            direction=payload.side,
            quantity=bounded_qty,
            price=payload.entry_price,
            broker=getattr(payload, "broker", "default"),
            mode=getattr(payload, "mode", "live"),
            email_to=settings.notification_email_to or None,
        )
    except Exception:
        pass

    return ExecuteTradeResponse(
        accepted=True,
        reason=None,
        position_size=bounded_qty,
        max_loss_amount=max_loss_amount,
        risk_level=risk["risk_level"],
        expected_value=risk["expected_value"],
        risk_reward_ratio=risk["risk_reward_ratio"],
        target_pct=float(allocation["target_pct"]),
        position_notional=round(bounded_notional, 2),
        governor_decision=governor.decision,
        governor_reason=governor.reason,
        explainability=explainability,
    )
