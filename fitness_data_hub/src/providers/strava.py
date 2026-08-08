from typing import Any

from sqlalchemy.orm import Session

from ..strava_client import StravaClient
from .base import FitnessProvider
from .models import ProviderActivity, ProviderAthlete


class StravaProvider(FitnessProvider):
    """Strava provider implementation and payload normalization boundary."""

    name = "strava"
    requires_oauth = True
    requires_public_callback = True

    def __init__(self, db: Session):
        self.client = StravaClient(db)

    def build_authorize_url(self) -> str:
        return self.client.build_authorize_url()

    def complete_authorization(self, code: str, scope: str | None = None) -> ProviderAthlete:
        payload = self.client.exchange_code_for_token(code)
        athlete = self.client.upsert_token_payload(payload, accepted_scope=scope)
        athlete_data = payload.get("athlete", {})
        return ProviderAthlete(
            id=athlete.id,
            username=athlete.username,
            firstname=athlete.firstname,
            lastname=athlete.lastname,
            city=athlete.city,
            state=athlete.state,
            country=athlete.country,
            profile_medium=athlete.profile_medium,
            profile=athlete.profile,
            raw_data=athlete_data,
        )

    def list_activities(
        self,
        athlete_id: int,
        page: int = 1,
        per_page: int = 50,
        after: int | None = None,
    ) -> list[ProviderActivity]:
        raw_activities = self.client.list_activities(
            athlete_id=athlete_id,
            page=page,
            per_page=per_page,
            after=after,
        )
        return [self._normalize_activity(item) for item in raw_activities]

    @staticmethod
    def _normalize_activity(item: dict[str, Any]) -> ProviderActivity:
        return ProviderActivity(
            id=item["id"],
            name=item.get("name"),
            sport_type=item.get("sport_type"),
            activity_type=item.get("type"),
            start_date=item.get("start_date"),
            timezone=item.get("timezone"),
            distance=item.get("distance"),
            moving_time=item.get("moving_time"),
            elapsed_time=item.get("elapsed_time"),
            total_elevation_gain=item.get("total_elevation_gain"),
            average_speed=item.get("average_speed"),
            max_speed=item.get("max_speed"),
            average_heartrate=item.get("average_heartrate"),
            max_heartrate=item.get("max_heartrate"),
            average_cadence=item.get("average_cadence"),
            average_watts=item.get("average_watts"),
            kilojoules=item.get("kilojoules"),
            trainer=item.get("trainer"),
            commute=item.get("commute"),
            manual=item.get("manual"),
            private=item.get("private"),
            raw_data=item,
        )
