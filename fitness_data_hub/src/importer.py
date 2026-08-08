import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import Activity, SyncState
from .provider_health import clear_provider_failure, notify_provider_failure
from .providers import FitnessProvider, ProviderActivity, get_provider


class ActivityImporter:
    def __init__(self, db: Session, provider: FitnessProvider | None = None):
        self.db = db
        self.provider = provider or get_provider(db)

    def _find_activity(self, external_id: int | str) -> Activity | None:
        return (
            self.db.query(Activity)
            .filter(Activity.provider == self.provider.name, Activity.external_id == str(external_id))
            .first()
        )

    def _get_sync_state(self) -> SyncState | None:
        return self.db.query(SyncState).filter(SyncState.provider == self.provider.name).first()

    def _list_activities(self, operation: str, **kwargs) -> list[ProviderActivity]:
        try:
            return self.provider.list_activities(**kwargs)
        except Exception as error:
            notify_provider_failure(self.provider.name, operation, error)
            raise

    def import_activities(self, athlete_id: int, max_pages: int = 10, per_page: int = 50) -> tuple[int, int]:
        imported = 0
        pages = 0

        for page in range(1, max_pages + 1):
            activities = self._list_activities(
                "full activity import",
                athlete_id=athlete_id,
                page=page,
                per_page=per_page,
            )
            if not activities:
                break

            for item in activities:
                activity = self._find_activity(item.id)
                if activity is None:
                    activity = Activity(provider=self.provider.name, external_id=str(item.id), athlete_id=athlete_id)
                    self.db.add(activity)
                    imported += 1

                self._map_activity(activity, item)

            self.db.commit()
            pages += 1

            if len(activities) < per_page:
                break

        self._update_sync_state_from_db()
        clear_provider_failure(self.provider.name)
        return imported, pages

    def sync_incremental(self, athlete_id: int, per_page: int = 200, overlap_seconds: int = 86400) -> tuple[int, int]:
        sync_state = self._get_sync_state()
        after = self._calculate_after_timestamp(sync_state=sync_state, overlap_seconds=overlap_seconds)

        imported = 0
        pages = 0
        page = 1

        while True:
            activities = self._list_activities(
                "incremental synchronization",
                athlete_id=athlete_id,
                page=page,
                per_page=per_page,
                after=after,
            )
            pages += 1

            if not activities:
                break

            for item in activities:
                activity = self._find_activity(item.id)
                if activity is None:
                    activity = Activity(provider=self.provider.name, external_id=str(item.id), athlete_id=athlete_id)
                    self.db.add(activity)
                    imported += 1

                self._map_activity(activity, item)

            self.db.commit()

            if len(activities) < per_page:
                break

            page += 1

        self._update_sync_state_from_db()
        clear_provider_failure(self.provider.name)
        return imported, pages

    def _calculate_after_timestamp(self, sync_state: SyncState | None, overlap_seconds: int) -> int | None:
        latest_start_date = sync_state.last_activity_start_date if sync_state else None

        if latest_start_date is None:
            latest_activity = (
                self.db.query(Activity)
                .filter(Activity.provider == self.provider.name)
                .order_by(Activity.start_date.desc())
                .first()
            )
            latest_start_date = latest_activity.start_date if latest_activity else None

        latest_epoch = self._parse_datetime_to_epoch(latest_start_date)
        if latest_epoch is None:
            return None

        now_epoch = int(time.time())
        calculated_after = max(0, latest_epoch - overlap_seconds)
        maximum_safe_after = max(0, now_epoch - overlap_seconds)

        if calculated_after > maximum_safe_after:
            print(
                "[SYNC WARNING] Future activity timestamp detected "
                f"(provider={self.provider.name}, latest_start_date={latest_start_date}, calculated_after={calculated_after}). "
                f"Using safe after={maximum_safe_after}."
            )
            return maximum_safe_after

        return calculated_after

    def _update_sync_state_from_db(self) -> None:
        sync_state = self._get_sync_state()
        if sync_state is None:
            sync_state = SyncState(provider=self.provider.name)
            self.db.add(sync_state)

        latest_activity = (
            self.db.query(Activity)
            .filter(Activity.provider == self.provider.name)
            .order_by(Activity.start_date.desc())
            .first()
        )

        sync_state.last_sync_at = int(time.time())
        sync_state.last_activity_start_date = latest_activity.start_date if latest_activity else None
        self.db.commit()

    def get_sync_state(self) -> SyncState | None:
        return self._get_sync_state()

    @staticmethod
    def _parse_datetime_to_epoch(value: str | None) -> int | None:
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
    def _map_activity(activity: Activity, item: ProviderActivity) -> None:
        activity.name = item.name
        activity.sport_type = item.sport_type
        activity.type = item.activity_type
        activity.start_date = item.start_date
        activity.timezone = item.timezone
        activity.distance = item.distance
        activity.moving_time = item.moving_time
        activity.elapsed_time = item.elapsed_time
        activity.total_elevation_gain = item.total_elevation_gain
        activity.average_speed = item.average_speed
        activity.max_speed = item.max_speed
        activity.average_heartrate = item.average_heartrate
        activity.max_heartrate = item.max_heartrate
        activity.average_cadence = item.average_cadence
        activity.average_watts = item.average_watts
        activity.kilojoules = item.kilojoules
        activity.trainer = item.trainer
        activity.commute = item.commute
        activity.manual = item.manual
        activity.private = item.private
        activity.raw_json = json.dumps(item.raw_data, ensure_ascii=False)
