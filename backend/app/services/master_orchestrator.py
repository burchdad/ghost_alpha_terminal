"""master_orchestrator.py

GhostAlpha Intelligence Engine — the meta-agent that sits above all other agents.

Responsibilities:
  1. Scans the full UNIVERSE and ranks opportunities by composite score
  2. Selects strategy type per candidate (OPTIONS_PLAY, SWING_TRADE, DAY_TRADE, SCALP, WATCH, IGNORE)
  3. Generates a market narrative summary
  4. Manages auto-mode state
  5. Caches the latest scan result for instant UI reads

Architecture position:
  [UNIVERSE tickers]
       ↓
  [opportunity_scanner]  ← existing scoring + prefilter
       ↓
  [MasterOrchestrator]   ← strategy selection + narrative (this file)
       ↓
  [OrchestratorPanel UI] ← ranked feed with ▶ RUN buttons
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.services.control_engine import control_engine
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.opportunity_scanner import opportunity_scanner
from app.services.portfolio_manager import portfolio_manager

StrategyType = Literal["OPTIONS_PLAY", "SWING_TRADE", "DAY_TRADE", "SCALP", "WATCH", "IGNORE"]
ActionLabel = Literal["EXECUTE", "SIMULATE", "MONITOR", "SKIP"]


@dataclass
class OrchestratorCandidate:
    rank: int
    symbol: str
    asset_class: str
    region: str
    composite_score: float
    strategy_type: StrategyType
    action_label: ActionLabel
    regime: str
    consensus_bias: str
    consensus_confidence: float
    momentum_score: float
    volume_spike: float
    news_strength: float
    volatility: float
    expected_return_pct: float
    risk_level: str
    tradable: bool
    reasoning: str


@dataclass
class OrchestratorScanResult:
    candidates: list[OrchestratorCandidate]
    market_narrative: str
    regime_summary: dict[str, int]
    sector_leaders: list[str]
    scanned_at: datetime
    scan_count: int
    total_scanned: int
    passed_prefilter: int
    auto_mode: bool


class MasterOrchestrator:
    """
    The 'brain above the brain' — decides WHICH tickers to focus on and
    WHAT strategy to apply before routing into the existing agent pipeline.
    """

    SCORE_THRESHOLD_EXECUTE = 0.68
    SCORE_THRESHOLD_SIMULATE = 0.45

    def __init__(self) -> None:
        self._auto_mode: bool = False
        self._auto_interval_seconds: int = 300
        self._scan_count: int = 0
        self._last_scan_at: datetime | None = None
        self._latest_result: OrchestratorScanResult | None = None

    # ── Strategy Selection ─────────────────────────────────────────────────

    def _select_strategy(
        self,
        regime: str,
        volatility: float,
        news_strength: float,
        consensus_bias: str,
        confidence: float,
        momentum_score: float,
        asset_class: str,
        composite_score: float,
    ) -> StrategyType:
        if composite_score < 0.18:
            return "IGNORE"

        # High volatility + news catalyst → options structure is most efficient
        if regime == "HIGH_VOLATILITY" and (news_strength > 0.40 or volatility > 0.07):
            return "OPTIONS_PLAY"

        # Crypto with strong momentum → tight scalp window
        if asset_class == "crypto" and regime == "TRENDING" and consensus_bias != "NEUTRAL" and confidence > 0.60:
            return "SCALP"

        # Strong trend + strong directional consensus → swing trade
        if regime == "TRENDING" and consensus_bias != "NEUTRAL" and confidence >= 0.63 and momentum_score > 0.005:
            return "SWING_TRADE"

        # ETF with elevated vol + catalyst → options play
        if asset_class == "etf" and news_strength > 0.30 and volatility > 0.04 and regime != "RANGE_BOUND":
            return "OPTIONS_PLAY"

        # Range-bound + decent confidence → day trade / mean-reversion
        if regime == "RANGE_BOUND" and confidence >= 0.55:
            return "DAY_TRADE"

        # Promising but not confirmed
        if composite_score >= 0.28:
            return "WATCH"

        return "IGNORE"

    def _select_action(
        self, strategy: StrategyType, tradable: bool, composite_score: float
    ) -> ActionLabel:
        if strategy == "IGNORE":
            return "SKIP"
        if not tradable or composite_score < self.SCORE_THRESHOLD_SIMULATE:
            return "MONITOR"
        if composite_score >= self.SCORE_THRESHOLD_EXECUTE:
            return "EXECUTE"
        return "SIMULATE"

    # ── Market Narrative ───────────────────────────────────────────────────

    def _build_narrative(
        self,
        candidates: list[OrchestratorCandidate],
        regime_summary: dict[str, int],
        total_scanned: int,
        passed: int,
    ) -> str:
        if not candidates:
            return (
                "No actionable opportunities detected after full universe scan. "
                "Market conditions are ambiguous — standing by for next scan cycle."
            )

        top = candidates[:3]
        top_symbols = ", ".join(c.symbol for c in top)

        dominant_regime = max(regime_summary, key=lambda k: regime_summary[k])
        options_plays = sum(1 for c in candidates if c.strategy_type == "OPTIONS_PLAY")
        swing_plays = sum(1 for c in candidates if c.strategy_type == "SWING_TRADE")
        scalps = sum(1 for c in candidates if c.strategy_type == "SCALP")
        execute_count = sum(1 for c in candidates if c.action_label == "EXECUTE")
        simulate_count = sum(1 for c in candidates if c.action_label == "SIMULATE")

        bullish_count = sum(1 for c in candidates if c.consensus_bias == "BULLISH")
        bearish_count = sum(1 for c in candidates if c.consensus_bias == "BEARISH")
        if bullish_count > bearish_count * 1.5:
            bias_label = "broadly bullish"
        elif bearish_count > bullish_count * 1.5:
            bias_label = "broadly bearish"
        else:
            bias_label = "mixed directional"

        avg_score = sum(c.composite_score for c in candidates) / len(candidates)
        strength_label = "strong" if avg_score > 0.6 else "moderate" if avg_score > 0.4 else "weak"

        lines: list[str] = []
        lines.append(
            f"Intelligence scan complete — {total_scanned} tickers evaluated, "
            f"{passed} passed prefilter, {len(candidates)} ranked. "
            f"Dominant regime: {dominant_regime.replace('_', ' ')}. "
            f"Overall signal environment is {bias_label} with {strength_label} conviction."
        )

        strategy_parts: list[str] = []
        if options_plays:
            strategy_parts.append(f"{options_plays} options play(s)")
        if swing_plays:
            strategy_parts.append(f"{swing_plays} swing setup(s)")
        if scalps:
            strategy_parts.append(f"{scalps} scalp(s)")
        if strategy_parts:
            lines.append(
                f"Strategy mix: {', '.join(strategy_parts)} identified. "
                f"Top picks by composite score: {top_symbols}."
            )

        if execute_count > 0:
            lines.append(
                f"{execute_count} position(s) cleared all risk and allocation gates — ready for execution. "
                f"{simulate_count} additional candidate(s) queued for simulation."
            )
        else:
            lines.append(
                "No candidates have cleared all execution gates — all positions in simulation or monitoring status."
            )

        return " ".join(lines)

    # ── Primary Scan ──────────────────────────────────────────────────────

    def scan(self, limit: int = 20) -> OrchestratorScanResult:
        """
        Full market scan: calls opportunity_scanner, then layers strategy
        selection, action routing, and narrative generation on top.
        """
        portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
        ctrl = control_engine.status()
        goal = goal_engine.status(current_capital=float(portfolio["account_balance"]))

        raw = opportunity_scanner.scan(
            limit=limit,
            account_balance=float(portfolio["account_balance"]),
            drawdown_pct=float(ctrl["rolling_drawdown_pct"]),
            current_exposure_pct=float(portfolio["risk_exposure_pct"]),
            goal_pressure_multiplier=float(goal["goal_pressure_multiplier"]),
        )

        candidates: list[OrchestratorCandidate] = []
        regime_summary: dict[str, int] = {}

        for rank, opp in enumerate(raw["opportunities"], start=1):
            regime = opp.get("regime", "RANGE_BOUND")
            regime_summary[regime] = regime_summary.get(regime, 0) + 1

            volatility = float(opp.get("realized_volatility_pct", 0.03))
            news_strength = max(
                float(opp.get("sentiment_score", 0.0)),
                float(opp.get("news_momentum_score", 0.0)),
                float(opp.get("event_strength", 0.0)),
            )
            confidence = float(opp.get("consensus_confidence", 0.5))
            ctx_mods = opp.get("context_modifiers") or {}
            momentum_score = float(ctx_mods.get("opportunity_boost", 0.0))
            composite_score = float(opp.get("opportunity_score", 0.0))

            # Normalise to [0, 1] — raw opportunity_score is typically in [0, ~1.4]
            norm_score = min(1.0, composite_score / 1.3)

            strategy = self._select_strategy(
                regime=regime,
                volatility=volatility,
                news_strength=news_strength,
                consensus_bias=opp.get("consensus_bias", "NEUTRAL"),
                confidence=confidence,
                momentum_score=momentum_score,
                asset_class=opp.get("asset_class", "equity"),
                composite_score=norm_score,
            )
            action = self._select_action(strategy, bool(opp.get("tradable", False)), norm_score)

            reasoning_parts: list[str] = [
                f"Regime: {regime}",
                f"Bias: {opp.get('consensus_bias', 'NEUTRAL')} @ {confidence:.0%}",
                f"Vol: {volatility:.1%}",
            ]
            if news_strength > 0.25:
                reasoning_parts.append(f"News: {news_strength:.2f}")
            if strategy == "OPTIONS_PLAY":
                reasoning_parts.append("elevated vol + catalyst favors options structure")
            elif strategy == "SWING_TRADE":
                reasoning_parts.append("trend alignment supports multi-day hold")
            elif strategy == "DAY_TRADE":
                reasoning_parts.append("range-bound — intraday mean-reversion setup")
            elif strategy == "SCALP":
                reasoning_parts.append("momentum burst — short window, tight stop")

            avg_dollar_vol = float(opp.get("avg_dollar_volume", 0.0))
            candidates.append(
                OrchestratorCandidate(
                    rank=rank,
                    symbol=opp["symbol"],
                    asset_class=opp.get("asset_class", "equity"),
                    region=opp.get("region", "US"),
                    composite_score=round(norm_score, 4),
                    strategy_type=strategy,
                    action_label=action,
                    regime=regime,
                    consensus_bias=opp.get("consensus_bias", "NEUTRAL"),
                    consensus_confidence=round(confidence, 4),
                    momentum_score=round(momentum_score, 4),
                    volume_spike=round(avg_dollar_vol / 1_000_000, 2),
                    news_strength=round(news_strength, 4),
                    volatility=round(volatility, 4),
                    expected_return_pct=round(float(opp.get("expected_return_pct", 0.0)), 6),
                    risk_level=opp.get("risk_level", "MEDIUM"),
                    tradable=bool(opp.get("tradable", False)),
                    reasoning=", ".join(reasoning_parts),
                )
            )

        narrative = self._build_narrative(
            candidates, regime_summary, raw["scanned"], raw["passed_prefilter"]
        )
        sector_leaders = [c.symbol for c in candidates[:5]]

        self._scan_count += 1
        self._last_scan_at = datetime.now(tz=timezone.utc)

        result = OrchestratorScanResult(
            candidates=candidates,
            market_narrative=narrative,
            regime_summary=regime_summary,
            sector_leaders=sector_leaders,
            scanned_at=self._last_scan_at,
            scan_count=self._scan_count,
            total_scanned=raw["scanned"],
            passed_prefilter=raw["passed_prefilter"],
            auto_mode=self._auto_mode,
        )
        self._latest_result = result
        return result

    # ── Auto Mode ─────────────────────────────────────────────────────────

    def set_auto_mode(self, enabled: bool, interval_seconds: int | None = None) -> None:
        self._auto_mode = enabled
        if interval_seconds is not None:
            self._auto_interval_seconds = max(60, min(interval_seconds, 3600))

    def status(self) -> dict:
        top_pick: dict | None = None
        if self._latest_result and self._latest_result.candidates:
            c = self._latest_result.candidates[0]
            top_pick = {
                "symbol": c.symbol,
                "strategy_type": c.strategy_type,
                "composite_score": c.composite_score,
            }
        return {
            "auto_mode": self._auto_mode,
            "auto_interval_seconds": self._auto_interval_seconds,
            "scan_count": self._scan_count,
            "last_scan_at": self._last_scan_at.isoformat() if self._last_scan_at else None,
            "top_pick": top_pick,
        }

    def latest(self) -> OrchestratorScanResult | None:
        return self._latest_result


master_orchestrator = MasterOrchestrator()
