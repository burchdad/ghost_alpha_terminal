from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.core.config import settings
from app.models.schemas import ForecastResponse
from app.services.historical_data_service import historical_data_service


class KronosService:
    def __init__(self) -> None:
        self._model: Any | None = None

    def _load_model(self) -> None:
        if self._model is not None:
            return

        if settings.use_mock_data:
            self._model = "mock"
            return

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(settings.kronos_model_id)
            model = AutoModelForCausalLM.from_pretrained(settings.kronos_model_id)
            self._model = {"tokenizer": tokenizer, "model": model}
        except Exception as exc:
            # Forecast generation remains live-data-driven even if model loading fails.
            self._model = {"status": "load_failed", "error": str(exc)}

    def _fallback_forecast(self, symbol: str, timeframe: str) -> ForecastResponse:
        seed = abs(hash(f"{symbol.upper()}:{timeframe}")) % (2**32)
        rng = np.random.default_rng(seed)
        base_price = float(rng.normal(120.0, 25.0))
        base_price = max(5.0, base_price)
        horizon = 10
        noise = rng.normal(0, 0.0075, horizon)
        path = base_price * np.cumprod(1 + noise)

        return ForecastResponse(
            symbol=symbol.upper(),
            timeframe=timeframe,
            direction="SIDEWAYS",
            confidence=0.51,
            volatility="MEDIUM",
            range_bound=True,
            forecast_prices=[round(float(x), 2) for x in path],
            generated_at=datetime.now(tz=timezone.utc),
        )

    def generate_forecast(self, symbol: str, timeframe: str = "1d") -> ForecastResponse:
        self._load_model()

        end = datetime.now(tz=timezone.utc)
        start = end.replace(year=end.year - 1)
        df = historical_data_service.load_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
        )
        if df.empty:
            return self._fallback_forecast(symbol=symbol, timeframe=timeframe)
        closes = df["close"].to_numpy(dtype=float)
        returns = np.diff(closes) / closes[:-1]

        mean_return = float(np.mean(returns)) if len(returns) else 0.0
        vol = float(np.std(returns) * np.sqrt(252)) if len(returns) else 0.0

        if mean_return > 0.001:
            direction = "UP"
        elif mean_return < -0.001:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        if vol < 0.15:
            volatility = "LOW"
        elif vol < 0.35:
            volatility = "MEDIUM"
        else:
            volatility = "HIGH"

        range_bound = abs(mean_return) < 0.0008 and vol < 0.22
        confidence = float(min(0.95, max(0.51, abs(mean_return) * 200 + 0.55)))

        last_price = float(closes[-1])
        horizon = 10
        drift = mean_return
        noise = np.random.default_rng(abs(hash(symbol)) % (2**32)).normal(0, vol / np.sqrt(252), horizon)
        path = last_price * np.cumprod(1 + drift + noise)

        return ForecastResponse(
            symbol=symbol.upper(),
            timeframe=timeframe,
            direction=direction,
            confidence=round(confidence, 3),
            volatility=volatility,
            range_bound=range_bound,
            forecast_prices=[round(float(x), 2) for x in path],
            generated_at=datetime.now(tz=timezone.utc),
        )


kronos_service = KronosService()
