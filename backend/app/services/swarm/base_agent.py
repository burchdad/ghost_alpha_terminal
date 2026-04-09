"""
Base class for all execution-oriented trading agents in the swarm layer.

Each agent receives a standardised MarketSnapshot and returns a
SwarmSignal.  The base contract is:

    analyze_market(snapshot)   → populates internal state from data
    generate_signal()          → returns SwarmSignal (BUY / SELL / HOLD)
    confidence_score           → float 0–1 (set after analyze_market)

Both methods must be implemented by every concrete agent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class MarketSnapshot:
    """Minimal market context passed to every agent on each cycle."""
    symbol: str
    close_prices: list[float]          # ordered oldest → newest, required ≥ 2
    volumes: list[float]
    current_price: float
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"] = "RANGE_BOUND"
    regime_confidence: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class SwarmSignal:
    """Output contract every agent must produce."""
    agent_name: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float              # 0–1
    reasoning: str
    suggested_qty: float = 1.0     # fractional units; execution bridge may round
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class TradingAgent(ABC):
    """Abstract base for all swarm agents."""

    #: Unique identifier — override in subclasses
    name: str = "base_agent"

    #: Set by analyze_market(); read by external callers
    confidence_score: float = 0.5

    @abstractmethod
    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        """Update internal state from the current market snapshot."""

    @abstractmethod
    def generate_signal(self) -> SwarmSignal:
        """Return a trading signal. Must be called after analyze_market()."""

    def run(self, snapshot: MarketSnapshot) -> SwarmSignal:
        """Convenience: analyze then generate in one call."""
        self.analyze_market(snapshot)
        return self.generate_signal()
