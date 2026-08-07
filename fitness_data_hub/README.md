# Fitness Data Hub

Fitness Data Hub is a Home Assistant add-on for collecting, storing and analysing personal fitness activity data independently from the data provider.

## Current provider

- Strava

Future versions will introduce additional providers while keeping the dashboard, statistics and insights independent from the source of the activity data.

## Features

- Strava OAuth authentication
- Activity import and incremental sync
- Automatic background sync
- Athlete information
- Weekly and monthly statistics
- Year-to-date statistics by activity type
- Estimated training load
- Rule-based fitness insights
- REST API for Home Assistant dashboards and sensors
- Local SQLite storage

## Access

The add-on exposes its web interface and REST API on port `8100`.

Useful endpoints include:

- `/health`
- `/docs`
- `/stats/dashboard`

## Configuration

Select the fitness data provider and configure its credentials. Version 0.1.0 supports Strava only.

Required Strava settings:

- Strava Client ID
- Strava Client Secret
- Strava scopes

Optional settings include the public application base URL and background synchronization interval.

## Provider architecture

Fitness Data Hub is being developed so that provider-specific data acquisition is separated from storage, analytics, statistics and Home Assistant integration.

Current:

`Strava -> Fitness Data Hub -> Home Assistant`

Planned:

`Strava / FIT / other providers -> Fitness Data Hub -> Home Assistant`

## Version

### 0.1.0

Initial Fitness Data Hub release, derived from the proven Strava Fitness Connector codebase and rebranded as the foundation for provider-independent development.
