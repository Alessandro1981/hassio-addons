"""Configuration loading for the ETF Checker add-on."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OPTIONS_PATH = Path("/data/options.json")
UI_CONFIG_PATH = Path("/data/ui_config.json")
DEFAULT_NOTIFY_SERVICE = "notify/mobile_app_mio_telefono"


@dataclass(slots=True)
class AddonOptions:
    """Supervisor-provided options."""

    homeassistant_url: str = "http://supervisor/core"
    homeassistant_token: str = ""
    notify_service: str = DEFAULT_NOTIFY_SERVICE
    alpha_vantage_api_key: str = ""
    finnhub_api_key: str = ""
    poll_interval_seconds: int = 900
    default_threshold_percent: float = 2.0
    log_level: str = "INFO"


@dataclass(slots=True)
class UiConfig:
    """User-defined configuration stored via the add-on UI."""

    etf_symbols: list[str]
    threshold_percent: float
    market_open_retry_seconds: int
    notify_services: list[str]


@dataclass(slots=True)
class EffectiveConfig:
    """Merged configuration used by the monitor."""

    options: AddonOptions
    ui: UiConfig


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_notify_service(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("notify."):
        return cleaned.replace(".", "/", 1)
    return cleaned


def parse_notify_services(raw: Any, fallback: str) -> list[str]:
    values: list[str] = []
    if isinstance(raw, list):
        values = [str(item) for item in raw]
    elif isinstance(raw, str) and raw.strip():
        values = [item.strip() for item in raw.replace("\n", ",").split(",")]
    elif fallback:
        values = [fallback]

    services: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_notify_service(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        services.append(normalized)
    return services


def load_addon_options() -> AddonOptions:
    raw = _load_json(OPTIONS_PATH)
    return AddonOptions(
        homeassistant_url=str(raw.get("homeassistant_url", AddonOptions.homeassistant_url)).strip(),
        homeassistant_token=str(raw.get("homeassistant_token", AddonOptions.homeassistant_token)).strip(),
        notify_service=normalize_notify_service(str(raw.get("notify_service", AddonOptions.notify_service))),
        alpha_vantage_api_key=str(
            raw.get("alpha_vantage_api_key", AddonOptions.alpha_vantage_api_key)
        ).strip(),
        finnhub_api_key=str(raw.get("finnhub_api_key", AddonOptions.finnhub_api_key)).strip(),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", AddonOptions.poll_interval_seconds)),
        default_threshold_percent=float(
            raw.get("default_threshold_percent", AddonOptions.default_threshold_percent)
        ),
        log_level=str(raw.get("log_level", AddonOptions.log_level)),
    )


def load_ui_config(default_threshold: float, default_notify_service: str) -> UiConfig:
    raw = _load_json(UI_CONFIG_PATH)
    symbols = raw.get("etf_symbols", [])
    if not isinstance(symbols, list):
        symbols = []
    cleaned_symbols = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]
    threshold = raw.get("threshold_percent", default_threshold)
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        threshold_value = default_threshold
    retry_raw = raw.get("market_open_retry_seconds", 60)
    try:
        retry_value = int(retry_raw)
    except (TypeError, ValueError):
        retry_value = 60
    retry_value = max(retry_value, 0)
    notify_services = parse_notify_services(
        raw.get("notify_services", raw.get("notify_service")),
        default_notify_service,
    )
    return UiConfig(
        etf_symbols=cleaned_symbols,
        threshold_percent=max(threshold_value, 0.1),
        market_open_retry_seconds=retry_value,
        notify_services=notify_services,
    )


def save_ui_config(config: UiConfig) -> None:
    UI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "etf_symbols": config.etf_symbols,
        "threshold_percent": config.threshold_percent,
        "market_open_retry_seconds": config.market_open_retry_seconds,
        "notify_services": config.notify_services,
    }
    with UI_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_effective_config() -> EffectiveConfig:
    options = load_addon_options()
    ui = load_ui_config(options.default_threshold_percent, options.notify_service)
    if ui.notify_services:
        options.notify_service = ",".join(ui.notify_services)
    return EffectiveConfig(options=options, ui=ui)
