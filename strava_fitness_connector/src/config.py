import json
import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


HASSIO_OPTIONS_PATH = Path("/data/options.json")


def running_in_hassio() -> bool:
    return HASSIO_OPTIONS_PATH.exists()


def load_hassio_options() -> dict[str, Any]:
    if not running_in_hassio():
        return {}

    with HASSIO_OPTIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


class Settings(BaseSettings):
    app_name: str = "Strava Fitness Connector"
    app_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./data/strava_phase1.db"
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/auth/callback"
    strava_scopes: str = "read,activity:read_all,profile:read_all"
    sync_interval_seconds: int = 3600
    sync_enabled: bool = True
    is_hassio: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def build_settings() -> Settings:
    settings = Settings()
    options = load_hassio_options()

    if not options:
        return settings

    settings.is_hassio = True
    settings.database_url = "sqlite:////data/strava_phase1.db"
    settings.app_base_url = options.get("app_base_url") or settings.app_base_url
    settings.strava_client_id = str(options.get("strava_client_id") or "")
    settings.strava_client_secret = str(options.get("strava_client_secret") or "")
    settings.strava_redirect_uri = options.get("strava_redirect_uri") or settings.strava_redirect_uri
    settings.strava_scopes = options.get("strava_scopes") or settings.strava_scopes
    settings.sync_enabled = bool(options.get("sync_enabled", settings.sync_enabled))
    settings.sync_interval_seconds = int(options.get("sync_interval_seconds", settings.sync_interval_seconds))

    os.makedirs("/data", exist_ok=True)

    return settings


settings = build_settings()
