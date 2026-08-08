from sqlalchemy.orm import Session

from ..config import settings
from .base import FitnessProvider
from .strava import StravaProvider


def get_provider(db: Session) -> FitnessProvider:
    provider_name = (settings.provider or "strava").strip().lower()

    if provider_name == "strava":
        return StravaProvider(db)

    raise ValueError(f"Unsupported fitness provider: {provider_name}")
