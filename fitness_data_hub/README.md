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

## Prerequisite: public OAuth callback

Fitness Data Hub can be opened from Home Assistant through Ingress, including through Nabu Casa, but provider OAuth callbacks must reach the add-on directly through a stable public HTTPS URL. Home Assistant Ingress/Nabu Casa is therefore not used as the Strava OAuth callback endpoint.

The validated setup for Fitness Data Hub uses **Tailscale Funnel** to expose only Fitness Data Hub port `8100` over HTTPS. Tailscale Funnel is therefore a prerequisite for the current Strava OAuth setup unless you provide another equivalent stable public HTTPS reverse proxy yourself.

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

Before configuring Funnel:

1. Install and authenticate the Tailscale Home Assistant add-on.
2. In the Tailscale admin console, enable **MagicDNS**.
3. Enable **HTTPS Certificates** for the tailnet.
4. Enable/approve **Funnel** for the tailnet when prompted.
5. Keep `Share Home Assistant with Serve or Funnel` set to **disabled** if the intention is to expose only Fitness Data Hub.
6. Fitness Data Hub must expose port `8100` on the Home Assistant host and be reachable over plain HTTP on the local network.

Tailscale Funnel accepts public HTTPS listeners on ports `443`, `8443`, or `10000`. This project uses **8443** so that the endpoint is dedicated to Fitness Data Hub.

### Configure the Fitness Data Hub Funnel

The Home Assistant Tailscale add-on UI can publish Home Assistant itself, but it does not provide a UI option for publishing an arbitrary second add-on. Configure the Fitness Data Hub Funnel once from the Tailscale container CLI.

Install/open **Advanced SSH & Web Terminal** and temporarily disable its Protection Mode so that Docker is accessible. Then locate and enter the Tailscale container:

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Image}}" | grep -i tailscale
docker exec -it $(docker ps -q -f name=tailscale) /bin/bash
```

Inside the Tailscale container, the CLI supplied by this add-on is available as `/opt/tailscale`.

Check connectivity:

```bash
/opt/tailscale status
```

Create the persistent Funnel, replacing the local Home Assistant address if necessary:

```bash
/opt/tailscale funnel --bg --https=8443 --set-path=/ http://192.168.1.242:8100
```

Check the result:

```bash
/opt/tailscale funnel status
```

Expected shape:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443 (Funnel on)
|-- / proxy http://192.168.1.242:8100
```

The `--bg` configuration is persistent across Tailscale/device restarts. After the Funnel is configured, re-enable Protection Mode on Advanced SSH & Web Terminal.

### Validate the public endpoint

From a device outside the Home Assistant LAN, open:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443/health
```

Fitness Data Hub must return a successful health response before OAuth is configured.

New Funnel DNS records can take several minutes to become publicly resolvable. If the browser reports `NXDOMAIN`, verify public DNS resolution and retry after propagation.

### Configure Fitness Data Hub

Set:

```text
public_base_url = https://<tailscale-device>.<tailnet>.ts.net:8443
```

Do not append `/auth/callback` to `public_base_url`; Fitness Data Hub builds the callback path itself.

For the validated installation used during development, the value is:

```text
https://homeassistant.taildd4425.ts.net:8443
```

`app_base_url` remains the internal/direct application URL fallback and is separate from the public OAuth URL.

### Configure the Strava application

In the Strava API application set **Authorization Callback Domain** to the domain only:

```text
<tailscale-device>.<tailnet>.ts.net
```

Do not include `https://`, the port, a slash, or `/auth/callback` in this Strava field.

Fitness Data Hub will use the complete callback URL:

```text
https://<tailscale-device>.<tailnet>.ts.net:8443/auth/callback
```

### OAuth and Home Assistant Ingress

External identity-provider login pages should not be embedded in the Home Assistant Ingress iframe. When Fitness Data Hub needs initial Strava authentication from Ingress, it presents a Connect Strava page that opens the external OAuth flow outside the iframe. After authentication, the Home Assistant UI can continue to use Ingress normally.

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

### 0.2.0

Promotes the validated Strava OAuth and Home Assistant Ingress implementation to the 0.2 baseline. Adds complete documentation for the required public OAuth callback architecture, including Tailscale Funnel setup, validation, Strava callback-domain configuration and the separation between Home Assistant Ingress and external OAuth.

### 0.1.4

Improves initial Strava authentication when Fitness Data Hub is opened through Home Assistant Ingress by keeping the external OAuth flow outside the embedded iframe.

### 0.1.3

Adds dynamic Home Assistant Ingress path handling for redirects and FastAPI documentation endpoints.

### 0.1.2

Adds Home Assistant Ingress support while keeping port 8100 available for local REST access. Clarifies the separation between Ingress access and the external OAuth callback URL.

### 0.1.1

Introduces a dedicated `public_base_url` setting for OAuth callbacks.

### 0.1.0

Initial Fitness Data Hub release, derived from the proven Strava Fitness Connector codebase and rebranded as the foundation for provider-independent development.
