import os

import httpx


HOME_ASSISTANT_API = "http://supervisor/core/api"


def notify_provider_failure(provider: str, operation: str, error: Exception) -> None:
    """Create/update a Home Assistant persistent notification for provider failures.

    Notification failures are deliberately non-fatal: a problem reporting an
    error must never hide or replace the original provider exception.
    """
    symptom = f"{type(error).__name__}: {error}"
    notification_id = f"fitness_data_hub_{provider}_{operation}".replace(" ", "_").lower()
    title = f"Fitness Data Hub - {provider.title()} provider problem"
    message = (
        f"Provider: {provider}\n"
        f"Operation: {operation}\n"
        f"Symptom: {symptom}\n\n"
        "Check the Fitness Data Hub add-on log and provider configuration."
    )

    print(f"[PROVIDER ERROR] provider={provider} operation={operation} symptom={symptom}")

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        print("[NOTIFICATION ERROR] SUPERVISOR_TOKEN is not available")
        return

    try:
        response = httpx.post(
            f"{HOME_ASSISTANT_API}/services/persistent_notification/create",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "message": message,
                "notification_id": notification_id,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception as notification_error:
        print(f"[NOTIFICATION ERROR] provider={provider} operation={operation} error={notification_error}")
