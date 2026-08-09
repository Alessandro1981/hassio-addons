from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def _table_names(connection: Connection) -> set[str]:
    rows = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _column_names(connection: Connection, table_name: str) -> set[str]:
    # Use the same connection/transaction for schema inspection and DDL.
    # Creating a second inspector connection while SQLite holds a write lock
    # can deadlock the migration itself.
    rows = connection.exec_driver_sql(f'PRAGMA table_xinfo("{table_name}")').fetchall()
    return {row[1] for row in rows}


def migrate_provider_identity(engine: Engine) -> None:
    """Upgrade existing SQLite databases to provider-aware persistence.

    Existing records are backfilled as Strava so current installations retain
    all data. The migration is additive, idempotent and uses one SQLite
    connection for both schema inspection and writes to avoid self-locking.
    """
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA busy_timeout = 30000")
        tables = _table_names(connection)

        if "athletes" in tables:
            columns = _column_names(connection, "athletes")
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE athletes ADD COLUMN provider VARCHAR(50)"))
            if "external_id" not in columns:
                connection.execute(text("ALTER TABLE athletes ADD COLUMN external_id VARCHAR(255)"))
            connection.execute(text("UPDATE athletes SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("UPDATE athletes SET external_id = CAST(id AS TEXT) WHERE external_id IS NULL OR external_id = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_athletes_provider_external_id ON athletes(provider, external_id)"))

        if "activities" in tables:
            columns = _column_names(connection, "activities")
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE activities ADD COLUMN provider VARCHAR(50)"))
            if "external_id" not in columns:
                connection.execute(text("ALTER TABLE activities ADD COLUMN external_id VARCHAR(255)"))
            connection.execute(text("UPDATE activities SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("UPDATE activities SET external_id = CAST(id AS TEXT) WHERE external_id IS NULL OR external_id = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_activities_provider_external_id ON activities(provider, external_id)"))

        if "sync_state" in tables:
            columns = _column_names(connection, "sync_state")
            if "provider" not in columns:
                connection.execute(text("ALTER TABLE sync_state ADD COLUMN provider VARCHAR(50)"))
            connection.execute(text("UPDATE sync_state SET provider = 'strava' WHERE provider IS NULL OR provider = ''"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_state_provider ON sync_state(provider)"))
