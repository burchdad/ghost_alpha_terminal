from __future__ import annotations

import numpy as np
import pandas as pd

from app.models.schemas import RegimeResponse
from app.services.historical_data_service import historical_data_service


class RegimeDetector:
    def detect(self, symbol: str, timeframe: str = "1d") -> RegimeResponse:
        from datetime import datetime, timedelta, timezone

        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=160)
        df = historical_data_service.load_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
        )
        return self.detect_from_dataframe(df)

    def detect_from_dataframe(self, df: pd.DataFrame) -> RegimeResponse:
        if df.empty or len(df) < 25:
            return RegimeResponse(regime="RANGE_BOUND", confidence=0.51)

        close = df["close"].to_numpy(dtype=float)
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)

        returns = np.diff(close) / close[:-1]
        realized_vol = float(np.std(returns) * np.sqrt(252)) if len(returns) else 0.0

        # ATR proxy using true range normalized by price.
        prev_close = np.concatenate(([close[0]], close[:-1]))
        true_range = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
        atr_pct = float(np.mean(true_range[-20:] / np.maximum(close[-20:], 1e-6)))

        x = np.arange(20)
        y = close[-20:]
        slope = np.polyfit(x, y, 1)[0]
        trend_strength = abs(float(slope)) / max(float(np.mean(y)), 1e-6)

        if realized_vol > 0.35 or atr_pct > 0.03:
            regime = "HIGH_VOLATILITY"
            confidence = min(0.95, 0.58 + realized_vol * 0.7)
        elif trend_strength > 0.007:
            regime = "TRENDING"
            confidence = min(0.95, 0.56 + trend_strength * 15)
        else:
            regime = "RANGE_BOUND"
            confidence = min(0.9, 0.55 + max(0.0, 0.02 - trend_strength) * 8)

        return RegimeResponse(regime=regime, confidence=round(float(confidence), 3))


regime_detector = RegimeDetector()
