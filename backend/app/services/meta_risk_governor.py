from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

from app.db.models import DecisionAudit
from app.db.models import MetaRiskCooldownState
from app.db.session import get_session
from app.services.execution_journal import execution_journal
from app.services.strategy_lifecycle_transition_store import strategy_lifecycle_transition_store


class MetaRiskGovernor:
    """Global risk and evolution control to prevent system-wide collapse and thrashing."""

    THRASH_TRANSITIONS_24H = 8
    CONFIDENCE_COLLAPSE_THRESHOLD = 0.52
    CORRELATION_SPIKE_THRESHOLD = 0.72

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._persisted_mode = "normal"
        self._persisted_cooldown_until: datetime | None = None
        self._persisted_exposure_multiplier = 1.0
        self._persisted_disable_evolution = False
        self._persisted_frozen_strategies: list[str] = []

    @staticmethod
    def _as_utc(ts: datetime | None) -> datetime | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    @staticmethod
    def _mode_rank(mode: str) -> int:
        if mode == "critical":
            return 3
        if mode == "elevated":
            return 2
        return 1

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                with get_session() as session:
                    row = session.query(MetaRiskCooldownState).filter(MetaRiskCooldownState.scope == "global").first()
                    if row is not None:
                        self._persisted_mode = str(row.mode or "normal")
                        self._persisted_cooldown_until = self._as_utc(row.cooldown_until)
                        self._persisted_exposure_multiplier = float(row.exposure_multiplier or 1.0)
                        self._persisted_disable_evolution = bool(row.disable_evolution_temporarily)
                        try:
                            parsed = json.loads(row.frozen_strategies_json or "[]")
                            if isinstance(parsed, list):
                                self._persisted_frozen_strategies = [str(item).upper() for item in parsed if str(item).strip()]
                        except Exception:
                            self._persisted_frozen_strategies = []
            except Exception:
                pass
            self._loaded = True

    def _persist_state(self, *, mode: str, cooldown_until: datetime | None, exposure_multiplier: float, disable_evolution: bool, frozen_strategies: list[str], transitions_24h: int) -> None:
        try:
            with get_session() as session:
                row = session.query(MetaRiskCooldownState).filter(MetaRiskCooldownState.scope == "global").first()
                if row is None:
                    row = MetaRiskCooldownState(scope="global")
                    session.add(row)
                row.mode = mode
                row.cooldown_until = cooldown_until
                row.exposure_multiplier = exposure_multiplier
                row.disable_evolution_temporarily = disable_evolution
                row.frozen_strategies_json = json.dumps(sorted(set(frozen_strategies)))
                row.last_transitions_24h = int(transitions_24h)
                row.updated_at = datetime.now(tz=timezone.utc)
        except Exception:
            return

        with self._lock:
            self._persisted_mode = mode
            self._persisted_cooldown_until = cooldown_until
            self._persisted_exposure_multiplier = exposure_multiplier
            self._persisted_disable_evolution = disable_evolution
            self._persisted_frozen_strategies = sorted(set(frozen_strategies))

    def _cooldown_for_mode(self, *, mode: str, thrashing: bool, worsening: bool) -> datetime | None:
        now = datetime.now(tz=timezone.utc)
        if mode == "critical":
            return now + timedelta(hours=6)
        if mode == "elevated" and (thrashing or worsening):
            return now + timedelta(hours=2)
        return None

    def _drawdown_trend(self) -> dict:
        rows = [
            row
            for row in execution_journal.recent(limit=400)
            if str(row.outcome_label or "").upper() in {"WIN", "LOSS"} and row.pnl is not None
        ]
        if len(rows) < 16:
            return {
                "worsening": False,
                "recent_win_rate": 0.5,
                "previous_win_rate": 0.5,
                "recent_avg_pnl": 0.0,
                "previous_avg_pnl": 0.0,
            }

        recent = rows[-16:]
        previous = rows[-32:-16] if len(rows) >= 32 else rows[:16]
        if not previous:
            previous = recent

        def _stats(block: list) -> tuple[float, float]:
            wins = sum(1 for row in block if str(row.outcome_label).upper() == "WIN")
            avg_pnl = sum(float(row.pnl or 0.0) for row in block) / max(len(block), 1)
            return wins / max(len(block), 1), avg_pnl

        recent_win, recent_avg = _stats(recent)
        prev_win, prev_avg = _stats(previous)

        worsening = (recent_win + 0.07 < prev_win) or (recent_avg + 35.0 < prev_avg)
        return {
            "worsening": bool(worsening),
            "recent_win_rate": round(recent_win, 4),
            "previous_win_rate": round(prev_win, 4),
            "recent_avg_pnl": round(recent_avg, 2),
            "previous_avg_pnl": round(prev_avg, 2),
        }

        def _confidence_collapse_signal(self) -> dict:
            rows = execution_journal.recent(limit=220)
            confidences = [
                float(getattr(row, "confidence", 0.0) or 0.0)
                for row in rows
                if float(getattr(row, "confidence", 0.0) or 0.0) > 0.0
            ]
            if len(confidences) < 20:
                return {
                    "collapse": False,
                    "recent_avg_confidence": 0.5,
                    "previous_avg_confidence": 0.5,
                    "threshold": self.CONFIDENCE_COLLAPSE_THRESHOLD,
                }

            recent = confidences[-20:]
            previous = confidences[-40:-20] if len(confidences) >= 40 else confidences[:20]
            if not previous:
                previous = recent

            recent_avg = sum(recent) / max(len(recent), 1)
            previous_avg = sum(previous) / max(len(previous), 1)
            collapse = recent_avg < self.CONFIDENCE_COLLAPSE_THRESHOLD or (recent_avg + 0.08 < previous_avg)
            return {
                "collapse": bool(collapse),
                "recent_avg_confidence": round(recent_avg, 4),
                "previous_avg_confidence": round(previous_avg, 4),
                "threshold": self.CONFIDENCE_COLLAPSE_THRESHOLD,
            }

        def _correlation_spike_signal(self) -> dict:
            scores: list[float] = []
            try:
                with get_session() as session:
                    rows = (
                        session.query(DecisionAudit)
                        .order_by(DecisionAudit.timestamp.desc())
                        .limit(140)
                        .all()
                    )
                for row in rows:
                    try:
                        context = json.loads(row.context_snapshot or "{}")
                        market_reaction = context.get("market_reaction") or {}
                        score = float(market_reaction.get("correlation_score", 0.0) or 0.0)
                        scores.append(score)
                    except Exception:
                        continue
            except Exception:
                scores = []

            if len(scores) < 16:
                return {
                    "spike": False,
                    "recent_avg_correlation": 0.0,
                    "previous_avg_correlation": 0.0,
                    "threshold": self.CORRELATION_SPIKE_THRESHOLD,
                }

            recent = scores[:16]
            previous = scores[16:32] if len(scores) >= 32 else scores[-16:]
            recent_avg = sum(recent) / max(len(recent), 1)
            previous_avg = sum(previous) / max(len(previous), 1)
            spike = recent_avg > self.CORRELATION_SPIKE_THRESHOLD or (recent_avg > previous_avg + 0.15)
            return {
                "spike": bool(spike),
                "recent_avg_correlation": round(recent_avg, 4),
                "previous_avg_correlation": round(previous_avg, 4),
                "threshold": self.CORRELATION_SPIKE_THRESHOLD,
            }
    def _confidence_collapse_signal(self) -> dict:
        rows = execution_journal.recent(limit=220)
        confidences = [
            float(getattr(row, "confidence", 0.0) or 0.0)
            for row in rows
            if float(getattr(row, "confidence", 0.0) or 0.0) > 0.0
        ]
        if len(confidences) < 20:
            return {
                "collapse": False,
                "recent_avg_confidence": 0.5,
                "previous_avg_confidence": 0.5,
                "threshold": self.CONFIDENCE_COLLAPSE_THRESHOLD,
            }

        recent = confidences[-20:]
        previous = confidences[-40:-20] if len(confidences) >= 40 else confidences[:20]
        if not previous:
            previous = recent

        recent_avg = sum(recent) / max(len(recent), 1)
        previous_avg = sum(previous) / max(len(previous), 1)
        collapse = recent_avg < self.CONFIDENCE_COLLAPSE_THRESHOLD or (recent_avg + 0.08 < previous_avg)
        return {
            "collapse": bool(collapse),
            "recent_avg_confidence": round(recent_avg, 4),
            "previous_avg_confidence": round(previous_avg, 4),
            "threshold": self.CONFIDENCE_COLLAPSE_THRESHOLD,
        }

    def _correlation_spike_signal(self) -> dict:
        scores: list[float] = []
        try:
            with get_session() as session:
                rows = (
                    session.query(DecisionAudit)
                    .order_by(DecisionAudit.timestamp.desc())
                    .limit(140)
                    .all()
                )
            for row in rows:
                try:
                    context = json.loads(row.context_snapshot or "{}")
                    market_reaction = context.get("market_reaction") or {}
                    score = float(market_reaction.get("correlation_score", 0.0) or 0.0)
                    scores.append(score)
                except Exception:
                    continue
        except Exception:
            scores = []

        if len(scores) < 16:
            return {
                "spike": False,
                "recent_avg_correlation": 0.0,
                "previous_avg_correlation": 0.0,
                "threshold": self.CORRELATION_SPIKE_THRESHOLD,
            }

        recent = scores[:16]
        previous = scores[16:32] if len(scores) >= 32 else scores[-16:]
        recent_avg = sum(recent) / max(len(recent), 1)
        previous_avg = sum(previous) / max(len(previous), 1)
        spike = recent_avg > self.CORRELATION_SPIKE_THRESHOLD or (recent_avg > previous_avg + 0.15)
        return {
            "spike": bool(spike),
            "recent_avg_correlation": round(recent_avg, 4),
            "previous_avg_correlation": round(previous_avg, 4),
            "threshold": self.CORRELATION_SPIKE_THRESHOLD,
        }

    def evaluate(self, *, drawdown_pct: float) -> dict:
        self._ensure_loaded()
        transition_summary = strategy_lifecycle_transition_store.summary(since_hours=24)
        transitions_24h = int(transition_summary.get("total_transitions", 0) or 0)
        thrashing = transitions_24h > self.THRASH_TRANSITIONS_24H
        frozen_strategies = [
            str(item.get("strategy", "")).upper()
            for item in transition_summary.get("thrashing_strategies", [])
            if str(item.get("strategy", "")).strip()
        ]

        trend = self._drawdown_trend()
        worsening = bool(trend.get("worsening", False))
        confidence_signal = self._confidence_collapse_signal()
        confidence_collapse = bool(confidence_signal.get("collapse", False))
        correlation_signal = self._correlation_spike_signal()
        correlation_spike = bool(correlation_signal.get("spike", False))

        if drawdown_pct >= 0.10 or (worsening and drawdown_pct >= 0.07) or (confidence_collapse and correlation_spike and drawdown_pct >= 0.05):
            mode = "critical"
            exposure_multiplier = 0.60
        elif drawdown_pct >= 0.06 or worsening or thrashing or confidence_collapse or correlation_spike:
            mode = "elevated"
            exposure_multiplier = 0.80
        else:
            mode = "normal"
            exposure_multiplier = 1.0

        disable_evolution = mode == "critical" or (worsening and drawdown_pct >= 0.06)
        reduce_global_risk = mode != "normal"

        now = datetime.now(tz=timezone.utc)
        cooldown_until = self._cooldown_for_mode(mode=mode, thrashing=thrashing, worsening=worsening)

        persisted_cooldown = self._persisted_cooldown_until
        cooldown_active = bool(persisted_cooldown and persisted_cooldown > now)
        if cooldown_active:
            if self._mode_rank(self._persisted_mode) > self._mode_rank(mode):
                mode = self._persisted_mode
            exposure_multiplier = min(exposure_multiplier, float(self._persisted_exposure_multiplier or 1.0))
            disable_evolution = disable_evolution or bool(self._persisted_disable_evolution)
            reduce_global_risk = True
            frozen_strategies = sorted(set(frozen_strategies + list(self._persisted_frozen_strategies)))

        if cooldown_until is None and cooldown_active:
            cooldown_until = persisted_cooldown

        self._persist_state(
            mode=mode,
            cooldown_until=cooldown_until,
            exposure_multiplier=exposure_multiplier,
            disable_evolution=disable_evolution,
            frozen_strategies=frozen_strategies,
            transitions_24h=transitions_24h,
        )

        return {
            "as_of": datetime.now(tz=timezone.utc).isoformat(),
            "mode": mode,
            "drawdown_pct": round(float(drawdown_pct or 0.0), 4),
            "drawdown_trend": trend,
            "confidence_collapse": confidence_signal,
            "correlation_spike": correlation_signal,
            "transition_summary_24h": transition_summary,
            "transitions_last_24h": transitions_24h,
            "thrash_threshold": self.THRASH_TRANSITIONS_24H,
            "thrashing_detected": thrashing,
            "force_strategy_freeze": thrashing,
            "frozen_strategies": sorted(set(frozen_strategies)),
            "reduce_global_risk": reduce_global_risk,
            "global_exposure_multiplier": exposure_multiplier,
            "disable_evolution_temporarily": disable_evolution,
            "cooldown_until": cooldown_until.isoformat() if isinstance(cooldown_until, datetime) else None,
            "cooldown_active": bool(cooldown_until and cooldown_until > now),
        }

    def reset_cooldown(self) -> dict:
        self._ensure_loaded()
        self._persist_state(
            mode="normal",
            cooldown_until=None,
            exposure_multiplier=1.0,
            disable_evolution=False,
            frozen_strategies=[],
            transitions_24h=0,
        )
        now = datetime.now(tz=timezone.utc)
        return {
            "as_of": now.isoformat(),
            "mode": "normal",
            "cooldown_until": None,
            "cooldown_active": False,
            "global_exposure_multiplier": 1.0,
            "disable_evolution_temporarily": False,
            "frozen_strategies": [],
            "reset": True,
        }


meta_risk_governor = MetaRiskGovernor()
