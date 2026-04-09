from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import ForecastResponse, OptionsChainResponse, SignalResponse


class SignalEngine:
    def generate_signal(self, symbol: str, forecast: ForecastResponse, options_data: OptionsChainResponse) -> SignalResponse:
        avg_iv = options_data.avg_iv
        signal = "HOLD"
        reasoning = "No clear setup from current forecast/options blend."
        confidence = 0.5

        if forecast.direction == "UP":
            if avg_iv < 30:
                signal = "BUY_CALL"
                reasoning = "Bullish direction with relatively cheap implied volatility."
                confidence = min(0.92, forecast.confidence + 0.1)
            elif avg_iv > 60:
                signal = "SELL_PUT_SPREAD"
                reasoning = "Bullish direction with expensive volatility favors premium selling."
                confidence = min(0.9, forecast.confidence + 0.06)

        if forecast.volatility == "HIGH":
            signal = "STRADDLE"
            reasoning = "High volatility regime supports long-volatility structures."
            confidence = max(confidence, 0.72)

        if forecast.range_bound:
            signal = "IRON_CONDOR"
            reasoning = "Range-bound price action favors neutral income strategies."
            confidence = max(0.68, forecast.confidence)

        return SignalResponse(
            symbol=symbol.upper(),
            signal=signal,
            confidence=round(float(confidence), 3),
            reasoning=reasoning,
            generated_at=datetime.now(tz=timezone.utc),
        )


signal_engine = SignalEngine()
