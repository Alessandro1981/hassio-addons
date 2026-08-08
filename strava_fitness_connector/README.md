# Strava Fitness Connector — DEPRECATED

> **This add-on is deprecated and should not be used for new installations.**
>
> It has been replaced by **Fitness Data Hub**, available in this same Home Assistant add-on repository under `fitness_data_hub`.

## Why it was deprecated

Strava Fitness Connector was designed around a single data source: Strava. Over time, synchronization, statistics, training-load calculation, insights and Home Assistant integration became useful independently of Strava itself.

Continuing to evolve those capabilities inside a Strava-specific add-on would tightly couple the application to one provider and make support for alternative fitness data sources unnecessarily difficult.

The project therefore evolved into **Fitness Data Hub**, whose goal is to separate provider-specific data acquisition from storage, analytics, statistics, insights and Home Assistant integration.

## Replacement: Fitness Data Hub

Fitness Data Hub is the successor to this add-on and currently retains Strava support while providing the foundation for additional providers.

Architecture direction:

`Strava / future providers -> Fitness Data Hub -> Home Assistant`

Fitness Data Hub currently provides the functionality previously offered here, including:

- Strava OAuth authentication
- activity import and incremental synchronization
- automatic background synchronization
- athlete information
- weekly, monthly and year-to-date statistics
- estimated training load
- fitness insights
- REST API for Home Assistant
- local persistence
- Home Assistant Ingress support

For new installations use **Fitness Data Hub** (`fitness_data_hub`).

## Existing installations

Existing installations can remain available temporarily for migration or troubleshooting, but active use is no longer recommended. Running both add-ons is unnecessary and can result in duplicate requests to the Strava API.

After verifying that Home Assistant dashboards and REST sensors use Fitness Data Hub, this add-on can be stopped and uninstalled from Home Assistant.

The source remains in the repository as a migration and historical reference while Fitness Data Hub evolves.
