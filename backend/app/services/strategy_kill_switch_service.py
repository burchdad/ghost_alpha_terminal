from __future__ import annotations

import threading


class StrategyKillSwitchService:
    """Manual operator overrides for strategy kill-switch state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._force_enabled: set[str] = set()

    @staticmethod
    def _normalize(strategy: str) -> str:
        return str(strategy or "").strip().upper()

    def set_force_enabled(self, strategy: str, enabled: bool = True) -> dict:
        name = self._normalize(strategy)
        if not name:
            return {"strategy": "", "force_enabled": False, "changed": False}

        with self._lock:
            was_enabled = name in self._force_enabled
            if enabled:
                self._force_enabled.add(name)
            else:
                self._force_enabled.discard(name)
            now_enabled = name in self._force_enabled

        return {
            "strategy": name,
            "force_enabled": now_enabled,
            "changed": was_enabled != now_enabled,
        }

    def clear_force_enabled(self, strategy: str) -> dict:
        return self.set_force_enabled(strategy, enabled=False)

    def list_force_enabled(self) -> list[str]:
        with self._lock:
            return sorted(self._force_enabled)


strategy_kill_switch_service = StrategyKillSwitchService()
