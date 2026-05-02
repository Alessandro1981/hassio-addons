import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import Activity, SyncState
from .strava_client import StravaClient


class ActivityImporter:
    def __init__(self, db: Session):
        self.db = db
        self.client = StravaClient(db)

    def import_activities(self, athlete_id: int, max_pages: int = 10, per_page: int = 50) -> tuple[int, int]:
        imported = 0
        pages = 0

        for page in range(1, max_pages + 1):
            activities = self.client.list_activities(athlete_id=athlete_id, page=page, per_page=per_page)
            if not activities:
                break

            for item in activities:
                activity = self.db.get(Activity, item["id"])
                if activity is None:
                    activity = Activity(id=item["id"], athlete_id=athlete_id)
                    self.db.add(activity)
                    imported += 1

                self._map_activity(activity, item)

            self.db.commit()
            pages += 1

            if len(activities) < per_page:
                break

        self._update_sync_state_from_db()
        return imported, pages

    def sync_incremental(self, athlete_id: int, per_page: int = 200, overlap_seconds: int = 86400) -> tuple[int, int]:
        """
        Import only activities newer than the latest known activity.

        The overlap window intentionally re-reads the last 24h by default.
        This makes the sync safer if Strava receives a delayed upload or if
        an existing activity is edited after the first import.
        """
        sync_state = self.db.get(SyncState, 1)
        after = self._calculate_after_timestamp(sync_state=sync_state, overlap_seconds=overlap_seconds)

        imported = 0
        pages = 0
        page = 1

        while True:
            activities = self.client.list_activities(
                athlete_id=athlete_id,
                page=page,
                per_page=per_page,
                after=after,
            )
            pages += 1

            if not activities:
                break

            for item in activities:
                activity = self.db.get(Activity, item["id"])
                if activity is None:
                    activity = Activity(id=item["id"], athlete_id=athlete_id)
                    self.db.add(activity)
                    imported += 1

                self._map_activity(activity, item)

            self.db.commit()

            if len(activities) < per_page:
                break

            page += 1

        self._update_sync_state_from_db()
        return imported, pages

    def _calculate_after_timestamp(self, sync_state: SyncState | None, overlap_seconds: int) -> int | None:
        latest_start_date = sync_state.last_activity_start_date if sync_state else None

        if latest_start_date is None:
            latest_activity = self.db.query(Activity).order_by(Activity.start_date.desc()).first()
            latest_start_date = latest_activity.start_date if latest_activity else None

        latest_epoch = self._parse_strava_datetime_to_epoch(latest_start_date)
        if latest_epoch is None:
            return None

        return max(0, latest_epoch - overlap_seconds)

    def _update_sync_state_from_db(self) -> None:
        sync_state = self.db.get(SyncState, 1)
        if sync_state is None:
            sync_state = SyncState(id=1)
            self.db.add(sync_state)

        latest_activity = self.db.query(Activity).order_by(Activity.start_date.desc()).first()

        sync_state.last_sync_at = int(time.time())
        sync_state.last_activity_start_date = latest_activity.start_date if latest_activity else None

        self.db.commit()

    @staticmethod
    def _parse_strava_datetime_to_epoch(value: str | None) -> int | None:
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return None

    @staticmethod
    def _map_activity(activity: Activity, item: dict[str, Any]) -> None:
        activity.name = item.get("name")
        activity.sport_type = item.get("sport_type")
        activity.type = item.get("type")
        activity.start_date = item.get("start_date")
        activity.timezone = item.get("timezone")
        activity.distance = item.get("distance")
        activity.moving_time = item.get("moving_time")
        activity.elapsed_time = item.get("elapsed_time")
        activity.total_elevation_gain = item.get("total_elevation_gain")
        activity.average_speed = item.get("average_speed")
        activity.max_speed = item.get("max_speed")
        activity.average_heartrate = item.get("average_heartrate")
        activity.max_heartrate = item.get("max_heartrate")
        activity.average_cadence = item.get("average_cadence")
        activity.average_watts = item.get("average_watts")
        activity.kilojoules = item.get("kilojoules")
        activity.trainer = item.get("trainer")
        activity.commute = item.get("commute")
        activity.manual = item.get("manual")
        activity.private = item.get("private")
        activity.raw_json = json.dumps(item, ensure_ascii=False)
