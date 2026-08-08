# Fitness Data Hub

Fitness Data Hub is a Home Assistant add-on for collecting, storing and analysing personal fitness activity data independently from the data provider.

## Current provider

- Strava

The architecture is being evolved so that provider-specific authentication and acquisition remain isolated from persistence, analytics, statistics, insights and Home Assistant integration.

## Features

- Provider-based authentication and activity acquisition
- Provider-independent normalized activity and athlete payloads
- Provider-aware activity, athlete and synchronization persistence
- Strava OAuth authentication
- Activity import and incremental synchronization
- Automatic background synchronization
- Home Assistant persistent notifications when provider connection/sync fails
- Athlete information
- Weekly and monthly statistics
- Year-to-date statistics by activity type
- Estimated training load
- Rule-based fitness insights
- REST API for Home Assistant dashboards and sensors
- Local SQLite storage
- Home Assistant Ingress support

## Provider health notifications

From version **0.2.6**, Fitness Data Hub reports provider failures directly through Home Assistant persistent notifications.

A provider problem notification contains:

```text
Fitness Data Hub - provider problem

Provider: strava
Operation: incremental synchronization
Symptom: HTTP 403 Forbidden: {...}
```

The same notification ID is reused for subsequent failures from the same provider, avoiding notification spam. A successful provider authentication or synchronization dismisses the active provider-problem notification automatically.

Failures covered include:

- OAuth configuration/authentication failures;
- token refresh failures;
- provider connection/API errors encountered during synchronization;
- full import failures;
- incremental synchronization failures.

Provider error reporting is best-effort: failure to create a Home Assistant notification never replaces or hides the original provider exception. The add-on uses the Home Assistant Core API through the Supervisor proxy and therefore requires `homeassistant_api: true`.

## Provider-aware persistence

Provider identity is no longer implicit in activity records.

Activities are identified by the combination:

```text
provider + external_id
```

Synchronization state is stored independently per provider. Athlete records also carry their source `provider` and `external_id`.

Existing databases are migrated automatically and existing records are backfilled as `strava`, preserving current installations. The migration is additive and idempotent.

This prepares the database for multiple providers without assuming that source IDs are globally unique.

## Prerequisite: public OAuth callback

Fitness Data Hub can be opened from Home Assistant through Ingress, including through Nabu Casa, but providers such as Strava require an OAuth callback that is directly reachable through a stable public HTTPS URL.

The validated Strava setup uses **Tailscale Funnel** to expose only Fitness Data Hub port `8100` over HTTPS. Tailscale Funnel is therefore a prerequisite for the current Strava OAuth setup unless another equivalent stable HTTPS reverse proxy is provided.

Validated architecture:

```text
Home Assistant UI / Nabu Casa
        |
        +--> Home Assistant Ingress --> Fitness Data Hub UI

Strava OAuth / Internet
        |
        +--> https://<tailscale-device>.<tailnet>.ts.net:8443
                    |
                    +--> Tailscale Funnel
                              |
                              +--> http://<home-assistant-host>:8100
                                        |
                                        +--> Fitness Data Hub
```

### Tailscale requirements

1. Install and authenticate the Tailscale Home Assistant add-on.
2. Enable MagicDNS in Tailscale.
3. Enable HTTPS certificates for the tailnet.
4. Enable/approve Funnel when requested.
5. Keep `Share Home Assistant with Serve or Funnel` disabled when only Fitness Data Hub should be published.
6. Ensure Fitness Data Hub port `8100` is reachable locally.

The validated public listener uses port `8443`.

### Configure Funnel

Open Advanced SSH & Web Terminal and temporarily disable Protection Mode so Docker is available. Locate and enter the Tailscale container:

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}" | grep -i tailscale
docker exec -it $(docker ps -q -f name=tailscale) /bin/bash
```

Inside the Tailscale container:

```bash
/opt/tailscale status
/opt/tailscale funnel --bg --https=8443 --set-path=/ http://192.168.1.242:8100
/opt/tailscale funnel status
```

Expected shape:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443 (Funnel on)
|-- / proxy http://192.168.1.242:8100
```

After configuration, re-enable Protection Mode.

### Validate the public endpoint

From outside the Home Assistant LAN open:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443/health
```

The endpoint must return a successful health response before OAuth is configured. New Funnel DNS records can take several minutes to become publicly resolvable.

### Configure Fitness Data Hub

Set:

```text
public_base_url = https://<tailscale-device>.<tailnet>.ts.net:8443
```

Do not append `/auth/callback`; Fitness Data Hub builds the callback path itself.

### Configure Strava

Set **Authorization Callback Domain** to the domain only:

```text
<tailscale-device>.<tailnet>.ts.net
```

Do not include `https://`, the port or `/auth/callback`.

Fitness Data Hub will use:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443/auth/callback
```

External authentication is opened outside the Home Assistant Ingress iframe.

## Access

Useful endpoints:

- `/health`
- `/docs`
- `/stats/dashboard`
- `/sync/incremental`

Port `8100` remains exposed for local REST access.

## Provider architecture

Current structure:

```text
src/providers/
  base.py       -> FitnessProvider contract
  factory.py    -> provider selection
  models.py     -> ProviderActivity / ProviderAthlete normalized payloads
  strava.py     -> Strava adapter and normalization

Provider API
    |
    v
Provider adapter
    |
    v
Normalized payloads
    |
    v
Provider-aware persistence
    |
    +--> Analytics / Insights / REST API / Home Assistant
```

The application core no longer consumes Strava activity JSON directly. Provider-specific payloads are normalized at the provider boundary before entering shared importer and analytics logic.

## Versions

### 0.2.6

Completes the current provider-persistence step and introduces provider health notifications. Athlete records now include provider/external identity, existing SQLite installations are migrated and backfilled automatically, and synchronization/import failures create a Home Assistant persistent notification containing the provider, failed operation and symptom. Successful authentication or synchronization clears the notification.

### 0.2.5

Enables access to the Home Assistant Core API from the add-on in preparation for provider health notifications.

### 0.2.4

Introduces provider-aware activity and synchronization persistence using `provider + external_id` and per-provider sync state, together with automatic migration of existing Strava data.

### 0.2.3

Introduces provider-independent `ProviderActivity` and `ProviderAthlete` payloads. Strava responses are normalized inside `StravaProvider` before crossing the provider boundary.

### 0.2.2

Moves the OAuth lifecycle behind the `FitnessProvider` contract. FastAPI no longer imports or instantiates `StravaClient` directly.

### 0.2.1

Starts the provider abstraction with the `FitnessProvider` contract, provider factory and `StravaProvider` adapter.

### 0.2.0

Stable documented baseline for Strava OAuth, Home Assistant Ingress and Tailscale Funnel callback setup.
