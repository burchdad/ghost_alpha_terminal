from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


def load_mock_ohlcv(symbol: str, timeframe: str, periods: int = 120) -> pd.DataFrame:
    """Generate deterministic mock OHLCV for quick local development."""
    seed = abs(hash(f"{symbol}:{timeframe}")) % (2**32)
    rng = np.random.default_rng(seed)

    base = 100 + rng.normal(0, 2)
    returns = rng.normal(0.0005, 0.01, size=periods)
    close = base * np.cumprod(1 + returns)
    open_ = np.insert(close[:-1], 0, base)

    spread = np.abs(rng.normal(0.003, 0.002, size=periods))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.integers(150_000, 1_000_000, size=periods)

    now = datetime.now(tz=timezone.utc)
    freq = "1h" if timeframe in {"1h", "4h"} else "1D"
    idx = pd.date_range(end=now, periods=periods, freq=freq)

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
