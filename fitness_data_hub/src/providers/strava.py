from typing import Any

from sqlalchemy.orm import Session

from ..strava_client import StravaClient
from .base import FitnessProvider


class StravaProvider(FitnessProvider):
    """Strava implementation of the activity provider contract.

    OAuth and HTTP details still live in StravaClient for now. This adapter is
    the first separation step: the importer no longer depends directly on
    Strava-specific code.
    """

    name = "strava"
    requires_oauth = True
    requires_public_callback = True

    def __init__(self, db: Session):
        self.client = StravaClient(db)

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
