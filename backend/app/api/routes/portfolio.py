from fastapi import APIRouter

from app.models.schemas import PortfolioResponse
from app.services.live_portfolio_service import live_portfolio_service
from app.services.portfolio_manager import portfolio_manager

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio() -> PortfolioResponse:
    live_snapshot = live_portfolio_service.snapshot()
    if live_snapshot is not None:
        return PortfolioResponse(**live_snapshot)
    return PortfolioResponse(**portfolio_manager.snapshot())
