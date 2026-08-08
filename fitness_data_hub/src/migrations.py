from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrate_provider_identity(engine: Engine) -> None:
    """Upgrade existing SQLite databases to provider-aware persistence.

    Existing records are backfilled as Strava so current installations retain
    all data. The migration is additive and safe to run repeatedly.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "athletes" in tables:
            columns = {column["name"] for column in inspector.get_columns("athletes")}
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE athletes ADD COLUMN provider VARCHAR(50)"))
            if "external_id" not in columns:
                connection.execute(text("ALTER TABLE athletes ADD COLUMN external_id VARCHAR(255)"))
            connection.execute(text("UPDATE athletes SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("UPDATE athletes SET external_id = CAST(id AS TEXT) WHERE external_id IS NULL OR external_id = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_athletes_provider_external_id ON athletes(provider, external_id)"))

        if "activities" in tables:
            columns = {column["name"] for column in inspector.get_columns("activities")}
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE activities ADD COLUMN provider VARCHAR(50)"))
            if "external_id" not in columns:
                connection.execute(text("ALTER TABLE activities ADD COLUMN external_id VARCHAR(255)"))
            connection.execute(text("UPDATE activities SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("UPDATE activities SET external_id = CAST(id AS TEXT) WHERE external_id IS NULL OR external_id = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_activities_provider_external_id ON activities(provider, external_id)"))

        if "sync_state" in tables:
            columns = {column["name"] for column in inspector.get_columns("sync_state")}
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE sync_state ADD COLUMN provider VARCHAR(50)"))
            connection.execute(text("UPDATE sync_state SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_provider ON sync_state(provider)"))
