from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firstname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lastname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_medium: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    athlete_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_type: Mapped[str] = mapped_column(String(50))
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[int] = mapped_column(Integer)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sport_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    moving_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_elevation_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_heartrate: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_heartrate: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_cadence: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_watts: Mapped[float | None] = mapped_column(Float, nullable=True)
    kilojoules: Mapped[float | None] = mapped_column(Float, nullable=True)
    trainer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    commute: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    manual: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    private: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sync_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_activity_start_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
