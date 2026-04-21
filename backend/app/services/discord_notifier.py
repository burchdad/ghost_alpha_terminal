from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class DiscordNotifierService:
    def _is_configured(self) -> bool:
        webhook = str(settings.discord_webhook_url or "").strip()
        return bool(settings.discord_alerts_enabled and webhook)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": bool(settings.discord_alerts_enabled),
            "configured": self._is_configured(),
            "webhook_present": bool(str(settings.discord_webhook_url or "").strip()),
            "username": str(settings.discord_username or "Ghost Alpha Ops"),
        }

    def send_message(
        self,
        *,
        title: str,
        message: str,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Post a structured alert message to Discord webhook.

        Returns False when integration is disabled/unconfigured or when delivery fails.
        """
        if not self._is_configured():
            return False

        severity_normalized = severity.strip().lower()
        color_map = {
            "info": 0x3B82F6,
            "warning": 0xF59E0B,
            "critical": 0xEF4444,
            "success": 0x10B981,
        }
        embed_color = color_map.get(severity_normalized, color_map["info"])

        fields = []
        if context:
            for key, value in context.items():
                fields.append(
                    {
                        "name": str(key).replace("_", " ").title(),
                        "value": str(value),
                        "inline": True,
                    }
                )

        payload: dict[str, Any] = {
            "username": str(settings.discord_username or "Ghost Alpha Ops"),
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": embed_color,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "fields": fields[:10],
                }
            ],
        }

        try:
            with httpx.Client(timeout=max(1.0, float(settings.discord_timeout_seconds or 5.0))) as client:
                response = client.post(str(settings.discord_webhook_url).strip(), json=payload)
                if response.status_code >= 400:
                    logger.error(
                        "discord_webhook_post_failed status=%s body=%s",
                        response.status_code,
                        response.text[:400],
                    )
                    return False
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("discord_webhook_exception error=%s", exc)
            return False


# Singleton service
discord_notifier = DiscordNotifierService()
