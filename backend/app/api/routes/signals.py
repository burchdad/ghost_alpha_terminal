from fastapi import APIRouter

from datetime import datetime, timedelta, timezone

from app.models.schemas import SignalResponse
from app.models.schemas import PriceHistoryResponse
from app.services.kronos_service import kronos_service
from app.services.options_service import options_service
from app.services.signal_engine import signal_engine
from app.services.historical_data_service import historical_data_service

router = APIRouter(prefix="/signal", tags=["signals"])


@router.get("/{symbol}", response_model=SignalResponse)
def get_signal(symbol: str) -> SignalResponse:
    forecast = kronos_service.generate_forecast(symbol=symbol, timeframe="1d")
    options_data = options_service.get_options_chain(symbol=symbol)
    return signal_engine.generate_signal(symbol=symbol, forecast=forecast, options_data=options_data)


@router.get("/history/{symbol}", response_model=PriceHistoryResponse)
def get_price_history(symbol: str, days: int = 90) -> PriceHistoryResponse:
    days = max(10, min(365, days))
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)
    df = historical_data_service.load_historical_data(
        symbol=symbol, timeframe="1d", start_date=start, end_date=end
    )
    bars = []
    if not df.empty:
        for _, row in df.iterrows():
            ts = row["timestamp"]
            bars.append(
                {
                    "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
    source = "mock" if not bars else "alpaca"
    return PriceHistoryResponse(symbol=symbol.upper(), timeframe="1d", bars=bars, source=source)
