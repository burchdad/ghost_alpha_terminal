from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timezone

from app.services.swarm.execution_bridge import execution_bridge
from app.services.swarm.swarm_manager import swarm_manager


class AutonomousRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._interval_seconds = 300
        self._symbols = ["AAPL", "TSLA", "NVDA", "SPY"]
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
        if execution_bridge.get_mode() != "PAPER_TRADING":
            with self._lock:
                self._last_error = "Autonomous mode requires PAPER_TRADING execution mode."
            return self.status()

        try:
            for symbol in self.status()["symbols"]:
                close_prices, volumes, regime = self._mock_market(symbol)
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

    def _mock_market(self, symbol: str) -> tuple[list[float], list[float], str]:
        seeds = {"AAPL": 185.0, "TSLA": 170.0, "NVDA": 905.0, "SPY": 510.0}
        base = seeds.get(symbol.upper(), 100.0)
        minute = int(time.time() // 60)
        prices: list[float] = []
        volumes: list[float] = []
        for idx in range(30):
            drift = math.sin((minute + idx) / 3.0) * (base * 0.0025)
            oscillation = math.cos((minute + idx) / 5.0) * (base * 0.0015)
            prices.append(round(base + drift + oscillation + idx * 0.03, 4))
            volumes.append(1_000_000 + ((minute + idx) % 15) * 25_000)
        regime = ["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"][minute % 3]
        return prices, volumes, regime


autonomous_runner = AutonomousRunner()