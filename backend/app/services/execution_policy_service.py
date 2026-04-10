from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.models import ExecutionPolicyState
from app.db.session import get_session


@dataclass
class ExecutionPolicy:
    live_only_during_market_hours: bool
    market_timezone: str
    market_open_hhmm: str
    market_close_hhmm: str


class ExecutionPolicyService:
    def _get_or_create_row(self) -> ExecutionPolicyState:
        with get_session() as session:
            row = session.execute(
                select(ExecutionPolicyState).where(ExecutionPolicyState.scope == "global")
            ).scalar_one_or_none()
            if row is None:
                row = ExecutionPolicyState(scope="global")
                session.add(row)
                session.flush()
            return row

    def status(self) -> dict:
        row = self._get_or_create_row()
        return {
            "live_only_during_market_hours": bool(row.live_only_during_market_hours),
            "market_timezone": str(row.market_timezone),
            "market_open_hhmm": str(row.market_open_hhmm),
            "market_close_hhmm": str(row.market_close_hhmm),
            "updated_at": row.updated_at,
        }

    def configure(
        self,
        *,
        live_only_during_market_hours: bool | None = None,
        market_timezone: str | None = None,
        market_open_hhmm: str | None = None,
        market_close_hhmm: str | None = None,
    ) -> dict:
        with get_session() as session:
            row = session.execute(
                select(ExecutionPolicyState).where(ExecutionPolicyState.scope == "global")
            ).scalar_one_or_none()
            if row is None:
                row = ExecutionPolicyState(scope="global")
                session.add(row)
                session.flush()

            if live_only_during_market_hours is not None:
                row.live_only_during_market_hours = bool(live_only_during_market_hours)
            if market_timezone is not None and market_timezone.strip():
                row.market_timezone = market_timezone.strip()
            if market_open_hhmm is not None and market_open_hhmm.strip():
                row.market_open_hhmm = market_open_hhmm.strip()
            if market_close_hhmm is not None and market_close_hhmm.strip():
                row.market_close_hhmm = market_close_hhmm.strip()

            row.updated_at = datetime.now(tz=timezone.utc)
            session.add(row)

        return self.status()

    def _parse_hhmm(self, value: str) -> time:
        text = (value or "").strip()
        if ":" not in text:
            raise ValueError("Invalid HH:MM format")
        hh, mm = text.split(":", 1)
        return time(hour=max(0, min(int(hh), 23)), minute=max(0, min(int(mm), 59)))

    def is_live_execution_allowed_now(self) -> tuple[bool, str | None]:
        policy = self.status()
        if not policy.get("live_only_during_market_hours", False):
            return True, None

        tz_name = str(policy.get("market_timezone") or "America/New_York")
        zone = ZoneInfo(tz_name)
        now_local = datetime.now(tz=timezone.utc).astimezone(zone)

        # Monday=0 ... Sunday=6
        if now_local.weekday() >= 5:
            return False, f"Live execution blocked by policy: outside market hours ({tz_name})."

        open_at = self._parse_hhmm(str(policy.get("market_open_hhmm") or "09:30"))
        close_at = self._parse_hhmm(str(policy.get("market_close_hhmm") or "16:00"))
        now_t = now_local.time().replace(second=0, microsecond=0)

        if open_at <= now_t <= close_at:
            return True, None

        return False, (
            "Live execution blocked by policy: outside configured market hours "
            f"({policy.get('market_open_hhmm')}-{policy.get('market_close_hhmm')} {tz_name})."
        )


execution_policy_service = ExecutionPolicyService()
