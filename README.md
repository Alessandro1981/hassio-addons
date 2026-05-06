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

Personal ETF monitoring add-on for Home Assistant focused on long-term ETF portfolios and deep-and-hold strategies.

Features:
- ETF price monitoring
- Daily opening price tracking
- Latest price dashboard with timestamps
- Percentage variation from daily opening price
- Home Assistant native dashboard UI
- Dynamic notification service selector (notify.*)
- Automatic Home Assistant Supervisor token usage
- Market-hours-aware polling
- Configurable polling interval
- Configurable percentage threshold
- Alpha Vantage and Finnhub provider support
- Rate-limit protection and provider cooldown handling
- Downside-only notifications (alerts only on ETF drops)
- Home Assistant Companion notifications
- Mobile-friendly responsive UI

Source repository / Home Assistant catalog:
https://github.com/Alessandro1981/hassio-addons/tree/main/etf_checker

---

## Installation

In Home Assistant, add this repository URL to the Add-on Store repositories:

```text
https://github.com/Alessandro1981/hassio-addons
```

Then reload the Add-on Store and install the add-on you want to use.
