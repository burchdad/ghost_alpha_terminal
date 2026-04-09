from fastapi import APIRouter

from app.models.schemas import PortfolioResponse
from app.services.portfolio_manager import portfolio_manager

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio() -> PortfolioResponse:
    return PortfolioResponse(**portfolio_manager.snapshot())
