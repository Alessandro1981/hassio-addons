from typing import Any

from sqlalchemy.orm import Session

from ..strava_client import StravaClient
from .base import FitnessProvider


class StravaProvider(FitnessProvider):
    """Strava provider implementation.

    Provider-specific OAuth, token refresh and HTTP behavior remain implemented
    by StravaClient, but the rest of Fitness Data Hub now reaches them only
    through this adapter.
    """

    name = "strava"
    requires_oauth = True
    requires_public_callback = True

    def __init__(self, db: Session):
        self.client = StravaClient(db)

    def build_authorize_url(self) -> str:
        return self.client.build_authorize_url()

    def complete_authorization(self, code: str, scope: str | None = None) -> Any:
        payload = self.client.exchange_code_for_token(code)
        return self.client.upsert_token_payload(payload, accepted_scope=scope)

    def list_activities(
        self,
        athlete_id: int,
        page: int = 1,
        per_page: int = 50,
        after: int | None = None,
    ) -> list[dict[str, Any]]:
        return self.client.list_activities(
            athlete_id=athlete_id,
            page=page,
            per_page=per_page,
            after=after,
        )
