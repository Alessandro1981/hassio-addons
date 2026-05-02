import time
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from .config import settings
from .models import Athlete, OAuthToken

STRAVA_OAUTH_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


def build_redirect_uri() -> str:
    base_url = settings.app_base_url.rstrip("/")
    return f"{base_url}/auth/callback"


class StravaClient:
    def __init__(self, db: Session):
        self.db = db

    def build_authorize_url(self) -> str:
        query = urlencode(
            {
                "client_id": settings.strava_client_id,
                "response_type": "code",
                "redirect_uri": build_redirect_uri(),
                "approval_prompt": "force",
                "scope": settings.strava_scopes,
            }
        )
        return f"{STRAVA_OAUTH_AUTHORIZE_URL}?{query}"

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        response = httpx.post(
            STRAVA_OAUTH_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": build_redirect_uri(),
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        response = httpx.post(
            STRAVA_OAUTH_TOKEN_URL,
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def upsert_token_payload(self, payload: dict[str, Any], accepted_scope: str | None = None) -> Athlete:
        athlete_data = payload["athlete"]
        athlete = self.db.get(Athlete, athlete_data["id"])
        if athlete is None:
            athlete = Athlete(id=athlete_data["id"])
            self.db.add(athlete)

        athlete.username = athlete_data.get("username")
        athlete.firstname = athlete_data.get("firstname")
        athlete.lastname = athlete_data.get("lastname")
        athlete.city = athlete_data.get("city")
        athlete.state = athlete_data.get("state")
        athlete.country = athlete_data.get("country")
        athlete.profile_medium = athlete_data.get("profile_medium")
        athlete.profile = athlete_data.get("profile")

        token = self.db.get(OAuthToken, athlete_data["id"])
        if token is None:
            token = OAuthToken(athlete_id=athlete_data["id"])
            self.db.add(token)

        self._map_token(token, payload, accepted_scope=accepted_scope)

        self.db.commit()
        self.db.refresh(athlete)
        return athlete

    def update_existing_token_payload(self, athlete_id: int, payload: dict[str, Any], accepted_scope: str | None = None) -> None:
        token = self.db.get(OAuthToken, athlete_id)
        if token is None:
            raise ValueError("No token found for athlete")

        self._map_token(token, payload, accepted_scope=accepted_scope or token.scope)
        self.db.commit()

    @staticmethod
    def _map_token(token: OAuthToken, payload: dict[str, Any], accepted_scope: str | None = None) -> None:
        token.token_type = payload["token_type"]
        token.access_token = payload["access_token"]
        token.refresh_token = payload["refresh_token"]
        token.expires_at = payload["expires_at"]
        token.scope = accepted_scope

    def get_primary_athlete(self) -> Athlete | None:
        return self.db.query(Athlete).order_by(Athlete.id.asc()).first()

    def get_valid_access_token(self, athlete_id: int) -> str:
        token = self.db.get(OAuthToken, athlete_id)
        if token is None:
            raise ValueError("No token found for athlete")

        now = int(time.time())
        if token.expires_at <= now + 120:
            refreshed = self.refresh_access_token(token.refresh_token)
            self.update_existing_token_payload(athlete_id, refreshed, accepted_scope=token.scope)
            token = self.db.get(OAuthToken, athlete_id)
            if token is None:
                raise ValueError("Token refresh failed")

        return token.access_token

    def get_logged_in_athlete(self, athlete_id: int) -> dict[str, Any]:
        access_token = self.get_valid_access_token(athlete_id)
        response = httpx.get(
            f"{STRAVA_API_BASE}/athlete",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def list_activities(self, athlete_id: int, page: int = 1, per_page: int = 50, after: int | None = None) -> list[dict[str, Any]]:
        access_token = self.get_valid_access_token(athlete_id)
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after

        response = httpx.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()
