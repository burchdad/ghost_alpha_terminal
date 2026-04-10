from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.mission_intelligence_service import MissionIntelligenceService
from app.services.system_mode_service import SystemModeService


def build_quality(*, transitions: int = 10, thrashing_count: int = 3) -> dict:
    return {
        "sample_size": 140,
        "strategy_quality": {
            "core_trend": {"settled": 30, "win_rate": 0.62},
            "mean_reversion": {"settled": 25, "win_rate": 0.61},
            "crypto_momentum": {"settled": 18, "win_rate": 0.63},
        },
        "strategy_lifecycle_transition_summary": {
            "total_transitions": transitions,
            "thrashing_strategies": [f"strategy_{index}" for index in range(thrashing_count)],
        },
    }


def build_meta_risk() -> dict:
    return {
        "mode": "normal",
        "thrashing_detected": False,
        "correlation_spike": {"spike": False, "recent_avg_correlation": 0.12},
        "confidence_collapse": {"collapse": False, "recent_avg_confidence": 0.68},
    }


def build_live_mode() -> dict:
    return {"promoted_at": None}


class SystemModePredictivePreventionTests(unittest.TestCase):
    def make_service(self) -> SystemModeService:
        service = SystemModeService()
        service._loaded = True
        service._persist_state = lambda: setattr(service, "_last_write_verification_ok", True)
        service._health_history = deque(maxlen=service.HEALTH_HISTORY_WINDOW)
        return service

    def test_predictive_warning_activates_on_health_trend(self) -> None:
        service = self.make_service()
        service._health_history.extend(
            [
                {"score": 0.96, "drift_magnitude": 1.0, "conflict_score": 0.0, "retry_count": 0},
                {"score": 0.94, "drift_magnitude": 1.5, "conflict_score": 0.0, "retry_count": 0},
            ]
        )
        service._last_write_retry_count = 2
        service._last_write_backoff_seconds = 0.15

        result = service.evaluate(
            goal_pressure=1.04,
            drawdown_pct=0.0,
            quality=build_quality(),
            meta_risk=build_meta_risk(),
            live_mode=build_live_mode(),
        )

        predictive = result["predictive_prevention"]
        self.assertTrue(predictive["early_warning"])
        self.assertGreaterEqual(predictive["warning_score"], 0.35)
        self.assertIn("health_trending_down", predictive["signals"])

    def test_predictive_warning_preemptively_shifts_balanced_to_defensive(self) -> None:
        service = self.make_service()
        service._health_history.extend(
            [
                {"score": 0.95, "drift_magnitude": 1.0, "conflict_score": 0.0, "retry_count": 0},
                {"score": 0.93, "drift_magnitude": 1.0, "conflict_score": 0.0, "retry_count": 1},
            ]
        )
        service._last_write_retry_count = 2
        service._last_write_backoff_seconds = 0.15

        result = service.evaluate(
            goal_pressure=1.04,
            drawdown_pct=0.0,
            quality=build_quality(),
            meta_risk=build_meta_risk(),
            live_mode=build_live_mode(),
        )

        self.assertEqual(result["candidate_mode"], "BALANCED")
        self.assertEqual(result["predictive_prevention"]["base_mode"], "BALANCED")
        self.assertTrue(result["predictive_prevention"]["preventive_shift_applied"])
        self.assertEqual(result["mode"], "DEFENSIVE")
        self.assertEqual(result["predictive_prevention"]["effective_mode"], "DEFENSIVE")

    def test_predictive_tuning_raises_threshold_after_false_positive(self) -> None:
        service = self.make_service()
        service._last_predictive_observation = {
            "signals": ["health_trending_down"],
            "warning_score": 0.41,
            "warning_threshold": 0.35,
            "watch_threshold": 0.25,
            "phase": "EARLY_WARNING",
        }

        tuning = service._update_predictive_tuning(
            health={"score": 0.92},
            meta_risk_mode="normal",
            sanity={"score": 0.0},
            experiment_instability={"score": 0.12},
            candidate_mode="BALANCED",
            confirmed_mode="BALANCED",
        )

        self.assertGreaterEqual(tuning["warning_threshold"], service.PREDICTIVE_BASE_WARNING_THRESHOLD)
        self.assertLess(
            tuning["weights"]["health_trending_down"],
            service.PREDICTIVE_SIGNAL_BASE_WEIGHTS["health_trending_down"],
        )

    def test_predictive_tuning_rewards_true_positive_signal(self) -> None:
        service = self.make_service()
        service._last_predictive_observation = {
            "signals": ["rising_retry_counts"],
            "warning_score": 0.41,
            "warning_threshold": 0.35,
            "watch_threshold": 0.25,
            "phase": "EARLY_WARNING",
        }

        tuning = service._update_predictive_tuning(
            health={"score": 0.64},
            meta_risk_mode="elevated",
            sanity={"score": 0.12},
            experiment_instability={"score": 0.44},
            candidate_mode="DEFENSIVE",
            confirmed_mode="BALANCED",
        )

        self.assertGreater(
            tuning["weights"]["rising_retry_counts"],
            service.PREDICTIVE_SIGNAL_BASE_WEIGHTS["rising_retry_counts"],
        )
        self.assertGreaterEqual(tuning["event_precision"], 0.5)

    def test_predictive_tuning_reports_signal_rankings_and_lead_time(self) -> None:
        service = self.make_service()
        service._last_predictive_observation = {
            "timestamp": (datetime.now(tz=timezone.utc) - timedelta(minutes=90)).isoformat(),
            "signals": ["rising_retry_counts", "increasing_drift"],
            "warning_score": 0.46,
            "warning_threshold": 0.35,
            "watch_threshold": 0.25,
            "phase": "EARLY_WARNING",
        }

        tuning = service._update_predictive_tuning(
            health={"score": 0.65},
            meta_risk_mode="elevated",
            sanity={"score": 0.22},
            experiment_instability={"score": 0.62},
            candidate_mode="DEFENSIVE",
            confirmed_mode="BALANCED",
        )

        self.assertGreater(tuning["average_lead_hours"], 0.0)
        self.assertTrue(len(tuning["signal_rankings"]) > 0)
        self.assertIn("rising_retry_counts", tuning["signal_quality"])

    def test_predictive_tuning_suppresses_repeated_false_positive_signal(self) -> None:
        service = self.make_service()

        for _ in range(4):
            service._last_predictive_observation = {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "signals": ["health_trending_down"],
                "warning_score": 0.42,
                "warning_threshold": 0.35,
                "watch_threshold": 0.25,
                "phase": "EARLY_WARNING",
            }
            service._update_predictive_tuning(
                health={"score": 0.96},
                meta_risk_mode="normal",
                sanity={"score": 0.0},
                experiment_instability={"score": 0.10},
                candidate_mode="BALANCED",
                confirmed_mode="BALANCED",
            )

        tuning = service._predictive_tuning_snapshot()
        quality = tuning["signal_quality"]["health_trending_down"]
        self.assertLess(quality["contribution_multiplier"], 1.0)
        self.assertTrue(bool(quality["suppressed"]))
        self.assertLess(
            tuning["weights"]["health_trending_down"],
            service.PREDICTIVE_SIGNAL_BASE_WEIGHTS["health_trending_down"],
        )

    def test_operator_alerts_warn_before_visible_shift(self) -> None:
        system_mode = {
            "mode": "BALANCED",
            "predictive_prevention": {
                "early_warning": False,
                "watch_active": True,
                "phase": "WATCH",
                "warning_score": 0.35,
                "signals": ["health_trending_down"],
                "preventive_mode": "DEFENSIVE",
                "preventive_shift_applied": False,
                "tuning": {
                    "warning_threshold": 0.39,
                    "watch_threshold": 0.28,
                    "average_reliability": 0.5,
                    "bias_aggressiveness": 0.45,
                    "samples": 0,
                    "weights": {"health_trending_down": 0.35},
                    "event_precision": 0.5,
                    "false_positive_rate": 0.0,
                },
            },
        }

        alerts = MissionIntelligenceService._operator_alerts(system_mode=system_mode)

        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["phase"], "WATCH")
        self.assertEqual(alert["severity"], "INFO")
        self.assertIn("warning score 0.35", alert["message"])
        self.assertIn("DEFENSIVE", alert["message"])

    def test_mission_intelligence_route_exposes_operator_alert_payload(self) -> None:
        payload = {
            "mission": {
                "mission_style": "steady",
                "goal_pressure_multiplier": 1.02,
                "tuning": {"min_confidence_floor": 0.56, "concurrency_target": 3},
                "risk_posture": {"mode": "normal"},
                "capital_buckets": {},
            },
            "compounding": {},
            "strategy_evolution": {},
            "time_weighted_confidence": {},
            "system_confidence": {"score": 0.8, "label": "HIGH", "factors": {}},
            "system_mode": {
                "mode": "BALANCED",
                "reason": "System operating in steady-state growth mode.",
                "predictive_prevention": {
                    "early_warning": True,
                    "warning_score": 0.47,
                    "signals": ["health_trending_down", "rising_retry_counts"],
                    "preventive_mode": "DEFENSIVE",
                    "preventive_shift_applied": False,
                },
            },
            "operator_alerts": [
                {
                    "code": "system_mode_predictive_prevention",
                    "phase": "EARLY_WARNING",
                    "severity": "WARNING",
                    "title": "Predictive Failure Warning",
                    "message": "Predictive warning score 0.47 indicates a likely DEFENSIVE downgrade if deterioration continues. Signals: health_trending_down, rising_retry_counts.",
                    "score": 0.47,
                    "target_mode": "DEFENSIVE",
                    "signals": ["health_trending_down", "rising_retry_counts"],
                }
            ],
            "meta_risk_governor": {},
            "live_experiment_mode": {},
            "sprint_governance": {"active": False},
            "execution_quality": {"disabled_strategies": []},
            "parity_watchdog": {"status": "GREEN", "mode": "aligned", "issues": []},
        }

        with (
            patch("app.main.initialize_database"),
            patch("app.main.coinbase_ws_service.start"),
            patch("app.main.coinbase_ws_service.stop"),
            patch("app.api.routes.metrics.mission_intelligence_service.snapshot", return_value=payload),
        ):
            with TestClient(app) as client:
                response = client.get("/metrics/mission-intelligence")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("operator_alerts", body)
        self.assertEqual(len(body["operator_alerts"]), 1)
        alert = body["operator_alerts"][0]
        self.assertEqual(alert["phase"], "EARLY_WARNING")
        self.assertEqual(alert["severity"], "WARNING")
        self.assertEqual(alert["target_mode"], "DEFENSIVE")
        self.assertEqual(alert["signals"], ["health_trending_down", "rising_retry_counts"])
        self.assertEqual(response.headers.get("x-request-id") is not None, True)


if __name__ == "__main__":
    unittest.main()