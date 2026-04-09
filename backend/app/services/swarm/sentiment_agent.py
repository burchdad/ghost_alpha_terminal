"""
SentimentAgent — stub for external sentiment integration.

Currently returns HOLD with moderate confidence.  The stub is fully
wired into the swarm so that when a real sentiment feed is integrated
(news API, social scraper, fear/greed index) it only requires
filling in `analyze_market()` — nothing else changes.

Sentiment sources planned:
  - Fear & Greed Index
  - News headline NLP score
  - Reddit / social volume spike detection
"""
from __future__ import annotations

from app.services.context_intelligence import context_intelligence
from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class SentimentAgent(TradingAgent):
    name = "sentiment_agent"

    _sentiment_score: float = 0.0  # -1 bearish → +1 bullish
    _momentum_score: float = 0.0
    _event_strength: float = 0.0
    _context_reasoning: str = ""

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        context = context_intelligence.get_context(snapshot.symbol)
        sentiment = float(context.get("sentiment_score", 0.0))
        momentum = float(context.get("news_momentum_score", 0.0))
        event_strength = float(context.get("event_strength", 0.0))
        validation = context.get("signal_validation", {})
        validated_strength = float(validation.get("validated_signal_strength", 0.0))

        directional_momentum = (momentum - 0.5) * 2.0
        score = (
            sentiment * 0.55
            + directional_momentum * 0.25
            + (1.0 if sentiment >= 0 else -1.0) * event_strength * 0.2
        )

        self._sentiment_score = max(-1.0, min(score, 1.0))
        self._momentum_score = momentum
        self._event_strength = event_strength
        self.confidence_score = max(0.5, min(0.92, 0.52 + abs(self._sentiment_score) * 0.3 + validated_strength * 0.1))
        self._context_reasoning = (
            f"sentiment={sentiment:.2f}, momentum={momentum:.2f}, event={event_strength:.2f}, "
            f"validated={validated_strength:.2f}"
        )

    def generate_signal(self) -> SwarmSignal:
        action = "HOLD"
        if self._sentiment_score > 0.12:
            action = "BUY"
        elif self._sentiment_score < -0.12:
            action = "SELL"

        return SwarmSignal(
            agent_name=self.name,
            action=action,
            confidence=self.confidence_score,
            reasoning=(
                f"Context-driven sentiment signal: {self._context_reasoning}. "
                f"Blended sentiment score={self._sentiment_score:.2f}."
            ),
        )
