from fastapi import APIRouter

from app.models.schemas import PortfolioResponse
from app.services.live_portfolio_service import live_portfolio_service
from app.services.portfolio_manager import portfolio_manager

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio() -> PortfolioResponse:
    live_snapshot = live_portfolio_service.snapshot()
    if live_snapshot is not None:
        # Ensure the data_source field is present.
        live_snapshot.setdefault("data_source", "live")
        live_snapshot.setdefault("degraded", False)
        return PortfolioResponse(**live_snapshot)

    # No broker connected — return the in-memory state with degraded flag so
    # the frontend can surface a "broker not connected" warning instead of
    # silently showing stale numbers.
    pm_snapshot = portfolio_manager.snapshot()
    pm_snapshot["data_source"] = "local_fallback"
    pm_snapshot["degraded"] = True
    return PortfolioResponse(**pm_snapshot)
