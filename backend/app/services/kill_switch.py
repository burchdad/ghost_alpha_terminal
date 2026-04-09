from __future__ import annotations

from threading import Lock


class KillSwitch:
    def __init__(self) -> None:
        self._lock = Lock()
        self._trading_enabled = True

    def is_enabled(self) -> bool:
        with self._lock:
            return self._trading_enabled

    def set_enabled(self, enabled: bool) -> bool:
        with self._lock:
            self._trading_enabled = enabled
            return self._trading_enabled


kill_switch = KillSwitch()
