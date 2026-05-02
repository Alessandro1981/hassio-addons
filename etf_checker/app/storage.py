"""Persistence helpers for monitor state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STATE_PATH = Path("/data/monitor_state.json")


@dataclass(slots=True)
class PriceSnapshot:
    price: float
    read_at: str


@dataclass(slots=True)
class DailyOpenPrice:
    price: float
    date: str
    read_at: str


@dataclass(slots=True)
class MonitorState:
    baselines: dict[str, float] = field(default_factory=dict)
    last_baseline_update: str | None = None
    last_prices: dict[str, PriceSnapshot] = field(default_factory=dict)
    daily_open_prices: dict[str, DailyOpenPrice] = field(default_factory=dict)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _clean_float_dict(raw: Any) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    if isinstance(raw, dict):
        for symbol, value in raw.items():
            try:
                cleaned[str(symbol).upper()] = float(value)
            except (TypeError, ValueError):
                continue
    return cleaned


def _load_last_prices(raw: Any) -> dict[str, PriceSnapshot]:
    snapshots: dict[str, PriceSnapshot] = {}
    if not isinstance(raw, dict):
        return snapshots
    for symbol, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        try:
            price = float(payload.get("price"))
        except (TypeError, ValueError):
            continue
        read_at = payload.get("read_at")
        if not isinstance(read_at, str):
            continue
        snapshots[str(symbol).upper()] = PriceSnapshot(price=price, read_at=read_at)
    return snapshots


def _load_daily_open_prices(raw: Any) -> dict[str, DailyOpenPrice]:
    snapshots: dict[str, DailyOpenPrice] = {}
    if not isinstance(raw, dict):
        return snapshots
    for symbol, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        try:
            price = float(payload.get("price"))
        except (TypeError, ValueError):
            continue
        date = payload.get("date")
        read_at = payload.get("read_at")
        if not isinstance(date, str) or not isinstance(read_at, str):
            continue
        snapshots[str(symbol).upper()] = DailyOpenPrice(price=price, date=date, read_at=read_at)
    return snapshots


def load_state() -> MonitorState:
    raw = _load_json(STATE_PATH)
    baselines = _clean_float_dict(raw.get("baselines", {}))
    last_baseline_update = raw.get("last_baseline_update")
    if not isinstance(last_baseline_update, str):
        last_baseline_update = None
    return MonitorState(
        baselines=baselines,
        last_baseline_update=last_baseline_update,
        last_prices=_load_last_prices(raw.get("last_prices", {})),
        daily_open_prices=_load_daily_open_prices(raw.get("daily_open_prices", {})),
    )


def save_state(state: MonitorState) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "baselines": state.baselines,
        "last_baseline_update": state.last_baseline_update,
        "last_prices": {
            symbol: {"price": snapshot.price, "read_at": snapshot.read_at}
            for symbol, snapshot in state.last_prices.items()
        },
        "daily_open_prices": {
            symbol: {
                "price": snapshot.price,
                "date": snapshot.date,
                "read_at": snapshot.read_at,
            }
            for symbol, snapshot in state.daily_open_prices.items()
        },
    }
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
