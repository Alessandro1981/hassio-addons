"""Entrypoint for the ETF Checker add-on."""

from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

from pathlib import Path
from zoneinfo import ZoneInfo

from .config import EffectiveConfig, UiConfig, load_effective_config, parse_notify_services, save_ui_config
from .etf_monitor import EtfMonitor
from .storage import DailyOpenPrice, PriceSnapshot

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
LOGGER = logging.getLogger(__name__)

APP = Flask(__name__)
MONITOR = EtfMonitor(load_effective_config())
MONITOR.start()


def _ingress_root() -> str:
    return os.environ.get("SUPERVISOR_INGRESS", "").rstrip("/")


def _redact_token(token: str) -> str:
    if not token:
        return "<empty>"
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def _log_startup_diagnostics() -> None:
    if not LOGGER.isEnabledFor(logging.DEBUG):
        return
    LOGGER.debug("Runtime: python=%s platform=%s", sys.version.replace("\n", " "), platform.platform())
    LOGGER.debug("Runtime: uid=%s gid=%s cwd=%s", os.getuid(), os.getgid(), os.getcwd())
    config = load_effective_config()
    options = config.options
    ui = config.ui
    LOGGER.debug("Effective config: homeassistant_url=%s", options.homeassistant_url)
    LOGGER.debug("Effective config: notify_service=%s", options.notify_service)
    LOGGER.debug("Effective config: alpha_vantage_api_key_configured=%s", bool(options.alpha_vantage_api_key))
    LOGGER.debug("Effective config: finnhub_api_key_configured=%s", bool(options.finnhub_api_key))
    LOGGER.debug("Effective config: poll_interval_seconds=%s", options.poll_interval_seconds)
    LOGGER.debug("Effective config: default_threshold_percent=%s", options.default_threshold_percent)
    LOGGER.debug("Effective config: log_level=%s", options.log_level)
    LOGGER.debug("Effective config: homeassistant_token=%s", _redact_token(options.homeassistant_token))
    LOGGER.debug("UI config: symbols=%s", ", ".join(ui.etf_symbols) if ui.etf_symbols else "<none>")
    LOGGER.debug("UI config: threshold_percent=%s", ui.threshold_percent)
    LOGGER.debug("UI config: market_open_retry_seconds=%s", ui.market_open_retry_seconds)
    LOGGER.debug("UI config: notify_services=%s", ", ".join(ui.notify_services) if ui.notify_services else "<none>")
    data_path = Path("/data")
    LOGGER.debug("Data path exists: %s", data_path.exists())
    LOGGER.debug("Options file exists: %s", Path("/data/options.json").exists())
    LOGGER.debug("UI config file exists: %s", Path("/data/ui_config.json").exists())
    LOGGER.debug("State file exists: %s", Path("/data/monitor_state.json").exists())


