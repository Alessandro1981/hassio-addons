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
- Home Assistant Ingress support for local and Nabu Casa remote access

## Access

The add-on supports Home Assistant Ingress and can therefore be opened from the Home Assistant UI, including through Nabu Casa Remote UI.

For local debugging and REST access, port `8100` remains exposed.

Useful endpoints include:

- `/health`
- `/docs`
- `/stats/dashboard`

## Configuration

Select the fitness data provider and configure its credentials. The current release supports Strava only.

Required Strava settings:

- Strava Client ID
- Strava Client Secret
- Strava scopes

URL settings:

- `app_base_url`: internal/direct application URL used as a fallback
- `public_base_url`: externally reachable base URL used to build the OAuth callback URL

`public_base_url` is intentionally separate from Home Assistant Ingress. Ingress is suitable for accessing the add-on UI through Home Assistant/Nabu Casa, while OAuth providers such as Strava require a stable callback URL that they can redirect to directly.

## Provider architecture

Fitness Data Hub is being developed so that provider-specific data acquisition is separated from storage, analytics, statistics and Home Assistant integration.

Current:

`Strava -> Fitness Data Hub -> Home Assistant`

Planned:

`Strava / FIT / other providers -> Fitness Data Hub -> Home Assistant`

## Versions

### 0.1.2

Adds Home Assistant Ingress support while keeping port 8100 available for local REST access. Clarifies the separation between Ingress access and the external OAuth callback URL.

### 0.1.1

Introduces a dedicated `public_base_url` setting for OAuth callbacks.

### 0.1.0

Initial Fitness Data Hub release, derived from the proven Strava Fitness Connector codebase and rebranded as the foundation for provider-independent development.
