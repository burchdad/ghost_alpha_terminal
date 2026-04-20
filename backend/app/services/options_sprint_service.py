from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.models import OptionsSprintState
from app.db.session import get_session
from app.services.tradier_client import tradier_client


class OptionsSprintService:
    def _get_state_row(self) -> OptionsSprintState | None:
        with get_session() as session:
            return session.execute(
                select(OptionsSprintState).where(OptionsSprintState.scope == "global")
            ).scalar_one_or_none()

    def configure(
        self,
        *,
        enabled: bool,
        target_amount: float | None = None,
        timeframe_days: int | None = None,
        objective_summary: str | None = None,
        activation_source: str = "manual",
        acknowledged_high_risk: bool = False,
        allow_live_execution: bool = False,
    ) -> dict:
        now = datetime.now(tz=timezone.utc)
        with get_session() as session:
            row = session.execute(
                select(OptionsSprintState).where(OptionsSprintState.scope == "global")
            ).scalar_one_or_none()
            if row is None:
                row = OptionsSprintState(scope="global")
                session.add(row)

            row.enabled = bool(enabled)
            row.profile = "high_volume_directional"
            row.target_amount = float(target_amount) if target_amount is not None else None
            row.timeframe_days = int(timeframe_days) if timeframe_days is not None else None
            row.objective_summary = objective_summary.strip()[:500] if objective_summary else None
            row.activation_source = activation_source[:64] if activation_source else "manual"
            row.acknowledged_high_risk = bool(acknowledged_high_risk)
            row.allow_live_execution = bool(allow_live_execution)
            row.updated_at = now

        return self.status()

    def clear(self) -> dict:
        return self.configure(
            enabled=False,
            target_amount=None,
            timeframe_days=None,
            objective_summary=None,
            activation_source="manual",
            acknowledged_high_risk=False,
            allow_live_execution=False,
        )

    def live_execution_ready(self) -> tuple[bool, list[str]]:
        blockers: list[str] = []
        if not settings.tradier_live_api_key or not settings.tradier_live_account_number:
            blockers.append("Tradier live API key and account number are required for live options sprint execution.")
        if settings.tradier_sandbox:
            blockers.append("TRADIER_SANDBOX=true keeps execution in sandbox mode; switch to live mode for production routing.")
        if not tradier_client.is_configured():
            blockers.append("Active Tradier credentials are not configured for the current environment.")
        if not settings.tradier_live_trading_enabled:
            blockers.append("TRADIER_LIVE_TRADING_ENABLED must be true to submit live option orders.")
        return len(blockers) == 0, blockers

    @staticmethod
    def _strategy_bias(*, enabled: bool) -> dict[str, float]:
        if not enabled:
            return {
                "options_play_weight": 0.0,
                "directional_conviction_weight": 0.0,
                "turnover_target": 0.0,
            }
        return {
            "options_play_weight": 1.0,
            "directional_conviction_weight": 0.72,
            "turnover_target": 0.85,
        }

    def status(self) -> dict:
        row = self._get_state_row()
        live_ready, blockers = self.live_execution_ready()

        if row is None:
            return {
                "enabled": False,
                "profile": "high_volume_directional",
                "target_amount": None,
                "timeframe_days": None,
                "objective_summary": None,
                "activation_source": "manual",
                "acknowledged_high_risk": False,
                "allow_live_execution": False,
                "live_execution_ready": live_ready,
                "live_execution_blockers": blockers,
                "recommended_execution_mode": "SIMULATION",
                "strategy_bias": self._strategy_bias(enabled=False),
                "updated_at": None,
            }

        recommended_mode = "LIVE_TRADING" if row.allow_live_execution and live_ready else "SIMULATION"
        if row.enabled and not row.allow_live_execution:
            recommended_mode = "SIMULATION"

        return {
            "enabled": bool(row.enabled),
            "profile": str(row.profile or "high_volume_directional"),
            "target_amount": float(row.target_amount) if row.target_amount is not None else None,
            "timeframe_days": int(row.timeframe_days) if row.timeframe_days is not None else None,
            "objective_summary": row.objective_summary,
            "activation_source": str(row.activation_source or "manual"),
            "acknowledged_high_risk": bool(row.acknowledged_high_risk),
            "allow_live_execution": bool(row.allow_live_execution),
            "live_execution_ready": live_ready,
            "live_execution_blockers": blockers,
            "recommended_execution_mode": recommended_mode,
            "strategy_bias": self._strategy_bias(enabled=bool(row.enabled)),
            "updated_at": row.updated_at,
        }


options_sprint_service = OptionsSprintService()
