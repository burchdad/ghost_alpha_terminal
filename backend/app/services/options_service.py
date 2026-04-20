from __future__ import annotations

from datetime import datetime, timedelta, timezone

import math
import numpy as np
import httpx

from app.models.schemas import OptionContract, OptionsChainResponse
from app.services.historical_data_service import historical_data_service
from app.services.tradier_client import tradier_client


class OptionsService:
    def _fetch_underlying_quote(self, symbol: str) -> float:
        quotes = tradier_client.get("/markets/quotes", params={"symbols": symbol, "greeks": "false"})
        quote_block = quotes.get("quotes", {}) if isinstance(quotes, dict) else {}
        quote = quote_block.get("quote") if isinstance(quote_block, dict) else None
        if isinstance(quote, list):
            quote = quote[0] if quote else None
        if isinstance(quote, dict):
            return float(quote.get("last") or quote.get("bid") or quote.get("ask") or 0.0)
        return 0.0

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

    def get_available_expirations(self, symbol: str) -> list[str]:
        symbol = symbol.upper()
        if not tradier_client.is_configured():
            return [(datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")]

        try:
            payload = tradier_client.get(
                "/markets/options/expirations",
                params={
                    "symbol": symbol,
                    "includeAllRoots": "false",
                    "strikes": "false",
                    "contractSize": "false",
                    "expirationType": "false",
                },
            )
            expirations = payload.get("expirations", {}) if isinstance(payload, dict) else {}
            dates = expirations.get("date") if isinstance(expirations, dict) else None
            if isinstance(dates, list):
                return [str(item) for item in dates if str(item).strip()]
            if isinstance(dates, str) and dates.strip():
                return [dates]
        except Exception:
            pass

        return [(datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")]

    def _fallback_chain(self, symbol: str, *, expiration: str | None = None) -> OptionsChainResponse:
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
        selected_expiration = expiration or (datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

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
                        option_symbol=f"{symbol}{selected_expiration.replace('-', '')}{'C' if option_type == 'CALL' else 'P'}{int(strike * 1000):08d}",
                        strike=strike,
                        expiration=selected_expiration,
                        option_type=option_type,
                        iv=round(iv * 100, 2),
                        open_interest=int(rng.integers(150, 10000)),
                        volume=int(rng.integers(25, 5000)),
                        delta=greeks["delta"],
                        gamma=greeks["gamma"],
                        theta=greeks["theta"],
                        vega=greeks["vega"],
                        bid=round(max(0.05, abs(strike - underlying) * 0.04 + rng.uniform(0.05, 2.5)), 2),
                        ask=round(max(0.06, abs(strike - underlying) * 0.04 + rng.uniform(0.08, 2.7)), 2),
                        last=round(max(0.05, abs(strike - underlying) * 0.04 + rng.uniform(0.05, 2.6)), 2),
                        mid=None,
                        underlying=symbol,
                        source="synthetic",
                    )
                )

        for contract in contracts:
            if contract.bid is not None and contract.ask is not None:
                contract.mid = round((contract.bid + contract.ask) / 2, 2)

        avg_iv = float(np.mean([c.iv for c in contracts]))

        return OptionsChainResponse(
            symbol=symbol,
            underlying_price=underlying,
            contracts=contracts,
            avg_iv=round(avg_iv, 2),
            source="synthetic",
            selected_expiration=selected_expiration,
            available_expirations=[selected_expiration],
            generated_at=datetime.now(tz=timezone.utc),
        )

    def _tradier_chain(self, symbol: str, *, expiration: str | None = None) -> OptionsChainResponse:
        symbol = symbol.upper()
        expirations = self.get_available_expirations(symbol)
        selected_expiration = expiration or (expirations[0] if expirations else None)
        if not selected_expiration:
            raise ValueError("No option expiration available")

        payload = tradier_client.get(
            "/markets/options/chains",
            params={
                "symbol": symbol,
                "expiration": selected_expiration,
                "greeks": "true",
            },
        )
        options = payload.get("options", {}) if isinstance(payload, dict) else {}
        rows = options.get("option") if isinstance(options, dict) else None
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list) or not rows:
            raise ValueError("No option contracts returned")

        contracts: list[OptionContract] = []
        iv_values: list[float] = []
        underlying_price = self._fetch_underlying_quote(symbol)
        for row in rows:
            if not isinstance(row, dict):
                continue
            greeks = row.get("greeks") if isinstance(row.get("greeks"), dict) else {}
            bid = float(row.get("bid") or 0.0)
            ask = float(row.get("ask") or 0.0)
            last = float(row.get("last") or 0.0)
            mid = round((bid + ask) / 2, 4) if bid > 0 and ask > 0 else None
            iv_raw = greeks.get("mid_iv") or greeks.get("smv_vol") or greeks.get("iv") or 0.0
            iv_pct = round(float(iv_raw) * 100, 2) if float(iv_raw or 0.0) <= 3.0 else round(float(iv_raw or 0.0), 2)
            iv_values.append(iv_pct)
            contracts.append(
                OptionContract(
                    symbol=symbol,
                    option_symbol=str(row.get("symbol") or ""),
                    strike=float(row.get("strike") or 0.0),
                    expiration=str(row.get("expiration_date") or selected_expiration),
                    option_type="CALL" if str(row.get("option_type") or "call").lower() == "call" else "PUT",
                    iv=iv_pct,
                    open_interest=int(row.get("open_interest") or 0),
                    volume=int(row.get("volume") or 0),
                    delta=round(float(greeks.get("delta") or 0.0), 4),
                    gamma=round(float(greeks.get("gamma") or 0.0), 5),
                    theta=round(float(greeks.get("theta") or 0.0), 4),
                    vega=round(float(greeks.get("vega") or 0.0), 4),
                    bid=round(bid, 4) if bid > 0 else None,
                    ask=round(ask, 4) if ask > 0 else None,
                    last=round(last, 4) if last > 0 else None,
                    mid=mid,
                    underlying=str(row.get("underlying") or symbol),
                    source="tradier",
                )
            )

        contracts.sort(key=lambda item: (item.expiration, item.strike, item.option_type))
        if contracts:
            first = contracts[0]
            if first.last is not None and first.underlying == symbol:
                underlying_price = underlying_price or float(first.last or 0.0)

        if underlying_price <= 0:
            underlying_price = max((contract.strike for contract in contracts), default=0.0)

        avg_iv = round(float(np.mean(iv_values)), 2) if iv_values else 0.0
        return OptionsChainResponse(
            symbol=symbol,
            underlying_price=round(underlying_price, 2),
            contracts=contracts,
            avg_iv=avg_iv,
            source="tradier",
            selected_expiration=selected_expiration,
            available_expirations=expirations,
            generated_at=datetime.now(tz=timezone.utc),
        )

    def get_options_chain(self, symbol: str, *, expiration: str | None = None) -> OptionsChainResponse:
        if tradier_client.is_configured():
            try:
                return self._tradier_chain(symbol, expiration=expiration)
            except (httpx.HTTPError, ValueError, TypeError):
                pass
        return self._fallback_chain(symbol, expiration=expiration)


options_service = OptionsService()
