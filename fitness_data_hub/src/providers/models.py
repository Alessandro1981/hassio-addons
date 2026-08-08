from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProviderActivity:
    """Provider-independent activity payload used by the core importer."""

    id: int
    name: str | None = None
    sport_type: str | None = None
    activity_type: str | None = None
    start_date: str | None = None
    timezone: str | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    average_cadence: float | None = None
    average_watts: float | None = None
    kilojoules: float | None = None
    trainer: bool | None = None
    commute: bool | None = None
    manual: bool | None = None
    private: bool | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderAthlete:
    """Provider-independent athlete identity returned after authentication."""

    id: int
    username: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    profile_medium: str | None = None
    profile: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
