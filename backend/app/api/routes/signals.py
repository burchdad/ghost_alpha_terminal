from fastapi import APIRouter

from app.models.schemas import SignalResponse
from app.services.kronos_service import kronos_service
from app.services.options_service import options_service
from app.services.signal_engine import signal_engine

router = APIRouter(prefix="/signal", tags=["signals"])


@router.get("/{symbol}", response_model=SignalResponse)
def get_signal(symbol: str) -> SignalResponse:
    forecast = kronos_service.generate_forecast(symbol=symbol, timeframe="1d")
    options_data = options_service.get_options_chain(symbol=symbol)
    return signal_engine.generate_signal(symbol=symbol, forecast=forecast, options_data=options_data)
