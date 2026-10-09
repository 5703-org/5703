"""Read-only observations of the worker layout's PostgreSQL advisory locks.

The locks identify which queue a worker process currently owns. They are not a
heartbeat: a process can hold a lock while stalled, and a missing lock only
describes the instant of observation.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

QUEUE_LOCKS = {"all": 5703001, "interactive": 5703002, "background": 5703003}

_LOCK_QUERY = text(
    """
    SELECT objid::bigint AS lock_id, mode
    FROM pg_locks
    WHERE locktype = 'advisory'
      AND granted
      AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
      AND classid = 0
      AND objsubid = 1
      AND objid IN (5703001, 5703002, 5703003)
    """
)


def _unavailable() -> dict:
    return {
        "observation": "unavailable",
        "layout": "unavailable",
        "interactive": {"lock_observed": None},
        "background": {"lock_observed": None},
    }


def summarize_locks(rows: list[tuple[int, str]]) -> dict:
    """Classify observed lock modes without assuming they prove responsiveness."""
    held = {(int(lock_id), mode) for lock_id, mode in rows}
    all_exclusive = (QUEUE_LOCKS["all"], "ExclusiveLock") in held
    all_shared = (QUEUE_LOCKS["all"], "ShareLock") in held
    interactive = (QUEUE_LOCKS["interactive"], "ExclusiveLock") in held
    background = (QUEUE_LOCKS["background"], "ExclusiveLock") in held
    if held == {(QUEUE_LOCKS["all"], "ExclusiveLock")}:
        layout = "all"
        observed_interactive = observed_background = True
    elif (
        all_shared
        and not all_exclusive
        and held
        <= {
            (QUEUE_LOCKS["all"], "ShareLock"),
            (QUEUE_LOCKS["interactive"], "ExclusiveLock"),
            (QUEUE_LOCKS["background"], "ExclusiveLock"),
        }
    ):
        layout = "split" if interactive and background else "partial"
        observed_interactive = interactive
        observed_background = background
    elif not held:
        layout = "none"
        observed_interactive = observed_background = False
    else:
        # Unexpected modes/layouts need operator review; do not assert a lane.
        layout = "unexpected"
        observed_interactive = observed_background = False
    return {
        "observation": "postgres_advisory_lock",
        "layout": layout,
        "interactive": {"lock_observed": observed_interactive},
        "background": {"lock_observed": observed_background},
    }


def inspect_worker_locks(db: Session) -> dict:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return _unavailable()
    try:
        return summarize_locks([(row.lock_id, row.mode) for row in db.execute(_LOCK_QUERY)])
    except SQLAlchemyError:
        # Availability of the admin projection must not depend on pg_locks
        # permissions or a version-specific system-catalog layout.
        return _unavailable()
