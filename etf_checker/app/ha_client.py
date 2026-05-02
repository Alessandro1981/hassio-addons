"""Client helpers for Home Assistant REST API notifications."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any


@dataclass(slots=True)
class HomeAssistantClient:
    """Minimal REST client for sending notifications."""

    base_url: str
    token: str
    notify_service: str
    timeout_seconds: int = 15

    def is_configured(self) -> bool:
        return bool(self.base_url and self.notify_service and self._resolve_token())

    def send_notification(self, title: str, message: str, data: dict[str, Any] | None = None) -> None:
        if not self.is_configured():
            raise RuntimeError("Home Assistant client is not fully configured.")
        import requests

        token = self._resolve_token()
        if not token:
            raise RuntimeError("Home Assistant token is missing. Configure homeassistant_token or SUPERVISOR_TOKEN.")

        domain, service = self._split_service(self.notify_service)
        url = f"{self.base_url}/api/services/{domain}/{service}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"title": title, "message": message}
        if data:
            payload["data"] = data
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        response.raise_for_status()

    def _resolve_token(self) -> str:
        configured_token = self.token.strip()
        if configured_token:
            return configured_token
        return os.environ.get("SUPERVISOR_TOKEN", "").strip()

    @staticmethod
    def _split_service(service: str) -> tuple[str, str]:
        if "/" in service:
            domain, svc = service.split("/", maxsplit=1)
            return domain, svc
        if "." in service:
            domain, svc = service.split(".", maxsplit=1)
            return domain, svc
        raise ValueError(
            "Notify service must look like 'notify/mobile_app_phone' or 'notify.mobile_app_phone'."
        )
