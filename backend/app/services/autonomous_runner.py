from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from app.services.historical_data_service import historical_data_service
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
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
        self._last_run_at: datetime | None = None
        self._last_error: str | None = None
        self._cycles_run = 0

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

    def configure(self, *, enabled: bool | None = None, interval_seconds: int | None = None, symbols: list[str] | None = None) -> dict:
        with self._lock:
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

    def run_once(self) -> dict:
        if execution_bridge.get_mode() == "SIMULATION":
            with self._lock:
                self._last_error = "Autonomous mode requires PAPER_TRADING or LIVE_TRADING execution mode."
            return self.status()

        try:
            portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
            scan = master_orchestrator.scan(limit=8)
            candidates = [c for c in scan.candidates if c.action_label in {"EXECUTE", "SIMULATE"}][:4]
            if not candidates:
                # Fall back to top crypto watches so the swarm keeps exploring and adapting.
                candidates = [
                    c
                    for c in scan.candidates
                    if c.asset_class == "crypto" and c.action_label == "MONITOR" and c.composite_score >= 0.35
                ][:2]
            selected_symbols = [c.symbol for c in candidates]
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