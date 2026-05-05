"""Client helpers for Home Assistant REST API notifications."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any
from urllib.parse import urlsplit


@dataclass(slots=True)
class HomeAssistantClient:
    """Minimal REST client for sending notifications."""

    base_url: str
    token: str
    notify_service: str
    timeout_seconds: int = 15

    def is_configured(self) -> bool:
        return bool(self.base_url and self.notify_service and self._candidate_tokens())

    def send_notification(self, title: str, message: str, data: dict[str, Any] | None = None) -> None:
        if not self.is_configured():
            raise RuntimeError("Home Assistant client is not fully configured.")
        import requests

        domain, service = self._split_service(self.notify_service)
        url = f"{self.base_url}/api/services/{domain}/{service}"
        payload: dict[str, Any] = {"title": title, "message": message}
        if data:
            payload["data"] = data

        last_response: requests.Response | None = None
        for token_source, token in self._candidate_tokens():
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
            last_response = response
            if response.status_code != 401:
                response.raise_for_status()
                return
            # Re-read tokens on every send. If a stale manual token is configured, try the next candidate.
            continue

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("No valid Home Assistant token available.")

    def _candidate_tokens(self) -> list[tuple[str, str]]:
        """Return auth tokens in preferred order.

        For add-ons calling http://supervisor/core, the Supervisor injects SUPERVISOR_TOKEN
        when homeassistant_api is enabled. That token should be preferred over manually
        configured long-lived tokens, because the manual token may be stale.
        """
        configured_token = self.token.strip()
        supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
        candidates: list[tuple[str, str]] = []
        if self._uses_supervisor_core_url() and supervisor_token:
            candidates.append(("SUPERVISOR_TOKEN", supervisor_token))
        if configured_token:
            candidates.append(("configured_token", configured_token))
        if not self._uses_supervisor_core_url() and supervisor_token:
            candidates.append(("SUPERVISOR_TOKEN", supervisor_token))

        deduped: list[tuple[str, str]] = []
        seen: set[str] = set()
        for source, token in candidates:
            if token in seen:
                continue
            seen.add(token)
            deduped.append((source, token))
        return deduped

    def _uses_supervisor_core_url(self) -> bool:
        parsed = urlsplit(self.base_url.strip())
        return parsed.hostname == "supervisor" and parsed.path.rstrip("/") == "/core"

    def _resolve_token(self) -> str:
        candidates = self._candidate_tokens()
        if candidates:
            return candidates[0][1]
        return ""

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
