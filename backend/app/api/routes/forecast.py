from fastapi import APIRouter, Query

from app.models.schemas import ForecastResponse
from app.services.kronos_service import kronos_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/{symbol}", response_model=ForecastResponse)
def get_forecast(symbol: str, timeframe: str = Query(default="1d")) -> ForecastResponse:
    return kronos_service.generate_forecast(symbol=symbol, timeframe=timeframe)
