from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter

from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.control_engine import control_engine
from app.models.schemas import ExecuteTradeRequest, ExecuteTradeResponse
from app.services.historical_data_service import historical_data_service
from app.services.portfolio_manager import portfolio_manager
from app.services.regime_detector import regime_detector
from app.services.risk_engine import risk_engine

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
def execute_trade(payload: ExecuteTradeRequest) -> ExecuteTradeResponse:
    portfolio_manager.configure(balance=payload.account_balance)
    portfolio_state = portfolio_manager.snapshot()
    control_state = control_engine.status()

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
        )
    )

    max_notional_by_risk = payload.account_balance * payload.risk_per_trade / max(allocation["stop_loss_pct"], 0.001)
    bounded_notional = min(float(allocation["recommended_notional"]), max_notional_by_risk)
    bounded_qty = round(bounded_notional / max(payload.entry_price, 0.01), 4)
    max_loss_amount = round(bounded_notional * float(allocation["stop_loss_pct"]), 2)

    risk = risk_engine.evaluate_trade(
        entry_price=payload.entry_price,
        stop_loss_pct=float(allocation["stop_loss_pct"]),
        take_profit_pct=payload.take_profit_pct,
        confidence=payload.confidence,
        max_loss_amount=max_loss_amount,
        account_balance=payload.account_balance,
    )

    if not risk["approved"] or not allocation["accepted"]:
        reason = risk["reason"] if not risk["approved"] else allocation["reason"]
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
        )

    opened = portfolio_manager.open_position(
        symbol=payload.symbol,
        strategy=payload.strategy,
        side=payload.side,
        entry_price=payload.entry_price,
        units=bounded_qty,
    )

    if not opened["accepted"]:
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
        )

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
    )
