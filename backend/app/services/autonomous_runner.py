from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from app.services.historical_data_service import historical_data_service
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.control_engine import control_engine
from app.services.goal_engine import goal_engine
from app.services.mission_policy_engine import mission_policy_engine
from app.services.portfolio_manager import portfolio_manager
from app.services.regime_detector import regime_detector
from app.services.swarm.execution_bridge import execution_bridge
from app.services.swarm.swarm_manager import swarm_manager


class AutonomousRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._interval_seconds = 300
        self._symbols: list[str] = []
        self._thread: threading.Thread | None = None
        self._run_once_thread: threading.Thread | None = None
        self._run_once_active = False
        self._last_run_at: datetime | None = None
        self._last_error: str | None = None
        self._cycles_run = 0
        self._user_id: str | None = None

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "interval_seconds": self._interval_seconds,
                "symbols": list(self._symbols),
                "last_run_at": self._last_run_at,
                "last_error": self._last_error,
                "cycles_run": self._cycles_run,
            }

    def trigger_run_once(self, *, user_id: str | None = None) -> dict:
        should_start = False
        with self._lock:
            if user_id:
                self._user_id = user_id
            if not self._run_once_active:
                self._run_once_active = True
                should_start = True

        if should_start:
            thread = threading.Thread(target=self._run_once_wrapper, kwargs={"user_id": user_id}, daemon=True)
            with self._lock:
                self._run_once_thread = thread
            thread.start()

        return self.status()

    def _run_once_wrapper(self, user_id: str | None = None) -> None:
        try:
            self.run_once(user_id=user_id)
        finally:
            with self._lock:
                self._run_once_active = False

    def configure(
        self,
        *,
        enabled: bool | None = None,
        interval_seconds: int | None = None,
        symbols: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict:
        with self._lock:
            if user_id:
                self._user_id = user_id
            if interval_seconds is not None:
                self._interval_seconds = max(60, min(interval_seconds, 3600))
            if symbols:
                self._symbols = [s.upper() for s in symbols if s.strip()][:12] or self._symbols
            if enabled is not None:
                self._enabled = enabled
                if enabled and (self._thread is None or not self._thread.is_alive()):
                    self._thread = threading.Thread(target=self._loop, daemon=True)
                    self._thread.start()
        return self.status()

    def _target_symbol_count(self, portfolio: dict) -> int:
        max_trades = max(1, int(portfolio.get("max_concurrent_trades", 8) or 8))
        active_positions = portfolio.get("active_positions") or []
        open_slots = max(1, max_trades - len(active_positions))
        buying_power = float(portfolio.get("available_buying_power", 0.0) or 0.0)

        if buying_power >= 175_000:
            capital_capacity = 8
        elif buying_power >= 125_000:
            capital_capacity = 7
        elif buying_power >= 75_000:
            capital_capacity = 6
        elif buying_power >= 50_000:
            capital_capacity = 5
        elif buying_power >= 20_000:
            capital_capacity = 4
        elif buying_power >= 10_000:
            capital_capacity = 3
        elif buying_power >= 5_000:
            capital_capacity = 2
        else:
            capital_capacity = 1

        return max(1, min(open_slots, capital_capacity))

    def run_once(self, *, user_id: str | None = None) -> dict:
        if execution_bridge.get_mode() == "SIMULATION":
            with self._lock:
                self._last_error = "Autonomous mode requires PAPER_TRADING or LIVE_TRADING execution mode."
            return self.status()

        active_user_id = user_id
        with self._lock:
            if active_user_id is None:
                active_user_id = self._user_id
            elif active_user_id:
                self._user_id = active_user_id

        try:
            portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
            goal_status = goal_engine.status(current_capital=float(portfolio.get("account_balance", 0.0) or 0.0))
            control_status = control_engine.status()
            mission = mission_policy_engine.mission_snapshot(
                goal_status=goal_status,
                drawdown_pct=float(control_status.get("rolling_drawdown_pct", 0.0) or 0.0),
                sprint_active=False,
                dominant_regime="RANGE_BOUND",
                regime_quality={},
            )
            mission_concurrency = int((mission.get("tuning") or {}).get("concurrency_target", 8) or 8)
            portfolio_manager.configure(
                balance=float(portfolio.get("account_balance", 0.0) or 0.0),
                max_concurrent_trades=max(1, mission_concurrency),
            )
            portfolio["max_concurrent_trades"] = max(1, mission_concurrency)
            target_symbol_count = self._target_symbol_count(portfolio)
            latest = master_orchestrator.latest()
            now = datetime.now(tz=timezone.utc)
            if latest is not None and (now - latest.scanned_at).total_seconds() <= 180:
                scan = latest
            else:
                scan_limit = min(max(target_symbol_count * 3, 12), 24)
                scan = master_orchestrator.scan(limit=scan_limit)

            candidates = [c for c in scan.candidates if c.action_label in {"EXECUTE", "SIMULATE"}][:target_symbol_count]
            if not candidates:
                # Fall back to top crypto watches so the swarm keeps exploring and adapting.
                candidates = [
                    c
                    for c in scan.candidates
                    if c.asset_class == "crypto" and c.action_label == "MONITOR" and c.composite_score >= 0.35
                ][:target_symbol_count]
            selected_symbols = [c.symbol for c in candidates]

            if not selected_symbols:
                with self._lock:
                    self._last_error = "No eligible symbols from latest scan."
                return self.status()

            with self._lock:
                self._symbols = selected_symbols

            for symbol in selected_symbols:
                end = datetime.now(tz=timezone.utc)
                start = end - timedelta(days=120)
                df = historical_data_service.load_historical_data(
                    symbol=symbol,
                    timeframe="1d",
                    start_date=start,
                    end_date=end,
                )
                close_prices = [float(v) for v in df["close"].tolist() if float(v) > 0]
                volumes = [float(v) for v in df["volume"].tolist() if float(v) > 0]
                if len(close_prices) < 30 or len(volumes) < 30:
                    continue
                regime = regime_detector.detect_from_dataframe(df).regime
                swarm_manager.run_cycle(
                    symbol=symbol,
                    close_prices=close_prices,
                    volumes=volumes,
                    regime=regime,
                    regime_confidence=0.68,
                    default_qty=1.0,
                    user_id=active_user_id,
                )
            with self._lock:
                self._last_run_at = datetime.now(tz=timezone.utc)
                self._cycles_run += 1
                self._last_error = None
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
        return self.status()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._enabled:
                    break
                interval = self._interval_seconds
            self.run_once()
            time.sleep(interval)

autonomous_runner = AutonomousRunner()