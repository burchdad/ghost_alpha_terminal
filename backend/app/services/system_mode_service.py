from __future__ import annotations

from collections import deque
import logging
import threading
import time
from datetime import datetime, timezone
from math import floor
from statistics import pstdev
from typing import Literal

from app.db.models import SystemModeState
from app.db.session import get_session


SystemMode = Literal["AGGRESSIVE_GROWTH", "BALANCED", "DEFENSIVE", "SURVIVAL"]


logger = logging.getLogger(__name__)


class SystemModeService:
    """Computes a sticky, confidence-aware system identity across subsystems."""

    FAST_BUCKET_MINUTES = 2
    NORMAL_BUCKET_MINUTES = 5
    CALM_BUCKET_MINUTES = 8
    BASE_CONFIRMATION_CYCLES = 2
    CONFIDENCE_DECAY_PER_BUCKET = 0.86
    CLOCK_DRIFT_THRESHOLD_SECONDS = 90.0
    CLOCK_DRIFT_SMALL_SECONDS = 20.0
    WRITE_RETRY_ATTEMPTS = 3
    WRITE_RETRY_BASE_DELAY_SECONDS = 0.05
    MODERATE_DRIFT_CONFIDENCE_MULTIPLIER = 0.82
    SEVERE_DRIFT_CONFIDENCE_MULTIPLIER = 0.45
    RECOVERY_CYCLE_BUDGET = 4
    HEALTH_HISTORY_WINDOW = 6
    PREDICTIVE_TUNING_MIN_SAMPLES = 3
    PREDICTIVE_BASE_WARNING_THRESHOLD = 0.35
    PREDICTIVE_MIN_WARNING_THRESHOLD = 0.28
    PREDICTIVE_MAX_WARNING_THRESHOLD = 0.52
    PREDICTIVE_WATCH_THRESHOLD_RATIO = 0.72
    PREDICTIVE_SIGNAL_BASE_WEIGHTS: dict[str, float] = {
        "health_trending_down": 0.35,
        "rising_retry_counts": 0.18,
        "increasing_drift": 0.17,
        "growing_conflict": 0.16,
        "instability_pressure": 0.14,
    }

    _MODE_CONTROLS: dict[SystemMode, dict] = {
        "AGGRESSIVE_GROWTH": {
            "allocation_multiplier": 1.12,
            "trade_frequency_multiplier": 1.20,
            "min_confidence_floor": 0.52,
            "allow_evolution": True,
            "allow_compounding": True,
            "risk_tolerance": "high",
            "bucket_bias": {
                "core_trend": 1.04,
                "mean_reversion": 0.92,
                "crypto_momentum": 1.10,
                "high_risk_sprint": 1.16,
            },
        },
        "BALANCED": {
            "allocation_multiplier": 1.00,
            "trade_frequency_multiplier": 1.00,
            "min_confidence_floor": 0.56,
            "allow_evolution": True,
            "allow_compounding": True,
            "risk_tolerance": "medium",
            "bucket_bias": {
                "core_trend": 1.02,
                "mean_reversion": 1.00,
                "crypto_momentum": 1.00,
                "high_risk_sprint": 0.96,
            },
        },
        "DEFENSIVE": {
            "allocation_multiplier": 0.82,
            "trade_frequency_multiplier": 0.72,
            "min_confidence_floor": 0.61,
            "allow_evolution": False,
            "allow_compounding": True,
            "risk_tolerance": "low",
            "bucket_bias": {
                "core_trend": 1.05,
                "mean_reversion": 1.14,
                "crypto_momentum": 0.82,
                "high_risk_sprint": 0.44,
            },
        },
        "SURVIVAL": {
            "allocation_multiplier": 0.58,
            "trade_frequency_multiplier": 0.45,
            "min_confidence_floor": 0.67,
            "allow_evolution": False,
            "allow_compounding": False,
            "risk_tolerance": "minimal",
            "bucket_bias": {
                "core_trend": 1.06,
                "mean_reversion": 1.18,
                "crypto_momentum": 0.60,
                "high_risk_sprint": 0.20,
            },
        },
    }
    _MODE_REASON: dict[SystemMode, str] = {
        "AGGRESSIVE_GROWTH": "System pressing edge while confidence is high and instability remains controlled.",
        "BALANCED": "System operating in steady-state growth mode.",
        "DEFENSIVE": "System reducing aggression because edge quality or stability deteriorated.",
        "SURVIVAL": "System capital protection mode due to stress, instability, or collapse signals.",
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._confirmed_mode: SystemMode = "BALANCED"
        self._pending_mode: SystemMode | None = None
        self._pending_confirmation_count = 0
        self._confirmation_required = self.BASE_CONFIRMATION_CYCLES
        self._last_evaluation_bucket: str | None = None
        self._mode_confidence = 0.0
        self._last_state_updated_at: datetime | None = None
        self._last_state_monotonic: float | None = None
        self._last_write_verification_ok = True
        self._last_write_verification_error: str | None = None
        self._last_write_retry_count = 0
        self._last_write_backoff_seconds = 0.0
        self._last_known_good_mode: SystemMode = "BALANCED"
        self._recovery_cycles_remaining = 0
        self._last_recovery_actions: dict = {
            "db_reconnect_attempted": False,
            "db_reconnect_success": False,
            "state_rebuild_applied": False,
            "rehydration_target_mode": None,
        }
        self._health_history: deque[dict] = deque(maxlen=self.HEALTH_HISTORY_WINDOW)
        self._predictive_signal_stats: dict[str, dict[str, float]] = {
            name: {"true_positive": 0.0, "false_positive": 0.0, "support": 0.0}
            for name in self.PREDICTIVE_SIGNAL_BASE_WEIGHTS
        }
        self._predictive_event_stats: dict[str, float] = {
            "true_positive": 0.0,
            "false_positive": 0.0,
            "watch_true_positive": 0.0,
            "watch_false_positive": 0.0,
        }
        self._last_predictive_observation: dict | None = None
        self._last_predictive_tuning: dict = {
            "warning_threshold": self.PREDICTIVE_BASE_WARNING_THRESHOLD,
            "watch_threshold": round(self.PREDICTIVE_BASE_WARNING_THRESHOLD * self.PREDICTIVE_WATCH_THRESHOLD_RATIO, 4),
            "average_reliability": 0.5,
            "bias_aggressiveness": 0.45,
            "samples": 0,
            "weights": dict(self.PREDICTIVE_SIGNAL_BASE_WEIGHTS),
            "event_precision": 0.5,
            "false_positive_rate": 0.0,
        }

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(float(value), maximum))

    @staticmethod
    def _safe_iso_age_hours(value: str | None) -> float | None:
        if not value:
            return None
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            return max(0.0, (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600.0)
        except Exception:
            return None

    @staticmethod
    def _mode_rank(mode: SystemMode) -> int:
        ranks: dict[SystemMode, int] = {
            "SURVIVAL": 1,
            "DEFENSIVE": 2,
            "BALANCED": 3,
            "AGGRESSIVE_GROWTH": 4,
        }
        return ranks.get(mode, 3)

    @classmethod
    def _current_bucket_key(cls, now: datetime, *, bucket_minutes: int) -> str:
        safe_bucket_minutes = max(1, int(bucket_minutes or cls.NORMAL_BUCKET_MINUTES))
        minute_bucket = (now.minute // safe_bucket_minutes) * safe_bucket_minutes
        return f"{safe_bucket_minutes}:{now:%Y%m%d%H}{minute_bucket:02d}"

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                with get_session() as session:
                    row = session.query(SystemModeState).filter(SystemModeState.scope == "global").first()
                    if row is not None:
                        self._confirmed_mode = self._coerce_mode(row.confirmed_mode)
                        self._pending_mode = self._coerce_mode(row.pending_mode) if row.pending_mode else None
                        self._pending_confirmation_count = max(0, int(row.pending_confirmation_count or 0))
                        self._confirmation_required = max(self.BASE_CONFIRMATION_CYCLES, int(row.confirmation_required or self.BASE_CONFIRMATION_CYCLES))
                        self._last_evaluation_bucket = str(row.last_evaluation_bucket or "") or None
                        self._mode_confidence = self._clamp(float(row.mode_confidence or 0.0))
                        self._last_state_updated_at = row.updated_at.astimezone(timezone.utc) if row.updated_at and row.updated_at.tzinfo else (row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at else None)
                        self._last_state_monotonic = time.monotonic()
                        if self._confirmed_mode != "SURVIVAL":
                            self._last_known_good_mode = self._confirmed_mode
            except Exception:
                pass
            self._loaded = True

    @classmethod
    def _coerce_mode(cls, value: str | None) -> SystemMode:
        text = str(value or "BALANCED").strip().upper()
        if text in cls._MODE_CONTROLS:
            return text  # type: ignore[return-value]
        return "BALANCED"

    @staticmethod
    def _as_utc(ts: datetime | None) -> datetime | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    def _persist_state(self) -> None:
        previous_updated_at = self._last_state_updated_at
        last_error = "unknown"
        total_backoff_seconds = 0.0
        self._last_recovery_actions = {
            "db_reconnect_attempted": False,
            "db_reconnect_success": False,
            "state_rebuild_applied": False,
            "rehydration_target_mode": self._last_known_good_mode,
        }
        for attempt in range(1, self.WRITE_RETRY_ATTEMPTS + 1):
            updated_at = datetime.now(tz=timezone.utc)
            try:
                with get_session() as session:
                    row = session.query(SystemModeState).filter(SystemModeState.scope == "global").first()
                    if row is None:
                        row = SystemModeState(scope="global")
                        session.add(row)
                    row.confirmed_mode = self._confirmed_mode
                    row.pending_mode = self._pending_mode
                    row.pending_confirmation_count = int(self._pending_confirmation_count)
                    row.confirmation_required = int(self._confirmation_required)
                    row.last_evaluation_bucket = self._last_evaluation_bucket
                    row.mode_confidence = float(self._mode_confidence)
                    row.updated_at = updated_at
            except Exception:
                last_error = "write_failed"
                if attempt < self.WRITE_RETRY_ATTEMPTS:
                    backoff_seconds = self.WRITE_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    total_backoff_seconds += backoff_seconds
                    time.sleep(backoff_seconds)
                continue

            try:
                with get_session() as session:
                    persisted = session.query(SystemModeState).filter(SystemModeState.scope == "global").first()
                    persisted_updated_at = self._as_utc(persisted.updated_at if persisted else None)

                assert persisted_updated_at is not None
                if previous_updated_at is not None:
                    assert persisted_updated_at >= previous_updated_at

                self._last_state_updated_at = max(updated_at, persisted_updated_at)
                self._last_state_monotonic = time.monotonic()
                self._last_write_verification_ok = True
                self._last_write_verification_error = None
                self._last_write_retry_count = attempt - 1
                self._last_write_backoff_seconds = round(total_backoff_seconds, 4)
                return
            except Exception:
                last_error = "timestamp_verification_failed"
                if attempt < self.WRITE_RETRY_ATTEMPTS:
                    backoff_seconds = self.WRITE_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    total_backoff_seconds += backoff_seconds
                    time.sleep(backoff_seconds)
                continue

        self._last_write_verification_ok = False
        self._last_write_verification_error = f"{last_error}_retries_exhausted"
        self._last_write_retry_count = self.WRITE_RETRY_ATTEMPTS
        self._last_write_backoff_seconds = round(total_backoff_seconds, 4)
        self._attempt_recovery_hooks(previous_updated_at=previous_updated_at)
        self._trigger_meta_risk_alert(reason=self._last_write_verification_error)

    def _trigger_meta_risk_alert(self, *, reason: str) -> None:
        logger.error(
            "meta_risk_alert system_mode_persistence_failure reason=%s confirmed_mode=%s pending_mode=%s retries=%s",
            reason,
            self._confirmed_mode,
            self._pending_mode,
            self._last_write_retry_count,
        )

    def _attempt_recovery_hooks(self, *, previous_updated_at: datetime | None) -> None:
        actions = {
            "db_reconnect_attempted": True,
            "db_reconnect_success": False,
            "state_rebuild_applied": False,
            "rehydration_target_mode": self._last_known_good_mode,
        }
        try:
            with get_session() as session:
                persisted = session.query(SystemModeState).filter(SystemModeState.scope == "global").first()
                if persisted is not None:
                    persisted_mode = self._coerce_mode(persisted.confirmed_mode)
                    persisted_updated_at = self._as_utc(persisted.updated_at)
                    if persisted_updated_at is not None and (previous_updated_at is None or persisted_updated_at >= previous_updated_at):
                        self._confirmed_mode = persisted_mode
                        self._pending_mode = self._coerce_mode(persisted.pending_mode) if persisted.pending_mode else None
                        self._pending_confirmation_count = max(0, int(persisted.pending_confirmation_count or 0))
                        self._confirmation_required = max(1, int(persisted.confirmation_required or self.BASE_CONFIRMATION_CYCLES))
                        self._last_evaluation_bucket = str(persisted.last_evaluation_bucket or "") or None
                        self._mode_confidence = self._clamp(float(persisted.mode_confidence or 0.0))
                        self._last_state_updated_at = persisted_updated_at
                        self._last_state_monotonic = time.monotonic()
                        if persisted_mode != "SURVIVAL":
                            self._last_known_good_mode = persisted_mode
                        actions["db_reconnect_success"] = True
                        self._last_recovery_actions = actions
                        return
        except Exception:
            pass

        self._confirmed_mode = "SURVIVAL"
        self._pending_mode = None
        self._pending_confirmation_count = 0
        self._confirmation_required = self.BASE_CONFIRMATION_CYCLES
        self._mode_confidence = min(self._mode_confidence, 0.24)
        self._recovery_cycles_remaining = self.RECOVERY_CYCLE_BUDGET
        actions["state_rebuild_applied"] = True
        self._last_recovery_actions = actions

    @staticmethod
    def _system_confidence_score(*, quality: dict, drawdown_pct: float) -> float:
        sample_size = int(quality.get("sample_size", 0) or 0)
        strategy_quality = quality.get("strategy_quality", {}) or {}
        win_rates = [
            float((stats or {}).get("win_rate", 0.5) or 0.5)
            for stats in strategy_quality.values()
            if int((stats or {}).get("settled", 0) or 0) > 0
        ]

        data_sufficiency = max(0.0, min(sample_size / 120.0, 1.0))
        strategy_diversity = max(0.0, min(len(strategy_quality) / 6.0, 1.0))
        win_rate_stability = 1.0
        if len(win_rates) >= 2:
            win_rate_stability = max(0.0, 1.0 - min(pstdev(win_rates) / 0.20, 1.0))
        drawdown_pressure = max(0.0, 1.0 - min(max(drawdown_pct, 0.0) / 0.12, 1.0))
        return max(
            0.0,
            min(
                data_sufficiency * 0.30
                + strategy_diversity * 0.20
                + win_rate_stability * 0.25
                + drawdown_pressure * 0.25,
                1.0,
            ),
        )

    @staticmethod
    def _experiment_instability(*, quality: dict, meta_risk: dict, live_mode: dict) -> dict:
        transition_summary = quality.get("strategy_lifecycle_transition_summary", {}) or {}
        transitions = int(transition_summary.get("total_transitions", 0) or 0)
        thrashing_count = len(transition_summary.get("thrashing_strategies", []) or [])
        strategy_quality = quality.get("strategy_quality", {}) or {}
        win_rates = [
            float((stats or {}).get("win_rate", 0.5) or 0.5)
            for stats in strategy_quality.values()
            if int((stats or {}).get("settled", 0) or 0) > 0
        ]
        dispersion = min(pstdev(win_rates) / 0.18, 1.0) if len(win_rates) >= 2 else 0.25
        age_hours = SystemModeService._safe_iso_age_hours(str(live_mode.get("promoted_at") or "") or None)
        recent_promotion = 0.0
        if age_hours is not None:
            recent_promotion = max(0.0, min((72.0 - age_hours) / 72.0, 1.0))
        meta_mode = str(meta_risk.get("mode", "normal") or "normal")
        meta_pressure = 1.0 if meta_mode == "critical" else 0.6 if meta_mode == "elevated" else 0.15

        score = max(
            0.0,
            min(
                min(transitions / 10.0, 1.0) * 0.30
                + min(thrashing_count / 3.0, 1.0) * 0.20
                + dispersion * 0.25
                + recent_promotion * 0.10
                + meta_pressure * 0.15,
                1.0,
            ),
        )
        return {
            "score": round(score, 4),
            "transitions_last_window": transitions,
            "thrashing_strategies": thrashing_count,
            "win_rate_dispersion": round(dispersion, 4),
            "recent_promotion_pressure": round(recent_promotion, 4),
        }

    def _signal_pack(
        self,
        *,
        goal_pressure: float,
        drawdown_pct: float,
        confidence_score: float,
        experiment_instability: dict,
        meta_risk: dict,
    ) -> dict:
        correlation_signal = meta_risk.get("correlation_spike") or {}
        confidence_collapse_signal = meta_risk.get("confidence_collapse") or {}
        drawdown_signal = self._clamp(drawdown_pct / 0.10)
        confidence_signal = self._clamp(1.0 - confidence_score)
        thrash_signal = self._clamp(
            max(
                float(experiment_instability.get("score", 0.0) or 0.0),
                0.88 if bool(meta_risk.get("thrashing_detected", False)) else 0.0,
            )
        )
        correlation_raw = float(correlation_signal.get("recent_avg_correlation", 0.0) or 0.0)
        correlation_signal_score = self._clamp(max(correlation_raw, 0.80 if bool(correlation_signal.get("spike", False)) else 0.0))
        risk_pressure = self._clamp(
            drawdown_signal * 0.34
            + confidence_signal * 0.28
            + thrash_signal * 0.23
            + correlation_signal_score * 0.15
        )
        growth_pressure = self._clamp(
            self._clamp((goal_pressure - 1.0) / 0.35) * 0.55
            + confidence_score * 0.45
        )
        return {
            "drawdown_signal": round(drawdown_signal, 4),
            "confidence_signal": round(confidence_signal, 4),
            "thrash_signal": round(thrash_signal, 4),
            "correlation_signal": round(correlation_signal_score, 4),
            "risk_pressure_score": round(risk_pressure, 4),
            "growth_pressure_score": round(growth_pressure, 4),
            "goal_pressure": round(float(goal_pressure or 1.0), 4),
            "confidence_collapse": bool(confidence_collapse_signal.get("collapse", False)),
            "correlation_spike": bool(correlation_signal.get("spike", False)),
        }

    def _select_candidate_mode(self, *, signals: dict, meta_risk_mode: str) -> tuple[SystemMode, str, float]:
        risk_pressure = float(signals.get("risk_pressure_score", 0.0) or 0.0)
        growth_pressure = float(signals.get("growth_pressure_score", 0.0) or 0.0)
        hard_collapse = bool(signals.get("confidence_collapse", False)) and bool(signals.get("correlation_spike", False))

        if meta_risk_mode == "critical" or risk_pressure >= 0.72 or hard_collapse:
            candidate: SystemMode = "SURVIVAL"
            confidence = self._clamp(max(risk_pressure, 0.84 if hard_collapse else 0.0))
        elif meta_risk_mode == "elevated" or risk_pressure >= 0.50:
            candidate = "DEFENSIVE"
            defensive_center = 0.60
            band_support = 1.0 - min(abs(risk_pressure - defensive_center) / 0.28, 1.0)
            confidence = self._clamp(0.48 + band_support * 0.32 + min(risk_pressure, 0.9) * 0.20)
        elif meta_risk_mode == "normal" and risk_pressure <= 0.24 and growth_pressure >= 0.68:
            candidate = "AGGRESSIVE_GROWTH"
            confidence = self._clamp((1.0 - risk_pressure) * 0.45 + growth_pressure * 0.55)
        else:
            candidate = "BALANCED"
            balance_fit = 1.0 - min(abs(risk_pressure - 0.36) / 0.24, 1.0)
            confidence = self._clamp(0.44 + balance_fit * 0.34 + (1.0 - abs(growth_pressure - 0.55)) * 0.22)

        return candidate, self._MODE_REASON[candidate], round(confidence, 4)

    def _adaptive_bucket_minutes(self, *, signals: dict, meta_risk_mode: str, experiment_instability: dict) -> int:
        risk_pressure = float(signals.get("risk_pressure_score", 0.0) or 0.0)
        thrash_signal = float(signals.get("thrash_signal", 0.0) or 0.0)
        correlation_signal = float(signals.get("correlation_signal", 0.0) or 0.0)
        growth_pressure = float(signals.get("growth_pressure_score", 0.0) or 0.0)
        instability_score = float(experiment_instability.get("score", 0.0) or 0.0)

        if (
            meta_risk_mode == "critical"
            or risk_pressure >= 0.72
            or thrash_signal >= 0.70
            or correlation_signal >= 0.72
            or instability_score >= 0.68
        ):
            return self.FAST_BUCKET_MINUTES
        if risk_pressure <= 0.24 and growth_pressure >= 0.62 and instability_score <= 0.34:
            return self.CALM_BUCKET_MINUTES
        return self.NORMAL_BUCKET_MINUTES

    def _cross_signal_sanity_check(
        self,
        *,
        signals: dict,
        meta_risk_mode: str,
        experiment_instability: dict,
    ) -> dict:
        conflict_score = 0.0
        reasons: list[str] = []
        risk_pressure = float(signals.get("risk_pressure_score", 0.0) or 0.0)
        growth_pressure = float(signals.get("growth_pressure_score", 0.0) or 0.0)
        drawdown_signal = float(signals.get("drawdown_signal", 0.0) or 0.0)
        thrash_signal = float(signals.get("thrash_signal", 0.0) or 0.0)
        correlation_signal = float(signals.get("correlation_signal", 0.0) or 0.0)
        instability_score = float(experiment_instability.get("score", 0.0) or 0.0)

        if growth_pressure >= 0.72 and risk_pressure >= 0.52:
            conflict_score += 0.35
            reasons.append("growth_risk_conflict")
        if bool(signals.get("confidence_collapse", False)) and growth_pressure >= 0.60:
            conflict_score += 0.25
            reasons.append("confidence_collapse_vs_growth")
        if bool(signals.get("correlation_spike", False)) and growth_pressure >= 0.58:
            conflict_score += 0.20
            reasons.append("correlation_spike_vs_growth")
        if drawdown_signal <= 0.20 and (thrash_signal >= 0.75 or instability_score >= 0.72):
            conflict_score += 0.15
            reasons.append("low_drawdown_high_instability")
        if meta_risk_mode == "normal" and risk_pressure >= 0.62 and correlation_signal >= 0.60:
            conflict_score += 0.15
            reasons.append("nominal_meta_risk_with_hidden_stress")

        conflict_score = self._clamp(conflict_score)
        confidence_multiplier = self._clamp(1.0 - conflict_score * 0.45, minimum=0.55, maximum=1.0)
        return {
            "detected": bool(reasons),
            "score": round(conflict_score, 4),
            "confidence_multiplier": round(confidence_multiplier, 4),
            "reasons": reasons,
        }

    def _apply_drift_confidence_reset(
        self,
        *,
        confidence: float,
        drift_severity: str,
    ) -> tuple[float, bool, float]:
        if drift_severity == "large":
            multiplier = self.SEVERE_DRIFT_CONFIDENCE_MULTIPLIER
            return self._clamp(confidence * multiplier), True, multiplier
        if drift_severity == "moderate":
            multiplier = self.MODERATE_DRIFT_CONFIDENCE_MULTIPLIER
            return self._clamp(confidence * multiplier), True, multiplier
        return self._clamp(confidence), False, 1.0

    def _system_health_score(
        self,
        *,
        experiment_instability: dict,
        drift_detected: bool,
        drift_magnitude: float,
        sanity: dict,
    ) -> dict:
        retry_penalty = min(float(self._last_write_retry_count or 0) / max(self.WRITE_RETRY_ATTEMPTS, 1), 1.0)
        backoff_penalty = min(float(self._last_write_backoff_seconds or 0.0) / 0.35, 1.0)
        persistence_penalty = 1.0 if not self._last_write_verification_ok else 0.0
        conflict_penalty = float(sanity.get("score", 0.0) or 0.0)
        instability_penalty = min(float(experiment_instability.get("score", 0.0) or 0.0), 1.0)
        drift_penalty = min((float(drift_magnitude or 0.0) / self.CLOCK_DRIFT_THRESHOLD_SECONDS), 1.0) if drift_detected else min((float(drift_magnitude or 0.0) / self.CLOCK_DRIFT_THRESHOLD_SECONDS) * 0.25, 0.25)

        penalty = min(
            persistence_penalty * 0.34
            + retry_penalty * 0.16
            + backoff_penalty * 0.08
            + conflict_penalty * 0.16
            + drift_penalty * 0.12
            + instability_penalty * 0.14,
            1.0,
        )
        score = self._clamp(1.0 - penalty)
        return {
            "score": round(score, 4),
            "label": "GREEN" if score >= 0.78 else "YELLOW" if score >= 0.55 else "RED",
            "components": {
                "persistence_penalty": round(persistence_penalty, 4),
                "retry_penalty": round(retry_penalty, 4),
                "backoff_penalty": round(backoff_penalty, 4),
                "conflict_penalty": round(conflict_penalty, 4),
                "drift_penalty": round(drift_penalty, 4),
                "instability_penalty": round(instability_penalty, 4),
            },
        }

    def _apply_health_overlays(self, *, controls: dict, health_score: float, recovery_cycles_remaining: int) -> tuple[dict, dict]:
        safe_health = self._clamp(health_score)
        recovery_active = recovery_cycles_remaining > 0
        allocation_multiplier = float(controls.get("allocation_multiplier", 1.0) or 1.0)
        trade_frequency_multiplier = float(controls.get("trade_frequency_multiplier", 1.0) or 1.0)
        min_confidence_floor = float(controls.get("min_confidence_floor", 0.56) or 0.56)

        health_allocation_scale = 0.55 + safe_health * 0.45
        health_frequency_scale = 0.60 + safe_health * 0.40
        adjusted = {
            **controls,
            "allocation_multiplier": round(allocation_multiplier * health_allocation_scale, 4),
            "trade_frequency_multiplier": round(trade_frequency_multiplier * health_frequency_scale, 4),
            "min_confidence_floor": round(min(0.82, min_confidence_floor + (1.0 - safe_health) * 0.06), 4),
            "allow_evolution": bool(controls.get("allow_evolution", True)) and safe_health >= 0.72 and not recovery_active,
            "allow_compounding": bool(controls.get("allow_compounding", True)) and safe_health >= 0.48,
        }

        if recovery_active:
            adjusted["allocation_multiplier"] = round(float(adjusted["allocation_multiplier"]) * 0.72, 4)
            adjusted["trade_frequency_multiplier"] = round(float(adjusted["trade_frequency_multiplier"]) * 0.78, 4)
            adjusted["min_confidence_floor"] = round(min(0.85, float(adjusted["min_confidence_floor"]) + 0.03), 4)
            adjusted["allow_evolution"] = False

        recovery_phase = {
            "active": recovery_active,
            "cycles_remaining": recovery_cycles_remaining,
            "relearning_factor": round(1.0 - min(recovery_cycles_remaining / max(self.RECOVERY_CYCLE_BUDGET, 1), 1.0) * 0.45, 4) if recovery_active else 1.0,
            "rehydration_target_mode": self._last_recovery_actions.get("rehydration_target_mode") or self._last_known_good_mode,
        }
        return adjusted, recovery_phase

    def _predictive_outcome_positive(
        self,
        *,
        health: dict,
        meta_risk_mode: str,
        sanity: dict,
        experiment_instability: dict,
        candidate_mode: SystemMode,
        confirmed_mode: SystemMode,
    ) -> bool:
        return bool(
            float(health.get("score", 1.0) or 1.0) <= 0.72
            or meta_risk_mode in {"elevated", "critical"}
            or float(sanity.get("score", 0.0) or 0.0) >= 0.24
            or float(experiment_instability.get("score", 0.0) or 0.0) >= 0.58
            or candidate_mode in {"DEFENSIVE", "SURVIVAL"}
            or confirmed_mode in {"DEFENSIVE", "SURVIVAL"}
        )

    def _predictive_tuning_snapshot(self) -> dict:
        learned_weights: dict[str, float] = {}
        reliability_sum = 0.0
        sample_sum = 0.0
        for signal, base_weight in self.PREDICTIVE_SIGNAL_BASE_WEIGHTS.items():
            stats = self._predictive_signal_stats.get(signal, {})
            support = float(stats.get("support", 0.0) or 0.0)
            tp = float(stats.get("true_positive", 0.0) or 0.0)
            fp = float(stats.get("false_positive", 0.0) or 0.0)
            sample_factor = self._clamp(support / max(self.PREDICTIVE_TUNING_MIN_SAMPLES, 1))
            precision = tp / max(tp + fp, 1.0)
            reliability = ((1.0 - sample_factor) * 0.5) + (sample_factor * precision)
            learned_weights[signal] = round(base_weight * (0.7 + reliability * 0.8), 4)
            reliability_sum += reliability * max(support, 1.0)
            sample_sum += max(support, 1.0)

        tp_events = float(self._predictive_event_stats.get("true_positive", 0.0) or 0.0)
        fp_events = float(self._predictive_event_stats.get("false_positive", 0.0) or 0.0)
        watch_tp = float(self._predictive_event_stats.get("watch_true_positive", 0.0) or 0.0)
        watch_fp = float(self._predictive_event_stats.get("watch_false_positive", 0.0) or 0.0)
        event_precision = tp_events / max(tp_events + fp_events, 1.0)
        false_positive_rate = fp_events / max(tp_events + fp_events, 1.0)
        watch_precision = watch_tp / max(watch_tp + watch_fp, 1.0)
        average_reliability = reliability_sum / max(sample_sum, 1.0)
        warning_threshold = self._clamp(
            self.PREDICTIVE_BASE_WARNING_THRESHOLD
            + max(false_positive_rate - 0.32, 0.0) * 0.16
            - max(event_precision - 0.70, 0.0) * 0.08,
            minimum=self.PREDICTIVE_MIN_WARNING_THRESHOLD,
            maximum=self.PREDICTIVE_MAX_WARNING_THRESHOLD,
        )
        watch_threshold = round(warning_threshold * self.PREDICTIVE_WATCH_THRESHOLD_RATIO, 4)
        bias_aggressiveness = round(
            self._clamp(0.30 + average_reliability * 0.35 + watch_precision * 0.20, minimum=0.25, maximum=0.78),
            4,
        )
        total_samples = int(sum(float(stats.get("support", 0.0) or 0.0) for stats in self._predictive_signal_stats.values()))
        snapshot = {
            "warning_threshold": round(warning_threshold, 4),
            "watch_threshold": watch_threshold,
            "average_reliability": round(average_reliability, 4),
            "bias_aggressiveness": bias_aggressiveness,
            "samples": total_samples,
            "weights": learned_weights,
            "event_precision": round(event_precision, 4),
            "false_positive_rate": round(false_positive_rate, 4),
        }
        self._last_predictive_tuning = snapshot
        return snapshot

    def _update_predictive_tuning(
        self,
        *,
        health: dict,
        meta_risk_mode: str,
        sanity: dict,
        experiment_instability: dict,
        candidate_mode: SystemMode,
        confirmed_mode: SystemMode,
    ) -> dict:
        outcome_positive = self._predictive_outcome_positive(
            health=health,
            meta_risk_mode=meta_risk_mode,
            sanity=sanity,
            experiment_instability=experiment_instability,
            candidate_mode=candidate_mode,
            confirmed_mode=confirmed_mode,
        )
        previous_observation = self._last_predictive_observation
        if previous_observation is not None:
            observed_signals = previous_observation.get("signals", []) or []
            for signal in observed_signals:
                stats = self._predictive_signal_stats.setdefault(signal, {"true_positive": 0.0, "false_positive": 0.0, "support": 0.0})
                stats["support"] = float(stats.get("support", 0.0) or 0.0) + 1.0
                if outcome_positive:
                    stats["true_positive"] = float(stats.get("true_positive", 0.0) or 0.0) + 1.0
                else:
                    stats["false_positive"] = float(stats.get("false_positive", 0.0) or 0.0) + 1.0

            previous_score = float(previous_observation.get("warning_score", 0.0) or 0.0)
            previous_threshold = float(previous_observation.get("warning_threshold", self.PREDICTIVE_BASE_WARNING_THRESHOLD) or self.PREDICTIVE_BASE_WARNING_THRESHOLD)
            previous_watch_threshold = float(previous_observation.get("watch_threshold", previous_threshold * self.PREDICTIVE_WATCH_THRESHOLD_RATIO) or (previous_threshold * self.PREDICTIVE_WATCH_THRESHOLD_RATIO))
            if previous_score >= previous_threshold:
                event_key = "true_positive" if outcome_positive else "false_positive"
                self._predictive_event_stats[event_key] = float(self._predictive_event_stats.get(event_key, 0.0) or 0.0) + 1.0
            elif previous_score >= previous_watch_threshold:
                event_key = "watch_true_positive" if outcome_positive else "watch_false_positive"
                self._predictive_event_stats[event_key] = float(self._predictive_event_stats.get(event_key, 0.0) or 0.0) + 1.0

        return self._predictive_tuning_snapshot()

    def _predictive_failure_prevention(
        self,
        *,
        now: datetime,
        health: dict,
        drift_magnitude: float,
        sanity: dict,
        experiment_instability: dict,
        meta_risk_mode: str,
        candidate_mode: SystemMode,
        confirmed_mode: SystemMode,
    ) -> dict:
        tuning = self._update_predictive_tuning(
            health=health,
            meta_risk_mode=meta_risk_mode,
            sanity=sanity,
            experiment_instability=experiment_instability,
            candidate_mode=candidate_mode,
            confirmed_mode=confirmed_mode,
        )
        previous = list(self._health_history)
        previous_scores = [float(item.get("score", 1.0) or 1.0) for item in previous]
        previous_drifts = [float(item.get("drift_magnitude", 0.0) or 0.0) for item in previous]
        previous_conflicts = [float(item.get("conflict_score", 0.0) or 0.0) for item in previous]
        previous_retries = [int(item.get("retry_count", 0) or 0) for item in previous]

        current_score = float(health.get("score", 1.0) or 1.0)
        latest_prev_score = previous_scores[-1] if previous_scores else current_score
        baseline_score = previous_scores[0] if previous_scores else current_score
        health_delta = current_score - latest_prev_score
        trend_drop = max(0.0, baseline_score - current_score)
        learned_weights = tuning.get("weights", self.PREDICTIVE_SIGNAL_BASE_WEIGHTS)

        warning_score = 0.0
        signals: list[str] = []
        if len(previous_scores) >= 2 and (health_delta <= -0.04 or trend_drop >= 0.10):
            warning_score += float(learned_weights.get("health_trending_down", 0.35) or 0.35)
            signals.append("health_trending_down")
        if self._last_write_retry_count > 0 and self._last_write_retry_count >= (previous_retries[-1] if previous_retries else 0):
            warning_score += float(learned_weights.get("rising_retry_counts", 0.18) or 0.18)
            signals.append("rising_retry_counts")
        avg_prev_drift = sum(previous_drifts) / max(len(previous_drifts), 1) if previous_drifts else 0.0
        if drift_magnitude >= max(self.CLOCK_DRIFT_SMALL_SECONDS * 0.75, avg_prev_drift + 8.0):
            warning_score += float(learned_weights.get("increasing_drift", 0.17) or 0.17)
            signals.append("increasing_drift")
        conflict_score = float(sanity.get("score", 0.0) or 0.0)
        avg_prev_conflict = sum(previous_conflicts) / max(len(previous_conflicts), 1) if previous_conflicts else 0.0
        if conflict_score >= max(0.18, avg_prev_conflict + 0.08):
            warning_score += float(learned_weights.get("growing_conflict", 0.16) or 0.16)
            signals.append("growing_conflict")
        if float(experiment_instability.get("score", 0.0) or 0.0) >= 0.52 and current_score <= 0.80:
            warning_score += float(learned_weights.get("instability_pressure", 0.14) or 0.14)
            signals.append("instability_pressure")

        warning_score = self._clamp(warning_score)
        warning_threshold = float(tuning.get("warning_threshold", self.PREDICTIVE_BASE_WARNING_THRESHOLD) or self.PREDICTIVE_BASE_WARNING_THRESHOLD)
        watch_threshold = float(tuning.get("watch_threshold", warning_threshold * self.PREDICTIVE_WATCH_THRESHOLD_RATIO) or (warning_threshold * self.PREDICTIVE_WATCH_THRESHOLD_RATIO))
        early_warning = warning_score >= warning_threshold and current_score <= 0.88
        watch_active = not early_warning and warning_score >= watch_threshold and current_score <= 0.92
        bias_aggressiveness = float(tuning.get("bias_aggressiveness", 0.45) or 0.45)
        normalized_warning = self._clamp((warning_score - watch_threshold) / max(1.0 - watch_threshold, 0.01))
        preventive_shift_weight = round(self._clamp(0.22 + normalized_warning * bias_aggressiveness, minimum=0.0, maximum=0.84), 4) if early_warning else 0.0
        phase = "EARLY_WARNING" if early_warning else "WATCH" if watch_active else "CLEAR"

        self._health_history.append(
            {
                "timestamp": now.isoformat(),
                "score": round(current_score, 4),
                "drift_magnitude": round(float(drift_magnitude or 0.0), 4),
                "conflict_score": round(conflict_score, 4),
                "retry_count": int(self._last_write_retry_count or 0),
                "warning_score": round(warning_score, 4),
            }
        )
        self._last_predictive_observation = {
            "timestamp": now.isoformat(),
            "signals": list(signals),
            "warning_score": round(warning_score, 4),
            "warning_threshold": round(warning_threshold, 4),
            "watch_threshold": round(watch_threshold, 4),
            "phase": phase,
        }
        return {
            "early_warning": early_warning,
            "watch_active": watch_active,
            "phase": phase,
            "warning_score": round(warning_score, 4),
            "signals": signals,
            "health_delta": round(health_delta, 4),
            "trend_drop": round(trend_drop, 4),
            "preventive_mode": "DEFENSIVE" if early_warning else None,
            "preventive_shift_weight": preventive_shift_weight,
            "tuning": tuning,
        }

    def _apply_time_decay(
        self,
        *,
        now: datetime,
        bucket_minutes: int,
        pending_count: int,
        mode_confidence: float,
    ) -> tuple[int, float, float, float, str, bool, float, str]:
        wall_elapsed_seconds: float | None = None
        monotonic_elapsed_seconds: float | None = None
        if self._last_state_updated_at is not None:
            wall_elapsed_seconds = (now - self._last_state_updated_at).total_seconds()
        if self._last_state_monotonic is not None:
            monotonic_elapsed_seconds = time.monotonic() - self._last_state_monotonic

        drift_magnitude = 0.0
        drift_severity = "none"
        drift_detected = False
        if wall_elapsed_seconds is not None and monotonic_elapsed_seconds is not None:
            drift_magnitude = abs(wall_elapsed_seconds - monotonic_elapsed_seconds)
            if wall_elapsed_seconds < 0.0:
                drift_severity = "large"
                drift_detected = True
            elif drift_magnitude <= self.CLOCK_DRIFT_SMALL_SECONDS:
                drift_severity = "small"
                drift_detected = False
            elif drift_magnitude <= self.CLOCK_DRIFT_THRESHOLD_SECONDS:
                drift_severity = "moderate"
                drift_detected = True
            else:
                drift_severity = "large"
                drift_detected = True

        if drift_detected and monotonic_elapsed_seconds is not None:
            # Large drift gets a stricter decay response to avoid stale certainty after clock anomalies.
            severity_multiplier = 1.25 if drift_severity == "large" else 1.0
            elapsed_seconds = max(0.0, monotonic_elapsed_seconds * severity_multiplier)
            time_source = "monotonic"
        else:
            elapsed_seconds = max(0.0, wall_elapsed_seconds or 0.0)
            time_source = "wall_clock"

        if elapsed_seconds <= 0.0:
            return pending_count, self._clamp(mode_confidence), 1.0, 0.0, time_source, drift_detected, round(drift_magnitude, 4), drift_severity

        elapsed_minutes = elapsed_seconds / 60.0

        elapsed_buckets = elapsed_minutes / max(float(bucket_minutes), 1.0)
        decay_factor = self._clamp(self.CONFIDENCE_DECAY_PER_BUCKET ** elapsed_buckets)
        decayed_confidence = self._clamp(mode_confidence * decay_factor)
        decayed_pending = max(0, floor(pending_count * decay_factor))
        return decayed_pending, decayed_confidence, round(decay_factor, 4), round(elapsed_minutes, 2), time_source, drift_detected, round(drift_magnitude, 4), drift_severity

    def _confirmation_cycles_required(
        self,
        *,
        confirmed_mode: SystemMode,
        candidate_mode: SystemMode,
        mode_confidence: float,
        bucket_minutes: int,
    ) -> int:
        if candidate_mode == confirmed_mode:
            return 0
        mode_gap = abs(self._mode_rank(candidate_mode) - self._mode_rank(confirmed_mode))
        required = self.BASE_CONFIRMATION_CYCLES + (1 if mode_gap >= 2 else 0) + (1 if mode_confidence < 0.72 else 0)
        if bucket_minutes <= self.FAST_BUCKET_MINUTES:
            required = max(1, required - 1)
        elif bucket_minutes >= self.CALM_BUCKET_MINUTES:
            required += 1
        return max(1, min(required, 4))

    def _blend_controls(
        self,
        *,
        from_mode: SystemMode,
        to_mode: SystemMode,
        to_weight: float,
    ) -> dict:
        from_controls = self._MODE_CONTROLS[from_mode]
        to_controls = self._MODE_CONTROLS[to_mode]
        from_weight = 1.0 - to_weight
        blended_bucket_bias = {
            bucket: round(
                float(from_controls["bucket_bias"].get(bucket, 1.0)) * from_weight
                + float(to_controls["bucket_bias"].get(bucket, 1.0)) * to_weight,
                4,
            )
            for bucket in {**from_controls["bucket_bias"], **to_controls["bucket_bias"]}
        }
        allow_evolution_score = (1.0 if from_controls["allow_evolution"] else 0.0) * from_weight + (1.0 if to_controls["allow_evolution"] else 0.0) * to_weight
        allow_compounding_score = (1.0 if from_controls["allow_compounding"] else 0.0) * from_weight + (1.0 if to_controls["allow_compounding"] else 0.0) * to_weight
        dominant_mode = to_mode if to_weight >= 0.5 else from_mode
        return {
            "allocation_multiplier": round(float(from_controls["allocation_multiplier"]) * from_weight + float(to_controls["allocation_multiplier"]) * to_weight, 4),
            "trade_frequency_multiplier": round(float(from_controls["trade_frequency_multiplier"]) * from_weight + float(to_controls["trade_frequency_multiplier"]) * to_weight, 4),
            "min_confidence_floor": round(float(from_controls["min_confidence_floor"]) * from_weight + float(to_controls["min_confidence_floor"]) * to_weight, 4),
            "allow_evolution": allow_evolution_score >= 0.5,
            "allow_compounding": allow_compounding_score >= 0.5,
            "risk_tolerance": self._MODE_CONTROLS[dominant_mode]["risk_tolerance"],
            "bucket_bias": blended_bucket_bias,
        }

    def evaluate(
        self,
        *,
        goal_pressure: float,
        drawdown_pct: float,
        quality: dict,
        meta_risk: dict,
        live_mode: dict,
    ) -> dict:
        self._ensure_loaded()

        confidence_score = self._system_confidence_score(quality=quality, drawdown_pct=drawdown_pct)
        confidence_label = "HIGH" if confidence_score >= 0.72 else "MEDIUM" if confidence_score >= 0.52 else "LOW"
        experiment_instability = self._experiment_instability(quality=quality, meta_risk=meta_risk, live_mode=live_mode)
        meta_risk_mode = str(meta_risk.get("mode", "normal") or "normal")
        signals = self._signal_pack(
            goal_pressure=goal_pressure,
            drawdown_pct=drawdown_pct,
            confidence_score=confidence_score,
            experiment_instability=experiment_instability,
            meta_risk=meta_risk,
        )
        candidate_mode, candidate_reason, candidate_confidence = self._select_candidate_mode(
            signals=signals,
            meta_risk_mode=meta_risk_mode,
        )

        now = datetime.now(tz=timezone.utc)
        bucket_minutes = self._adaptive_bucket_minutes(
            signals=signals,
            meta_risk_mode=meta_risk_mode,
            experiment_instability=experiment_instability,
        )
        with self._lock:
            previous_confirmed_mode = self._confirmed_mode
            confirmed_mode = self._confirmed_mode
            pending_mode = self._pending_mode
            pending_count, decayed_stored_confidence, decay_factor, elapsed_minutes, time_source, drift_detected, drift_magnitude, drift_severity = self._apply_time_decay(
                now=now,
                bucket_minutes=bucket_minutes,
                pending_count=self._pending_confirmation_count,
                mode_confidence=self._mode_confidence,
            )
            sanity = self._cross_signal_sanity_check(
                signals=signals,
                meta_risk_mode=meta_risk_mode,
                experiment_instability=experiment_instability,
            )
            decayed_stored_confidence, decayed_reset_applied, decayed_reset_multiplier = self._apply_drift_confidence_reset(
                confidence=decayed_stored_confidence,
                drift_severity=drift_severity,
            )
            carried_confidence = decayed_stored_confidence
            if pending_mode and pending_mode != candidate_mode:
                carried_confidence *= 0.55
            elif confirmed_mode != candidate_mode:
                carried_confidence *= 0.70
            effective_candidate_confidence = self._clamp(candidate_confidence * 0.82 + carried_confidence * 0.18)
            effective_candidate_confidence = self._clamp(
                effective_candidate_confidence * float(sanity.get("confidence_multiplier", 1.0) or 1.0)
            )
            effective_candidate_confidence, effective_reset_applied, effective_reset_multiplier = self._apply_drift_confidence_reset(
                confidence=effective_candidate_confidence,
                drift_severity=drift_severity,
            )
            decayed_stored_confidence = self._clamp(decayed_stored_confidence)
            effective_candidate_confidence = self._clamp(effective_candidate_confidence)
            if confirmed_mode == "SURVIVAL" and drift_severity == "large":
                effective_candidate_confidence = self._clamp(effective_candidate_confidence * 0.80)
            evaluation_bucket = self._current_bucket_key(now, bucket_minutes=bucket_minutes)
            confirmation_required = self._confirmation_cycles_required(
                confirmed_mode=confirmed_mode,
                candidate_mode=candidate_mode,
                mode_confidence=effective_candidate_confidence,
                bucket_minutes=bucket_minutes,
            )
            duplicate_bucket = self._last_evaluation_bucket == evaluation_bucket

            if candidate_mode == confirmed_mode:
                pending_mode = None
                pending_count = 0
                confirmation_required = 0
                reason = candidate_reason
            else:
                if pending_mode != candidate_mode:
                    pending_mode = candidate_mode
                    pending_count = 0 if duplicate_bucket else 1
                elif not duplicate_bucket:
                    pending_count += 1

                if pending_count >= confirmation_required > 0:
                    confirmed_mode = candidate_mode
                    pending_mode = None
                    pending_count = 0
                    reason = candidate_reason
                else:
                    reason = (
                        f"Holding {confirmed_mode.replace('_', ' ')} until {candidate_mode.replace('_', ' ')} is confirmed "
                        f"for {confirmation_required} distinct cycles."
                    )

            transition_active = pending_mode is not None and pending_mode != confirmed_mode and confirmation_required > 0
            pending_progress = 0.0
            if transition_active:
                pending_progress = self._clamp(pending_count / max(confirmation_required, 1))
            blended_to_mode = pending_mode if transition_active else confirmed_mode
            controls = self._blend_controls(
                from_mode=confirmed_mode,
                to_mode=blended_to_mode,
                to_weight=pending_progress if transition_active else 1.0,
            )

            if previous_confirmed_mode == "SURVIVAL" and confirmed_mode != "SURVIVAL":
                self._recovery_cycles_remaining = self.RECOVERY_CYCLE_BUDGET
            elif confirmed_mode == "SURVIVAL":
                self._recovery_cycles_remaining = self.RECOVERY_CYCLE_BUDGET
            elif self._recovery_cycles_remaining > 0:
                self._recovery_cycles_remaining -= 1

            self._confirmed_mode = confirmed_mode
            self._pending_mode = pending_mode
            self._pending_confirmation_count = pending_count
            self._confirmation_required = max(confirmation_required, 0)
            self._last_evaluation_bucket = evaluation_bucket
            self._mode_confidence = effective_candidate_confidence
            self._persist_state()

            effective_mode = confirmed_mode
            effective_reason = reason
            assurance_forced_survival = False
            assurance_reason: str | None = None
            if not self._last_write_verification_ok:
                effective_mode = "SURVIVAL"
                effective_reason = "Persistence assurance failure forced SURVIVAL mode for capital protection."
                controls = dict(self._MODE_CONTROLS["SURVIVAL"])
                assurance_forced_survival = True
                assurance_reason = str(self._last_write_verification_error or "persistence_failure")
                self._recovery_cycles_remaining = self.RECOVERY_CYCLE_BUDGET

            if effective_mode != "SURVIVAL" and self._last_write_verification_ok:
                self._last_known_good_mode = effective_mode

            health = self._system_health_score(
                experiment_instability=experiment_instability,
                drift_detected=drift_detected,
                drift_magnitude=drift_magnitude,
                sanity=sanity,
            )
            predictive = self._predictive_failure_prevention(
                now=now,
                health=health,
                drift_magnitude=drift_magnitude,
                sanity=sanity,
                experiment_instability=experiment_instability,
                meta_risk_mode=meta_risk_mode,
                candidate_mode=candidate_mode,
                confirmed_mode=effective_mode,
            )
            controls, recovery_phase = self._apply_health_overlays(
                controls=controls,
                health_score=float(health.get("score", 1.0) or 1.0),
                recovery_cycles_remaining=self._recovery_cycles_remaining,
            )
            preventive_shift_applied = False
            preventive_base_mode = effective_mode
            if (
                bool(predictive.get("early_warning", False))
                and effective_mode in {"AGGRESSIVE_GROWTH", "BALANCED"}
                and not assurance_forced_survival
            ):
                preventive_shift_applied = True
                effective_mode = "DEFENSIVE"
                effective_reason = "Predictive prevention shifted the system toward DEFENSIVE before failure thresholds were hit."
                controls = self._blend_controls(
                    from_mode=preventive_base_mode,
                    to_mode="DEFENSIVE",
                    to_weight=float(predictive.get("preventive_shift_weight", 0.45) or 0.45),
                )
                controls, recovery_phase = self._apply_health_overlays(
                    controls=controls,
                    health_score=float(health.get("score", 1.0) or 1.0),
                    recovery_cycles_remaining=self._recovery_cycles_remaining,
                )

        return {
            "mode": effective_mode,
            "candidate_mode": candidate_mode,
            "reason": effective_reason,
            "candidate_reason": candidate_reason,
            "system_confidence": {
                "score": round(confidence_score, 4),
                "label": confidence_label,
            },
            "mode_confidence": {
                "score": round(effective_candidate_confidence, 4),
                "decayed_score": round(decayed_stored_confidence, 4),
                "decay_factor": decay_factor,
                "elapsed_minutes": elapsed_minutes,
                "time_source": time_source,
                "drift_detected": drift_detected,
                "drift_magnitude_seconds": drift_magnitude,
                "drift_severity": drift_severity,
                "drift_confidence_reset_applied": effective_reset_applied,
                "drift_confidence_reset_multiplier": round(effective_reset_multiplier, 4),
                "label": "HIGH" if effective_candidate_confidence >= 0.78 else "MEDIUM" if effective_candidate_confidence >= 0.58 else "LOW",
                "components": {
                    "drawdown_signal": signals["drawdown_signal"],
                    "confidence_signal": signals["confidence_signal"],
                    "thrash_signal": signals["thrash_signal"],
                    "correlation_signal": signals["correlation_signal"],
                },
                "risk_pressure_score": signals["risk_pressure_score"],
                "growth_pressure_score": signals["growth_pressure_score"],
            },
            "experiment_instability": experiment_instability,
            "predictive_prevention": {
                **predictive,
                "preventive_shift_applied": preventive_shift_applied,
                "base_mode": preventive_base_mode,
                "effective_mode": effective_mode,
            },
            "system_health": health,
            "assurance": {
                "forced_survival": assurance_forced_survival,
                "reason": assurance_reason,
                "cross_signal_conflict": sanity,
                "persistence_backoff_seconds": self._last_write_backoff_seconds,
                "drift_confidence_reset_applied": decayed_reset_applied or effective_reset_applied,
                "drift_confidence_reset_multiplier": round(
                    min(decayed_reset_multiplier, effective_reset_multiplier),
                    4,
                ),
                "recovery_hooks": self._last_recovery_actions,
                "recovery_phase": recovery_phase,
            },
            "signals": {
                "goal_pressure": signals["goal_pressure"],
                "drawdown_pct": round(float(drawdown_pct or 0.0), 4),
                "meta_risk_mode": meta_risk_mode,
                "confidence_collapse": signals["confidence_collapse"],
                "correlation_spike": signals["correlation_spike"],
            },
            "hysteresis": {
                "confirmed_mode": effective_mode,
                "pending_mode": self._pending_mode,
                "candidate_mode": candidate_mode,
                "confirmation_required": self._confirmation_required,
                "confirmation_count": self._pending_confirmation_count,
                "window_minutes": bucket_minutes,
                "progress": round(
                    self._clamp(self._pending_confirmation_count / max(self._confirmation_required, 1))
                    if self._pending_mode and self._confirmation_required > 0
                    else 1.0,
                    4,
                ),
                "active": bool(self._pending_mode),
                "evaluation_bucket": self._last_evaluation_bucket,
                "write_verification_ok": self._last_write_verification_ok,
                "write_verification_error": self._last_write_verification_error,
                "write_retry_count": self._last_write_retry_count,
                "write_backoff_seconds": self._last_write_backoff_seconds,
            },
            "blend": {
                "active": bool(self._pending_mode),
                "from_mode": effective_mode,
                "to_mode": self._pending_mode or effective_mode,
                "from_weight": round(1.0 - (self._pending_confirmation_count / max(self._confirmation_required, 1)) if self._pending_mode and self._confirmation_required > 0 else 0.0, 4),
                "to_weight": round(self._pending_confirmation_count / max(self._confirmation_required, 1) if self._pending_mode and self._confirmation_required > 0 else 1.0, 4),
            },
            "controls": controls,
        }

    def reset_to_default(self, *, source: str = "admin_reset") -> dict:
        del source
        self._ensure_loaded()
        with self._lock:
            self._confirmed_mode = "BALANCED"
            self._pending_mode = None
            self._pending_confirmation_count = 0
            self._confirmation_required = self.BASE_CONFIRMATION_CYCLES
            self._last_evaluation_bucket = None
            self._mode_confidence = 0.0
            self._health_history.clear()
            self._predictive_signal_stats = {
                name: {"true_positive": 0.0, "false_positive": 0.0, "support": 0.0}
                for name in self.PREDICTIVE_SIGNAL_BASE_WEIGHTS
            }
            self._predictive_event_stats = {
                "true_positive": 0.0,
                "false_positive": 0.0,
                "watch_true_positive": 0.0,
                "watch_false_positive": 0.0,
            }
            self._last_predictive_observation = None
            self._last_predictive_tuning = {
                "warning_threshold": self.PREDICTIVE_BASE_WARNING_THRESHOLD,
                "watch_threshold": round(self.PREDICTIVE_BASE_WARNING_THRESHOLD * self.PREDICTIVE_WATCH_THRESHOLD_RATIO, 4),
                "average_reliability": 0.5,
                "bias_aggressiveness": 0.45,
                "samples": 0,
                "weights": dict(self.PREDICTIVE_SIGNAL_BASE_WEIGHTS),
                "event_precision": 0.5,
                "false_positive_rate": 0.0,
            }
            self._persist_state()
        return {
            "mode": "BALANCED",
            "candidate_mode": "BALANCED",
            "reason": self._MODE_REASON["BALANCED"],
            "predictive_prevention": {
                "early_warning": False,
                "watch_active": False,
                "phase": "CLEAR",
                "warning_score": 0.0,
                "signals": [],
                "health_delta": 0.0,
                "trend_drop": 0.0,
                "preventive_mode": None,
                "preventive_shift_weight": 0.0,
                "preventive_shift_applied": False,
                "base_mode": "BALANCED",
                "effective_mode": "BALANCED",
                "tuning": {
                    "warning_threshold": self.PREDICTIVE_BASE_WARNING_THRESHOLD,
                    "watch_threshold": round(self.PREDICTIVE_BASE_WARNING_THRESHOLD * self.PREDICTIVE_WATCH_THRESHOLD_RATIO, 4),
                    "average_reliability": 0.5,
                    "bias_aggressiveness": 0.45,
                    "samples": 0,
                    "weights": dict(self.PREDICTIVE_SIGNAL_BASE_WEIGHTS),
                    "event_precision": 0.5,
                    "false_positive_rate": 0.0,
                },
            },
            "system_health": {
                "score": 1.0,
                "label": "GREEN",
                "components": {
                    "persistence_penalty": 0.0,
                    "retry_penalty": 0.0,
                    "backoff_penalty": 0.0,
                    "conflict_penalty": 0.0,
                    "drift_penalty": 0.0,
                    "instability_penalty": 0.0,
                },
            },
            "assurance": {
                "forced_survival": False,
                "reason": None,
                "cross_signal_conflict": {
                    "detected": False,
                    "score": 0.0,
                    "confidence_multiplier": 1.0,
                    "reasons": [],
                },
                "persistence_backoff_seconds": 0.0,
                "drift_confidence_reset_applied": False,
                "drift_confidence_reset_multiplier": 1.0,
                "recovery_hooks": {
                    "db_reconnect_attempted": False,
                    "db_reconnect_success": False,
                    "state_rebuild_applied": False,
                    "rehydration_target_mode": "BALANCED",
                },
                "recovery_phase": {
                    "active": False,
                    "cycles_remaining": 0,
                    "relearning_factor": 1.0,
                    "rehydration_target_mode": "BALANCED",
                },
            },
            "hysteresis": {
                "confirmed_mode": "BALANCED",
                "pending_mode": None,
                "candidate_mode": "BALANCED",
                "confirmation_required": self.BASE_CONFIRMATION_CYCLES,
                "confirmation_count": 0,
                "window_minutes": self.NORMAL_BUCKET_MINUTES,
                "progress": 1.0,
                "active": False,
                "evaluation_bucket": None,
                "write_verification_ok": True,
                "write_verification_error": None,
                "write_retry_count": 0,
                "write_backoff_seconds": 0.0,
            },
            "blend": {
                "active": False,
                "from_mode": "BALANCED",
                "to_mode": "BALANCED",
                "from_weight": 0.0,
                "to_weight": 1.0,
            },
            "controls": dict(self._MODE_CONTROLS["BALANCED"]),
            "reset": True,
        }


system_mode_service = SystemModeService()