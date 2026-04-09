from fastapi import APIRouter

from app.models.schemas import PerformanceResponse
from app.services.performance_service import performance_service

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/{symbol}", response_model=PerformanceResponse)
def get_performance(symbol: str) -> PerformanceResponse:
    return performance_service.get_performance(symbol=symbol)
