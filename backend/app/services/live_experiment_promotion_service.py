from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.db.models import LiveExperimentModeState
from app.db.session import get_session


VARIANT_CONFIG = {
    "evolution_on_compounding_on": {"enable_evolution": True, "enable_compounding": True},
    "evolution_off_compounding_on": {"enable_evolution": False, "enable_compounding": True},
    "evolution_on_compounding_off": {"enable_evolution": True, "enable_compounding": False},
    "evolution_off_compounding_off": {"enable_evolution": False, "enable_compounding": False},
}


class LiveExperimentPromotionService:
    """Stores current live variant promoted by controlled experiments."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._variant = "evolution_on_compounding_on"
        self._source = "default"
        self._promoted_at: datetime | None = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                with get_session() as session:
                    row = session.query(LiveExperimentModeState).filter(LiveExperimentModeState.scope == "global").first()
                    if row is not None:
                        self._variant = str(row.variant or self._variant).strip().lower()
                        self._source = str(row.source or self._source)
                        self._promoted_at = self._as_utc(row.promoted_at)
            except Exception:
                # Keep safe in-memory defaults if DB is unavailable.
                pass
            self._loaded = True

    @staticmethod
    def _as_utc(ts: datetime | None) -> datetime | None:
        if ts is None:
            return None
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    def _persist_state(self) -> None:
        try:
            with get_session() as session:
                row = session.query(LiveExperimentModeState).filter(LiveExperimentModeState.scope == "global").first()
                if row is None:
                    row = LiveExperimentModeState(scope="global")
                    session.add(row)
                row.variant = self._variant
                row.source = self._source
                row.promoted_at = self._promoted_at
                row.updated_at = datetime.now(tz=timezone.utc)
        except Exception:
            # Runtime should keep moving even if persistence temporarily fails.
            return

    def status(self) -> dict:
        self._ensure_loaded()
        with self._lock:
            variant = self._variant
            config = dict(VARIANT_CONFIG.get(variant, VARIANT_CONFIG["evolution_on_compounding_on"]))
            return {
                "variant": variant,
                "source": self._source,
                "promoted_at": self._promoted_at.isoformat() if self._promoted_at else None,
                **config,
            }

    def promote(self, *, variant: str, source: str) -> dict:
        self._ensure_loaded()
        name = str(variant or "").strip().lower()
        if name not in VARIANT_CONFIG:
            return {"changed": False, **self.status()}

        with self._lock:
            changed = self._variant != name
            self._variant = name
            self._source = str(source or "experiment")
            self._promoted_at = datetime.now(tz=timezone.utc)

        self._persist_state()

        return {"changed": changed, **self.status()}

    def reset_to_default(self, *, source: str = "admin_reset") -> dict:
        self._ensure_loaded()
        with self._lock:
            changed = self._variant != "evolution_on_compounding_on" or self._source != "default" or self._promoted_at is not None
            self._variant = "evolution_on_compounding_on"
            self._source = str(source or "admin_reset")
            self._promoted_at = None

        self._persist_state()
        return {"changed": changed, **self.status()}


live_experiment_promotion_service = LiveExperimentPromotionService()
