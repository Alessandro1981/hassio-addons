import os
from typing import Any

import httpx


HOME_ASSISTANT_API = "http://supervisor/core/api"


def _notification_id(provider: str) -> str:
    safe_provider = "".join(ch if ch.isalnum() else "_" for ch in provider.lower())
    return f"fitness_data_hub_provider_{safe_provider}"


def describe_exception(error: Exception) -> str:
    """Return a concise symptom suitable for logs and Home Assistant notifications."""
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        body_text = str(body)
        if len(body_text) > 500:
            body_text = body_text[:497] + "..."
        return f"HTTP {response.status_code} {response.reason_phrase}: {body_text}"

    if isinstance(error, httpx.RequestError):
        return f"Connection error: {error}"

    text = str(error).strip() or error.__class__.__name__
    if len(text) > 500:
        text = text[:497] + "..."
    return text


def notify_provider_failure(provider: str, operation: str, error: Exception) -> None:
    """Create/update one persistent Home Assistant notification per provider.

    Notification failures are deliberately best-effort: a problem reporting an
    upstream provider must never hide or replace the original provider error.
    """
    symptom = describe_exception(error)
    print(f"[PROVIDER ERROR] provider={provider} operation={operation} symptom={symptom}")

    token = os.getenv("SUPERVISOR_TOKEN")
    if not token:
        print("[PROVIDER NOTIFY WARNING] SUPERVISOR_TOKEN is not available")
        return

    payload = {
        "title": "Fitness Data Hub - provider problem",
        "message": f"Provider: {provider}\nOperation: {operation}\nSymptom: {symptom}",
        "notification_id": _notification_id(provider),
    }

    try:
        response = httpx.post(
            f"{HOME_ASSISTANT_API}/services/persistent_notification/create",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception as notify_error:
        print(f"[PROVIDER NOTIFY WARNING] Could not create Home Assistant notification: {notify_error}")


def clear_provider_failure(provider: str) -> None:
    """Dismiss the provider notification after a successful connection/sync."""
    token = os.getenv("SUPERVISOR_TOKEN")
    if not token:
        return

    try:
        response = httpx.post(
            f"{HOME_ASSISTANT_API}/services/persistent_notification/dismiss",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"notification_id": _notification_id(provider)},
            timeout=10.0,
        )
        # Dismissing an already absent notification should not affect provider operation.
        if response.status_code >= 400:
            print(f"[PROVIDER NOTIFY WARNING] Could not dismiss notification: HTTP {response.status_code}")
    except Exception as notify_error:
        print(f"[PROVIDER NOTIFY WARNING] Could not dismiss Home Assistant notification: {notify_error}")
