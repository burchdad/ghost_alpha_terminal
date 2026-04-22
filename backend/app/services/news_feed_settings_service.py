from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock

from sqlalchemy import select

from app.core.config import settings
from app.db.models import NewsFeedSettingsState
from app.db.session import get_session

_STATUS_CACHE_TTL_SECONDS = 5


class NewsFeedSettingsService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._status_cache: dict | None = None
        self._status_cache_at: datetime | None = None
    def _default_enabled_sources(self) -> list[str]:
        return [item.strip().upper() for item in settings.news_public_feed_sources.split(",") if item.strip()]

    def _default_source_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        for token in settings.news_source_weights.split(","):
            part = token.strip()
            if not part or "=" not in part:
                continue
            source, raw_value = part.split("=", 1)
            try:
                weights[source.strip().upper()] = max(0.1, min(float(raw_value.strip()), 10.0))
            except ValueError:
                continue
        return weights

    def _normalize_sources(self, values: list[str] | None) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for value in values or []:
            normalized = str(value).strip().upper()
            if not normalized or normalized in seen:
                continue
            ordered.append(normalized)
            seen.add(normalized)
        return ordered

    def _normalize_weights(self, values: dict[str, float] | None) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for source, raw_value in (values or {}).items():
            key = str(source).strip().upper()
            if not key:
                continue
            try:
                weight = float(raw_value)
            except (TypeError, ValueError):
                continue
            normalized[key] = max(0.1, min(weight, 10.0))
        return normalized

    def _get_or_create_row(self) -> NewsFeedSettingsState:
        with get_session() as session:
            row = session.execute(
                select(NewsFeedSettingsState).where(NewsFeedSettingsState.scope == "global")
            ).scalar_one_or_none()
            if row is None:
                row = NewsFeedSettingsState(scope="global")
                session.add(row)
                session.flush()
            return row

    def status(self) -> dict:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            if (
                self._status_cache is not None
                and self._status_cache_at is not None
                and (now - self._status_cache_at).total_seconds() < _STATUS_CACHE_TTL_SECONDS
            ):
                return dict(self._status_cache)

        row = self._get_or_create_row()
        enabled_sources = self._normalize_sources((row.enabled_sources_csv or "").split(","))
        source_weights = self._default_source_weights()
        try:
            parsed_weights = json.loads(row.source_weights_json or "{}")
        except json.JSONDecodeError:
            parsed_weights = {}
        source_weights.update(self._normalize_weights(parsed_weights if isinstance(parsed_weights, dict) else {}))
        result = {
            "enabled_sources": enabled_sources or self._default_enabled_sources(),
            "source_weights": source_weights,
            "refresh_seconds": int(settings.news_feed_refresh_seconds or 45),
            "updated_at": row.updated_at,
        }
        with self._lock:
            self._status_cache = result
            self._status_cache_at = now
        return dict(result)

    def configure(self, *, enabled_sources: list[str], source_weights: dict[str, float]) -> dict:
        normalized_sources = self._normalize_sources(enabled_sources)
        normalized_weights = self._normalize_weights(source_weights)
        with self._lock:
            self._status_cache = None
            self._status_cache_at = None
        with get_session() as session:
            row = session.execute(
                select(NewsFeedSettingsState).where(NewsFeedSettingsState.scope == "global")
            ).scalar_one_or_none()
            if row is None:
                row = NewsFeedSettingsState(scope="global")
                session.add(row)
                session.flush()

            row.enabled_sources_csv = ",".join(normalized_sources)
            row.source_weights_json = json.dumps(normalized_weights, sort_keys=True)
            row.updated_at = datetime.now(tz=timezone.utc)
            session.add(row)

        return self.status()


news_feed_settings_service = NewsFeedSettingsService()