from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean

from app.services.historical_data_service import historical_data_service


class SignalValidationEngine:
    """Validates raw news signals with source weighting, recency decay, and confirmation checks."""

    _source_weights = {
        "REUTERS_PUBLIC": 1.0,
        "SEC_FILINGS": 0.95,
        "FED_RELEASES": 0.95,
        "NASDAQ_NEWSROOM": 0.85,
        "YAHOO_FINANCE_PUBLIC": 0.65,
        "COINDESK_PUBLIC": 0.55,
    }
    _default_source_weight = 0.35
    _half_life_hours = 8.0

    def _source_weight(self, source: str) -> float:
        return float(self._source_weights.get(source, self._default_source_weight))

    def validate(
        self,
        *,
        symbol: str,
        sources_used: list[str],
        sentiment_score: float,
        news_momentum_score: float,
        event_strength: float,
    ) -> dict:
        upper = symbol.upper()
        unique_sources = sorted(set(sources_used))
        seed = abs(hash(f"signal-validation:{upper}"))

        source_details: list[dict] = []
        decayed_weights: list[float] = []
        decay_factors: list[float] = []

        for idx, source in enumerate(unique_sources):
            # Deterministic age simulation for mock/public mode.
            age_hours = float(((seed >> (idx * 4)) % 30) + 1)
            decay = 0.5 ** (age_hours / self._half_life_hours)
            base_weight = self._source_weight(source)
            weighted = base_weight * decay
            source_details.append(
                {
                    "source": source,
                    "source_weight": round(base_weight, 4),
                    "age_hours": round(age_hours, 2),
                    "decay_factor": round(decay, 6),
                    "effective_weight": round(weighted, 6),
                }
            )
            decayed_weights.append(weighted)
            decay_factors.append(decay)

        average_source_weight = mean(decayed_weights) if decayed_weights else 0.0
        recency_decay_factor = mean(decay_factors) if decay_factors else 0.0

        confirmation_count = len(unique_sources)
        if confirmation_count <= 1:
            confirmation_factor = 0.72
            confirmation_label = "WEAK"
        elif confirmation_count == 2:
            confirmation_factor = 0.92
            confirmation_label = "MEDIUM"
        else:
            confirmation_factor = min(1.2, 1.0 + (confirmation_count - 3) * 0.05)
            confirmation_label = "STRONG"

        raw_signal_strength = (
            abs(float(sentiment_score)) * 0.42
            + float(news_momentum_score) * 0.33
            + float(event_strength) * 0.25
        )

        validated_signal_strength = max(
            0.0,
            min(
                1.0,
                raw_signal_strength * max(0.1, average_source_weight) * confirmation_factor * 1.45,
            ),
        )

        return {
            "recency_decay_factor": round(recency_decay_factor, 6),
            "average_source_weight": round(average_source_weight, 6),
            "confirmation_count": confirmation_count,
            "confirmation_factor": round(confirmation_factor, 6),
            "confirmation_label": confirmation_label,
            "raw_signal_strength": round(raw_signal_strength, 6),
            "validated_signal_strength": round(validated_signal_strength, 6),
            "source_details": source_details,
        }

    def market_reaction_correlation(
        self,
        *,
        symbol: str,
        sentiment_score: float,
        news_momentum_score: float,
        event_strength: float,
    ) -> dict:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=120)
        candles = historical_data_service.load_historical_data(
            symbol=symbol.upper(),
            timeframe="1d",
            start_date=start,
            end_date=end,
        )
        close = [float(v) for v in candles["close"].tolist() if float(v) > 0]
        volume = [float(v) for v in candles["volume"].tolist() if float(v) > 0]

        if len(close) < 25 or len(volume) < 25:
            return {
                "price_reaction_pct": 0.0,
                "volume_spike_ratio": 1.0,
                "breakout": "NONE",
                "expected_direction": "NEUTRAL",
                "price_direction": "FLAT",
                "correlation_score": 0.0,
                "actionability_multiplier": 1.0,
            }

        price_reaction_pct = (close[-1] / close[-2]) - 1.0
        avg_volume_20 = sum(volume[-21:-1]) / 20.0
        volume_spike_ratio = volume[-1] / max(avg_volume_20, 1.0)

        lookback_high = max(close[-21:-1])
        lookback_low = min(close[-21:-1])
        breakout = "NONE"
        if close[-1] > lookback_high:
            breakout = "UP"
        elif close[-1] < lookback_low:
            breakout = "DOWN"

        expected_score = float(sentiment_score) + (float(news_momentum_score) - 0.5) * 0.35 + float(event_strength) * 0.25
        if expected_score > 0.06:
            expected_direction = "UP"
            expected_sign = 1.0
        elif expected_score < -0.06:
            expected_direction = "DOWN"
            expected_sign = -1.0
        else:
            expected_direction = "NEUTRAL"
            expected_sign = 0.0

        if price_reaction_pct > 0.001:
            price_direction = "UP"
            price_sign = 1.0
        elif price_reaction_pct < -0.001:
            price_direction = "DOWN"
            price_sign = -1.0
        else:
            price_direction = "FLAT"
            price_sign = 0.0

        alignment = 0.0
        if expected_sign != 0.0 and price_sign != 0.0:
            alignment = expected_sign * price_sign

        volume_factor = max(0.0, min((volume_spike_ratio - 1.0) / 1.5, 1.0))
        breakout_bonus = 0.0
        if breakout == "UP" and expected_sign >= 0:
            breakout_bonus = 0.2
        elif breakout == "DOWN" and expected_sign <= 0:
            breakout_bonus = 0.2

        reaction_strength = max(
            0.0,
            min(1.0, abs(price_reaction_pct) * 28.0 + volume_factor * 0.55 + breakout_bonus),
        )

        correlation_score = max(-1.0, min(1.0, alignment * 0.55 + reaction_strength * 0.45))
        actionability_multiplier = max(0.7, min(1.35, 1.0 + correlation_score * 0.25))

        return {
            "price_reaction_pct": round(price_reaction_pct, 6),
            "volume_spike_ratio": round(volume_spike_ratio, 6),
            "breakout": breakout,
            "expected_direction": expected_direction,
            "price_direction": price_direction,
            "correlation_score": round(correlation_score, 6),
            "actionability_multiplier": round(actionability_multiplier, 6),
        }


signal_validation_engine = SignalValidationEngine()
