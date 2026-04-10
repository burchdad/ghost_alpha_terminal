from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import tanh
import threading

from app.services.execution_journal import execution_journal
from app.services.strategy_lifecycle_transition_store import strategy_lifecycle_transition_store
from app.services.strategy_kill_switch_service import strategy_kill_switch_service


class ExecutionQualityEngine:
    """Derive execution-quality and post-trade learning signals from journal history."""

    PROBATION_THRESHOLD = 0.52
    DISABLE_THRESHOLD = 0.45
    MAX_PROBATION_DAYS = 14
    RETEST_WINDOW_TRADES = 12
    RETEST_PASS_WIN_RATE = 0.55
    RETEST_COOLDOWN_HOURS = 24

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._probation_state: dict[str, dict] = {}

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

    @staticmethod
    def _bucket_for_strategy(strategy: str) -> str:
        s = (strategy or "").upper()
        if "SPRINT" in s:
            return "high_risk_sprint"
        if any(token in s for token in ("SCALP", "CRYPTO")):
            return "crypto_momentum"
        if any(token in s for token in ("MEAN", "DAY", "RANGE")):
            return "mean_reversion"
        return "core_trend"

    @staticmethod
    def _as_utc(ts: datetime | None) -> datetime:
        if ts is None:
            return datetime.now(tz=timezone.utc)
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    @staticmethod
    def _iso(ts: datetime | None) -> str | None:
        if ts is None:
            return None
        return ts.isoformat()

    def _recovery_threshold(self, probation_age_days: int) -> float:
        if probation_age_days < 5:
            return self.PROBATION_THRESHOLD
        if probation_age_days < 10:
            return 0.53
        if probation_age_days < self.MAX_PROBATION_DAYS:
            return 0.54
        return self.RETEST_PASS_WIN_RATE

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
                "disabled_strategies": [],
                "raw_disabled_strategies": [],
                "probation_strategies": [],
                "raw_probation_strategies": [],
                "forced_retest_strategies": [],
                "raw_forced_retest_strategies": [],
                "manual_force_enabled": strategy_kill_switch_service.list_force_enabled(),
                "strategy_kill_switches": [],
                "strategy_states": [],
                "strategy_lifecycle_transitions": strategy_lifecycle_transition_store.recent(limit=200, since_hours=168),
                "strategy_lifecycle_transition_summary": strategy_lifecycle_transition_store.summary(since_hours=168),
                "bucket_quality": {},
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

        strategy_kill_switches: list[dict] = []
        disabled_strategies: list[str] = []
        probation_strategies: list[str] = []
        forced_retest_strategies: list[str] = []
        strategy_states: list[dict] = []
        observed_strategies = set(by_strategy.keys())
        latest_timestamp = max(
            (self._as_utc(getattr(entry, "timestamp", None)) for entry in entries),
            default=datetime.now(tz=timezone.utc),
        )

        with self._state_lock:
            strategy_lifecycle_state = dict(self._probation_state)

        for name, rows in by_strategy.items():
            settled = [row for row in rows if row.outcome_label in {"WIN", "LOSS"} and row.pnl is not None]
            state_meta = strategy_lifecycle_state.get(name, {})
            active_retest = bool(state_meta.get("retest_active"))
            recent_settled = settled[-50:]
            if len(recent_settled) < 50 and not active_retest:
                continue
            wins = sum(1 for row in recent_settled if str(row.outcome_label).upper() == "WIN")
            win_rate = wins / max(len(recent_settled), 1)
            state = "enabled"
            probation_age_days = 0
            recovery_threshold = self.PROBATION_THRESHOLD

            entered_probation_at = state_meta.get("entered_probation_at")
            if isinstance(entered_probation_at, datetime):
                probation_age_days = max(0, int((latest_timestamp - entered_probation_at).total_seconds() // 86400))
                recovery_threshold = self._recovery_threshold(probation_age_days)

            if active_retest:
                window = int(state_meta.get("retest_window_trades") or self.RETEST_WINDOW_TRADES)
                recent_retest_settled = settled[-window:]
                if len(recent_retest_settled) < window:
                    state = "forced_retest"
                    forced_retest_strategies.append(name)
                else:
                    retest_wins = sum(1 for row in recent_retest_settled if str(row.outcome_label).upper() == "WIN")
                    retest_win_rate = retest_wins / float(window)
                    if retest_win_rate >= self.RETEST_PASS_WIN_RATE:
                        state = "enabled"
                        strategy_lifecycle_state.pop(name, None)
                    elif retest_win_rate < self.DISABLE_THRESHOLD:
                        state = "disabled"
                        disabled_strategies.append(name)
                        strategy_lifecycle_state.pop(name, None)
                        strategy_kill_switches.append(
                            {
                                "strategy": name,
                                "window_trades": 50,
                                "win_rate": round(win_rate, 4),
                                "threshold": self.DISABLE_THRESHOLD,
                                "disabled": True,
                                "source": "forced_retest",
                            }
                        )
                    else:
                        state = "probation"
                        probation_strategies.append(name)
                        strategy_lifecycle_state[name] = {
                            "entered_probation_at": latest_timestamp,
                            "retest_active": False,
                            "retest_window_trades": self.RETEST_WINDOW_TRADES,
                            "cooldown_until": latest_timestamp + timedelta(hours=self.RETEST_COOLDOWN_HOURS),
                            "retest_failures": int(state_meta.get("retest_failures", 0)) + 1,
                        }
                        probation_age_days = 0
                        recovery_threshold = self._recovery_threshold(probation_age_days)
            elif win_rate < self.DISABLE_THRESHOLD:
                disabled_strategies.append(name)
                state = "disabled"
                strategy_lifecycle_state.pop(name, None)
                strategy_kill_switches.append(
                    {
                        "strategy": name,
                        "window_trades": 50,
                        "win_rate": round(win_rate, 4),
                        "threshold": self.DISABLE_THRESHOLD,
                        "disabled": True,
                    }
                )
            elif name in strategy_lifecycle_state or win_rate < self.PROBATION_THRESHOLD:
                if not isinstance(entered_probation_at, datetime):
                    entered_probation_at = latest_timestamp
                probation_age_days = max(0, int((latest_timestamp - entered_probation_at).total_seconds() // 86400))
                recovery_threshold = self._recovery_threshold(probation_age_days)
                cooldown_until = state_meta.get("cooldown_until")
                if isinstance(cooldown_until, datetime):
                    cooldown_until_utc = cooldown_until
                else:
                    cooldown_until_utc = None

                if win_rate >= recovery_threshold:
                    state = "enabled"
                    strategy_lifecycle_state.pop(name, None)
                elif probation_age_days >= self.MAX_PROBATION_DAYS and (
                    cooldown_until_utc is None or latest_timestamp >= cooldown_until_utc
                ):
                    state = "forced_retest"
                    forced_retest_strategies.append(name)
                    strategy_lifecycle_state[name] = {
                        "entered_probation_at": entered_probation_at,
                        "retest_active": True,
                        "retest_started_at": latest_timestamp,
                        "retest_window_trades": self.RETEST_WINDOW_TRADES,
                        "cooldown_until": latest_timestamp + timedelta(hours=self.RETEST_COOLDOWN_HOURS),
                        "retest_failures": int(state_meta.get("retest_failures", 0)),
                    }
                else:
                    state = "probation"
                    probation_strategies.append(name)
                    strategy_lifecycle_state[name] = {
                        "entered_probation_at": entered_probation_at,
                        "retest_active": False,
                        "retest_window_trades": self.RETEST_WINDOW_TRADES,
                        "cooldown_until": cooldown_until_utc,
                        "retest_failures": int(state_meta.get("retest_failures", 0)),
                    }
            else:
                strategy_lifecycle_state.pop(name, None)

            strategy_states.append(
                {
                    "strategy": name,
                    "window_trades": 50,
                    "win_rate": round(win_rate, 4),
                    "state": state,
                    "probation_threshold": self.PROBATION_THRESHOLD,
                    "disable_threshold": self.DISABLE_THRESHOLD,
                    "recovery_threshold": round(recovery_threshold, 4),
                    "probation_age_days": probation_age_days,
                    "max_probation_days": self.MAX_PROBATION_DAYS,
                    "retest_window_trades": self.RETEST_WINDOW_TRADES,
                    "retest_pass_win_rate": self.RETEST_PASS_WIN_RATE,
                    "entered_probation_at": self._iso(
                        strategy_lifecycle_state.get(name, {}).get("entered_probation_at")
                    ),
                    "retest_started_at": self._iso(
                        strategy_lifecycle_state.get(name, {}).get("retest_started_at")
                    ),
                }
            )
            strategy_lifecycle_transition_store.record_state(
                strategy=name,
                state=state,
                win_rate=win_rate,
                window_trades=len(recent_settled),
                timestamp=latest_timestamp,
            )

        with self._state_lock:
            self._probation_state = {
                strategy: meta
                for strategy, meta in strategy_lifecycle_state.items()
                if strategy in observed_strategies
            }

        manual_force_enabled = strategy_kill_switch_service.list_force_enabled()
        manual_force_enabled_set = set(manual_force_enabled)
        effective_disabled_strategies = sorted(
            name for name in disabled_strategies if name not in manual_force_enabled_set
        )
        effective_probation_strategies = sorted(
            name for name in probation_strategies if name not in manual_force_enabled_set
        )
        effective_forced_retest_strategies = sorted(
            name for name in forced_retest_strategies if name not in manual_force_enabled_set
        )

        bucket_quality_raw: dict[str, list[float]] = defaultdict(list)
        for strategy, stats in strategy_quality.items():
            bucket = self._bucket_for_strategy(strategy)
            bucket_quality_raw[bucket].append(float(stats.get("quality_score", 0.5) or 0.5))
        bucket_quality = {
            bucket: {
                "quality_score": round(sum(scores) / max(len(scores), 1), 4),
                "strategies": len(scores),
            }
            for bucket, scores in bucket_quality_raw.items()
        }

        return {
            "sample_size": len(entries),
            "symbol_quality": symbol_quality,
            "asset_class_quality": asset_quality,
            "regime_quality": regime_quality,
            "strategy_quality": strategy_quality,
            "confidence_band_quality": confidence_band_quality,
            "disabled_strategies": effective_disabled_strategies,
            "raw_disabled_strategies": sorted(disabled_strategies),
            "probation_strategies": effective_probation_strategies,
            "raw_probation_strategies": sorted(probation_strategies),
            "forced_retest_strategies": effective_forced_retest_strategies,
            "raw_forced_retest_strategies": sorted(forced_retest_strategies),
            "manual_force_enabled": manual_force_enabled,
            "strategy_kill_switches": strategy_kill_switches,
            "strategy_states": strategy_states,
            "strategy_lifecycle_transitions": strategy_lifecycle_transition_store.recent(limit=200, since_hours=168),
            "strategy_lifecycle_transition_summary": strategy_lifecycle_transition_store.summary(since_hours=168),
            "bucket_quality": bucket_quality,
        }


execution_quality_engine = ExecutionQualityEngine()
