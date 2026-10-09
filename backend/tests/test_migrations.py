"""Alembic migrations apply cleanly from an empty database (Spec J03)."""
import os
import tempfile

from alembic import command
from alembic.config import Config


def test_migrations_upgrade_head_on_empty_db():
    tmp = tempfile.mkdtemp(prefix="ala-migration-")
    db_path = os.path.join(tmp, "migration.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("DATABASE_URL", None)
    # Second run must be a no-op (migrations are re-runnable).
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("DATABASE_URL", None)
