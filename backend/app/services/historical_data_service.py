from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd


class HistoricalDataService:
    def load_historical_data(
        self,
        *,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        start = start_date if start_date.tzinfo else start_date.replace(tzinfo=timezone.utc)
        end = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)

        freq_map = {"1h": "1h", "4h": "4h", "1d": "1D"}
        freq = freq_map.get(timeframe, "1D")

        idx = pd.date_range(start=start, end=end, freq=freq)
        if len(idx) < 30:
            idx = pd.date_range(end=end, periods=60, freq=freq)

        seed = abs(hash(f"{symbol}:{timeframe}:{start.date()}:{end.date()}")) % (2**32)
        rng = np.random.default_rng(seed)

        base = 100 + rng.normal(0, 3)
        returns = rng.normal(0.0004, 0.012, size=len(idx))
        close = base * np.cumprod(1 + returns)
        open_ = np.insert(close[:-1], 0, base)

        spread = np.abs(rng.normal(0.004, 0.002, size=len(idx)))
        high = np.maximum(open_, close) * (1 + spread)
        low = np.minimum(open_, close) * (1 - spread)
        volume = rng.integers(100_000, 2_000_000, size=len(idx))

        return pd.DataFrame(
            {
                "timestamp": idx,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )


historical_data_service = HistoricalDataService()
