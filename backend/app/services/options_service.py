from __future__ import annotations

from datetime import datetime, timedelta, timezone

import math
import numpy as np

from app.models.schemas import OptionContract, OptionsChainResponse
from app.services.historical_data_service import historical_data_service


class OptionsService:
    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def calculate_greeks(self, *, spot: float, strike: float, ttm: float, iv: float, option_type: str) -> dict[str, float]:
        r = 0.02
        sigma = max(iv, 0.01)
        t = max(ttm, 1 / 365)

        d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
        d2 = d1 - sigma * math.sqrt(t)

        pdf_d1 = math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)
        delta_call = self._norm_cdf(d1)
        delta_put = delta_call - 1
        gamma = pdf_d1 / (spot * sigma * math.sqrt(t))
        vega = spot * pdf_d1 * math.sqrt(t) / 100

        theta_call = (
            -(spot * pdf_d1 * sigma) / (2 * math.sqrt(t))
            - r * strike * math.exp(-r * t) * self._norm_cdf(d2)
        ) / 365
        theta_put = (
            -(spot * pdf_d1 * sigma) / (2 * math.sqrt(t))
            + r * strike * math.exp(-r * t) * self._norm_cdf(-d2)
        ) / 365

        return {
            "delta": round(delta_call if option_type == "CALL" else delta_put, 4),
            "gamma": round(gamma, 5),
            "theta": round(theta_call if option_type == "CALL" else theta_put, 4),
            "vega": round(vega, 4),
        }

    def get_options_chain(self, symbol: str) -> OptionsChainResponse:
        symbol = symbol.upper()
        seed = abs(hash(symbol)) % (2**32)
        rng = np.random.default_rng(seed)
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=120)
        candles = historical_data_service.load_historical_data(
            symbol=symbol,
            timeframe="1d",
            start_date=start,
            end_date=end,
        )
        closes = candles["close"].to_numpy(dtype=float) if not candles.empty else np.array([])
        returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else np.array([])
        underlying = round(float(closes[-1]), 2) if len(closes) else round(float(rng.normal(180, 20)), 2)
        base_iv = float(np.std(returns) * np.sqrt(252)) if len(returns) else 0.35
        strikes = [round(underlying + x, 2) for x in range(-25, 30, 5)]
        expiration = (datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

        contracts: list[OptionContract] = []
        for strike in strikes:
            for option_type in ("CALL", "PUT"):
                iv = float(max(0.08, min(1.2, rng.normal(max(base_iv, 0.12), 0.08))))
                ttm = 30 / 365
                greeks = self.calculate_greeks(
                    spot=underlying,
                    strike=strike,
                    ttm=ttm,
                    iv=iv,
                    option_type=option_type,
                )
                contracts.append(
                    OptionContract(
                        symbol=symbol,
                        strike=strike,
                        expiration=expiration,
                        option_type=option_type,
                        iv=round(iv * 100, 2),
                        open_interest=int(rng.integers(150, 10000)),
                        volume=int(rng.integers(25, 5000)),
                        delta=greeks["delta"],
                        gamma=greeks["gamma"],
                        theta=greeks["theta"],
                        vega=greeks["vega"],
                    )
                )

        avg_iv = float(np.mean([c.iv for c in contracts]))

        return OptionsChainResponse(
            symbol=symbol,
            underlying_price=underlying,
            contracts=contracts,
            avg_iv=round(avg_iv, 2),
            generated_at=datetime.now(tz=timezone.utc),
        )


options_service = OptionsService()
