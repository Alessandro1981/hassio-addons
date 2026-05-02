# Home Assistant Add-ons

A curated collection of personal Home Assistant add-ons for fitness tracking, finance monitoring and automation.

## Available add-ons

This repository currently includes 2 add-ons:

### Strava Fitness Connector

Personal Strava fitness data connector with sync, stats and insights.

Features:
- Strava OAuth authentication
- Activity import and incremental sync
- Automatic background sync
- YTD and weekly statistics
- Rule-based insights

Source repository:
https://github.com/Alessandro1981/hassio-addons/tree/main/strava_fitness_connector

---

### ETF Checker

Personal ETF monitoring add-on that checks configured ETF prices and sends Home Assistant Companion notifications when a percentage threshold is exceeded.

Features:
- ETF price monitoring
- Configurable polling interval
- Configurable percentage threshold
- Daily opening price and latest price dashboard
- Home Assistant Companion notifications
- Alpha Vantage and Finnhub API key configuration

Source repository / Home Assistant catalog:
https://github.com/Alessandro1981/hassio-addons/tree/main/etf_checker

---

## Installation

In Home Assistant, add this repository URL to the Add-on Store repositories:

```text
https://github.com/Alessandro1981/hassio-addons
```

Then reload the Add-on Store and install the add-on you want to use.
