from __future__ import annotations

from collections import defaultdict
from math import tanh

from app.services.execution_journal import execution_journal


class ExecutionQualityEngine:
    """Derive execution-quality and post-trade learning signals from journal history."""

    @staticmethod
    def _asset_class(symbol: str) -> str:
        upper = (symbol or "").upper()
        if upper.endswith("USD") and len(upper) <= 12:
            return "crypto"
        return "equity"

    @staticmethod
    def _confidence_band(confidence: float) -> str:
        c = max(0.0, min(confidence, 1.0))
        if c < 0.55:
            return "low"
        if c < 0.65:
            return "mid"
        if c < 0.75:
            return "high"
        return "very_high"

    @staticmethod
    def _score(*, submission_rate: float, win_rate: float, avg_pnl: float, slippage_flag_rate: float) -> float:
        pnl_component = tanh(avg_pnl / 250.0)
        raw = (
            0.50
            + (submission_rate - 0.50) * 0.40
            + (win_rate - 0.50) * 0.30
            + pnl_component * 0.20
            - slippage_flag_rate * 0.20
        )
        return max(0.0, min(raw, 1.0))

    def summary(self, *, limit: int = 500) -> dict:
        entries = execution_journal.recent(limit=limit)
        if not entries:
            return {
                "sample_size": 0,
                "symbol_quality": {},
                "asset_class_quality": {},
                "regime_quality": {},
                "strategy_quality": {},
                "confidence_band_quality": {},
            }

        by_symbol: dict[str, list] = defaultdict(list)
        by_asset: dict[str, list] = defaultdict(list)
        by_regime: dict[str, list] = defaultdict(list)
        by_strategy: dict[str, list] = defaultdict(list)
        by_band: dict[str, list] = defaultdict(list)

        for entry in entries:
            symbol = str(entry.symbol or "").upper()
            asset_class = self._asset_class(symbol)
            by_symbol[symbol].append(entry)
            by_asset[asset_class].append(entry)
            by_regime[str(entry.regime or "UNKNOWN").upper()].append(entry)
            by_strategy[str(entry.strategy or "UNKNOWN").upper()].append(entry)
            by_band[self._confidence_band(float(entry.confidence or 0.0))].append(entry)

        def aggregate(group: list) -> dict:
            attempts = len(group)
            submitted = sum(1 for row in group if bool(row.submitted))
            settled = [row for row in group if row.outcome_label in {"WIN", "LOSS"} and row.pnl is not None]
            wins = sum(1 for row in settled if str(row.outcome_label).upper() == "WIN")
            pnl_values = [float(row.pnl or 0.0) for row in settled]
            reasons = [f"{row.reason or ''} {row.error or ''}".lower() for row in group]
            slippage_flags = sum(
                1
                for txt in reasons
                if any(key in txt for key in ("slippage", "spread", "liquidity", "price moved", "partial fill"))
            )
            submission_rate = submitted / max(attempts, 1)
            win_rate = wins / max(len(settled), 1)
            avg_pnl = sum(pnl_values) / max(len(pnl_values), 1)
            slippage_flag_rate = slippage_flags / max(attempts, 1)
            return {
                "attempts": attempts,
                "submitted": submitted,
                "settled": len(settled),
                "submission_rate": round(submission_rate, 4),
                "win_rate": round(win_rate, 4),
                "avg_pnl": round(avg_pnl, 4),
                "slippage_flag_rate": round(slippage_flag_rate, 4),
                "quality_score": round(
                    self._score(
                        submission_rate=submission_rate,
                        win_rate=win_rate,
                        avg_pnl=avg_pnl,
                        slippage_flag_rate=slippage_flag_rate,
                    ),
                    4,
                ),
            }

        symbol_quality = {key: aggregate(rows) for key, rows in by_symbol.items()}
        asset_quality = {key: aggregate(rows) for key, rows in by_asset.items()}
        regime_quality = {key: aggregate(rows) for key, rows in by_regime.items()}
        strategy_quality = {key: aggregate(rows) for key, rows in by_strategy.items()}
        confidence_band_quality = {key: aggregate(rows) for key, rows in by_band.items()}

        return {
            "sample_size": len(entries),
            "symbol_quality": symbol_quality,
            "asset_class_quality": asset_quality,
            "regime_quality": regime_quality,
            "strategy_quality": strategy_quality,
            "confidence_band_quality": confidence_band_quality,
        }


execution_quality_engine = ExecutionQualityEngine()
