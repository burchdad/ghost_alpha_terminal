from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app.core.config import settings
from app.services.alpaca_client import alpaca_client
from app.utils.data_loader import load_mock_ohlcv


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
        try:
            rows = alpaca_client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            if rows:
                df = pd.DataFrame(rows)
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                for column in ["open", "high", "low", "close", "volume"]:
                    df[column] = pd.to_numeric(df[column], errors="coerce")
                df = df.dropna(subset=["open", "high", "low", "close", "volume"])
                if not df.empty:
                    return df.sort_values("timestamp").reset_index(drop=True)
        except Exception:
            pass

        if settings.use_mock_data:
            periods = 90 if timeframe in {"1h", "4h"} else 140
            return load_mock_ohlcv(symbol=symbol, timeframe=timeframe, periods=periods)

        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


historical_data_service = HistoricalDataService()