def _install_exception_logging() -> None:
    def _log_exception(exc_type: type[BaseException], exc: BaseException, tb: Any) -> None:
        LOGGER.exception("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _log_exception


def _merge_config(ui_config: UiConfig) -> EffectiveConfig:
    current = load_effective_config()
    if ui_config.notify_services:
        current.options.notify_service = ",".join(ui_config.notify_services)
    return EffectiveConfig(options=current.options, ui=ui_config)


def _parse_symbols(raw_symbols: str) -> list[str]:
    symbols = [item.strip().upper() for item in raw_symbols.split(",")]
    return [symbol for symbol in symbols if symbol]


def _format_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Europe/Rome"))
    else:
        parsed = parsed.astimezone(ZoneInfo("Europe/Rome"))
    return parsed.strftime("%Y-%m-%d %H:%M:%S CET")


def _format_baseline_update(value: str | None) -> str | None:
    return _format_datetime(value)


def _snapshot_payload(snapshot: PriceSnapshot | DailyOpenPrice | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    payload: dict[str, Any] = {
        "price": snapshot.price,
        "read_at": snapshot.read_at,
        "read_at_formatted": _format_datetime(snapshot.read_at),
    }
    if isinstance(snapshot, DailyOpenPrice):
        payload["date"] = snapshot.date
    return payload


def _percent_change(reference: float | None, current: float | None) -> float | None:
    if reference in (None, 0) or current is None:
        return None
    return ((current - reference) / reference) * 100.0


def _homeassistant_headers() -> dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN is not available. Check homeassistant_api in config.yaml.")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@APP.route("/")
def index() -> str:
    config = load_effective_config()
    state = MONITOR.state
    baselines = {
        symbol: state.baselines.get(symbol)
        for symbol in config.ui.etf_symbols
        if symbol in state.baselines
    }
    price_rows = []
    for symbol in config.ui.etf_symbols:
        latest = state.last_prices.get(symbol)
        daily_open = state.daily_open_prices.get(symbol)
        latest_price = latest.price if latest else None
        daily_open_price = daily_open.price if daily_open else None
        daily_change_percent = _percent_change(daily_open_price, latest_price)
        price_rows.append(
            {
                "symbol": symbol,
                "daily_open_price": daily_open_price,
                "daily_open_read_at": _format_datetime(daily_open.read_at) if daily_open else None,
                "latest_price": latest_price,
                "latest_read_at": _format_datetime(latest.read_at) if latest else None,
                "daily_change_percent": daily_change_percent,
                "daily_change_class": "positive" if daily_change_percent and daily_change_percent > 0 else "negative" if daily_change_percent and daily_change_percent < 0 else "neutral",
            }
        )
    return render_template(
        "index.html",
        ingress_root=_ingress_root(),
        symbols=", ".join(config.ui.etf_symbols),
        threshold=config.ui.threshold_percent,
        market_open_retry_seconds=config.ui.market_open_retry_seconds,
        poll_interval=config.options.poll_interval_seconds,
        notify_service=config.options.notify_service,
        notify_services=config.ui.notify_services,
        baselines=baselines,
        price_rows=price_rows,
        last_baseline_update=_format_baseline_update(state.last_baseline_update),
    )


@APP.get("/assets/style.css")
def stylesheet() -> Any:
    return send_from_directory(Path(__file__).parent / "static", "style.css")


@APP.get("/api/notify-services")
def get_notify_services() -> Any:
    try:
        import requests

        config = load_effective_config()
        response = requests.get(
            f"{config.options.homeassistant_url}/api/services",
            headers=_homeassistant_headers(),
            timeout=10,
        )
        response.raise_for_status()
        services_payload = response.json()
    except Exception:  # noqa: BLE001
        LOGGER.exception("Unable to fetch Home Assistant services")
        return jsonify({"services": [], "error": "Unable to fetch notify services"})

    notify_services: list[str] = []
    for domain_payload in services_payload:
        if domain_payload.get("domain") != "notify":
            continue
        services = domain_payload.get("services", {})
        if isinstance(services, dict):
            notify_services.extend(f"notify/{service}" for service in services.keys())
        elif isinstance(services, list):
            notify_services.extend(f"notify/{service}" for service in services)
    return jsonify({"services": sorted(set(notify_services))})


@APP.get("/api/config")
def get_config() -> Any:
    config = load_effective_config()
    state = MONITOR.state
    payload = {
        "etf_symbols": config.ui.etf_symbols,
        "threshold_percent": config.ui.threshold_percent,
        "market_open_retry_seconds": config.ui.market_open_retry_seconds,
        "poll_interval_seconds": config.options.poll_interval_seconds,
        "notify_service": config.options.notify_service,
        "notify_services": config.ui.notify_services,
        "baselines": state.baselines,
        "last_baseline_update": state.last_baseline_update,
        "last_prices": {
            symbol: _snapshot_payload(snapshot)
            for symbol, snapshot in state.last_prices.items()
        },
        "daily_open_prices": {
            symbol: _snapshot_payload(snapshot)
            for symbol, snapshot in state.daily_open_prices.items()
        },
    }
    return jsonify(payload)


@APP.post("/api/config")
def update_config() -> Any:
    data = request.get_json(silent=True) or {}
    raw_symbols = str(data.get("etf_symbols", ""))
    symbols = _parse_symbols(raw_symbols)
    threshold_raw = data.get("threshold_percent")
    try:
        threshold = float(threshold_raw)
    except (TypeError, ValueError):
        threshold = load_effective_config().options.default_threshold_percent
    threshold = max(threshold, 0.1)
    retry_raw = data.get("market_open_retry_seconds", load_effective_config().ui.market_open_retry_seconds)
    try:
        retry_after_open = int(retry_raw)
    except (TypeError, ValueError):
        retry_after_open = load_effective_config().ui.market_open_retry_seconds
    retry_after_open = max(retry_after_open, 0)
    current_config = load_effective_config()
    notify_services = parse_notify_services(
        data.get("notify_services", data.get("notify_service")),
        current_config.options.notify_service,
    )
    ui_config = UiConfig(
        etf_symbols=symbols,
        threshold_percent=threshold,
        market_open_retry_seconds=retry_after_open,
        notify_services=notify_services,
    )
    save_ui_config(ui_config)
    MONITOR.update_config(_merge_config(ui_config))
    MONITOR.run_once()
    return jsonify(
        {
            "status": "ok",
            "etf_symbols": symbols,
            "threshold_percent": threshold,
            "market_open_retry_seconds": retry_after_open,
            "notify_services": notify_services,
        }
    )


@APP.post("/api/poll")
def trigger_poll() -> Any:
    MONITOR.run_once()
    return jsonify({"status": "ok"})


@APP.route("/health")
def health() -> Any:
    return jsonify({"status": "ok"})


@APP.route("/ingress")
def ingress_redirect() -> Any:
    root = _ingress_root()
    if root:
        return redirect(f"{root}/")
    return redirect(url_for("index"))


def main() -> None:
    port = int(os.environ.get("PORT", "8099"))
    ingress_entry = _ingress_root()
    _install_exception_logging()
    LOGGER.info("Starting ETF Checker on port %s (ingress root: %s)", port, ingress_entry or "-")
    _log_startup_diagnostics()
    try:
        APP.run(host="0.0.0.0", port=port, debug=False)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Flask server failed to start")
        raise


if __name__ == "__main__":
    main()
