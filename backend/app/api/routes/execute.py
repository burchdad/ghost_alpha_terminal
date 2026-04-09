from fastapi import APIRouter

from app.services.control_engine import control_engine
from app.models.schemas import ExecuteTradeRequest, ExecuteTradeResponse
from app.services.portfolio_manager import portfolio_manager
from app.services.position_sizer import position_sizer
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/execute", tags=["execute"])


@router.post("", response_model=ExecuteTradeResponse)
def execute_trade(payload: ExecuteTradeRequest) -> ExecuteTradeResponse:
    sizing = position_sizer.calculate_position_size(
        account_balance=payload.account_balance,
        risk_per_trade=payload.risk_per_trade,
        stop_loss_pct=payload.stop_loss_pct,
        entry_price=payload.entry_price,
    )

    risk = risk_engine.evaluate_trade(
        entry_price=payload.entry_price,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        confidence=payload.confidence,
        max_loss_amount=sizing["max_loss_amount"],
        account_balance=payload.account_balance,
    )

    if not risk["approved"]:
        return ExecuteTradeResponse(
            accepted=False,
            reason=risk["reason"],
            position_size=sizing["position_size"],
            max_loss_amount=sizing["max_loss_amount"],
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
        )

    control_ok, control_reason = control_engine.validate_trade(
        symbol=payload.symbol,
        confidence=payload.confidence,
        expected_value=risk["expected_value"],
        risk_reward_ratio=risk["risk_reward_ratio"],
        position_size=sizing["position_size"],
        position_notional=sizing["position_notional"],
        account_balance=payload.account_balance,
    )
    if not control_ok:
        return ExecuteTradeResponse(
            accepted=False,
            reason=control_reason,
            position_size=sizing["position_size"],
            max_loss_amount=sizing["max_loss_amount"],
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
        )

    portfolio_manager.configure(balance=payload.account_balance)
    opened = portfolio_manager.open_position(
        symbol=payload.symbol,
        strategy=payload.strategy,
        side=payload.side,
        entry_price=payload.entry_price,
        units=sizing["position_size"],
    )

    if not opened["accepted"]:
        return ExecuteTradeResponse(
            accepted=False,
            reason=opened["reason"],
            position_size=sizing["position_size"],
            max_loss_amount=sizing["max_loss_amount"],
            risk_level=risk["risk_level"],
            expected_value=risk["expected_value"],
            risk_reward_ratio=risk["risk_reward_ratio"],
        )

    return ExecuteTradeResponse(
        accepted=True,
        reason=None,
        position_size=sizing["position_size"],
        max_loss_amount=sizing["max_loss_amount"],
        risk_level=risk["risk_level"],
        expected_value=risk["expected_value"],
        risk_reward_ratio=risk["risk_reward_ratio"],
    )
