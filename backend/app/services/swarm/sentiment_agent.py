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

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class SentimentAgent(TradingAgent):
    name = "sentiment_agent"

    # Will be populated by a real feed in a future phase
    _sentiment_score: float = 0.0  # -1 bearish → +1 bullish

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        """
        Stub: in production this would call an external sentiment feed
        and set `_sentiment_score` to a value in [-1, +1].
        """
        self._snapshot = snapshot
        # Placeholder: no real data yet — stay neutral
        self._sentiment_score = 0.0
        self.confidence_score = 0.5

    def generate_signal(self) -> SwarmSignal:
        return SwarmSignal(
            agent_name=self.name,
            action="HOLD",
            confidence=self.confidence_score,
            reasoning=(
                "Sentiment feed not yet connected. "
                "Defaulting to HOLD pending external data. "
                "Future hook: Fear/Greed Index + NLP news scoring."
            ),
        )
