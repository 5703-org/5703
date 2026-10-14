"""Transaction-scoped source storage/publication serialization, separate from workers."""

from sqlalchemy import text

# Worker layout/lane keys remain 5703001, 5703002 and 5703003.
# All ingestion, import, cleanup and publication callers share this separate key.
SOURCE_MAINTENANCE_LOCK = 5703101


def lock_source_maintenance(db):
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": SOURCE_MAINTENANCE_LOCK},
        )
