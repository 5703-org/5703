"""No-network migration preflight and isolated SQLite compatibility."""

from pathlib import Path
import os
import subprocess
import sys
import pytest
from sqlalchemy import create_engine, text
from app.db.migration_support import require_postgresql_migration_url


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost/db",
        "postgresql+psycopg://u:p@localhost/db",
        "postgresql+psycopg2://u:p@localhost/db",
    ],
)
def test_postgresql_forms_preserved(url):
    assert require_postgresql_migration_url(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "sqlite+pysqlite:///:memory:",
        "mysql://u:private@localhost/db",
        "",
        "not a URL",
        "postgresql-lookalike://u:private@localhost/db",
    ],
)
def test_unsupported_targets_rejected_without_secret(url):
    with pytest.raises(ValueError) as error:
        require_postgresql_migration_url(url)
    assert "private" not in str(error.value)


def test_sqlite_engine_remains_usable():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE fixture (id INTEGER PRIMARY KEY)"))
            conn.execute(text("INSERT INTO fixture VALUES (1)"))
            assert conn.scalar(text("SELECT count(*) FROM fixture")) == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize("entry", ["cli", "alembic", "offline"])
@pytest.mark.parametrize("existing", [False, True])
def test_actual_entries_reject_before_database_creation(tmp_path, entry, existing):
    root = Path(__file__).resolve().parents[2]
    target = tmp_path / "must-not-exist.db"
    if existing:
        engine = create_engine("sqlite:///" + target.as_posix())
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE synthetic_sentinel (id INTEGER PRIMARY KEY)"))
            conn.execute(text("INSERT INTO synthetic_sentinel VALUES (42)"))
        engine.dispose()
    before = target.read_bytes() if existing else None
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + target.as_posix(),
        "PYTHONPATH": os.pathsep.join([str(root), str(root / "backend")]),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    args = (
        [sys.executable, "-m", "app.cli", "migrate"]
        if entry == "cli"
        else [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(root / "backend/alembic.ini"),
            "upgrade",
            "head",
        ]
    )
    if entry == "offline":
        args.append("--sql")
    result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "Current application migrations require PostgreSQL/pgvector" in result.stderr
    assert target.read_bytes() == before if existing else not target.exists()


def test_alembic_preflight_precedes_engine_and_context_creation(monkeypatch):
    import runpy
    import sqlalchemy
    from alembic import context
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Unsupported database must never reach engine/context creation")

    monkeypatch.setenv("DATABASE_URL", "mysql://user:private-sentinel@localhost/unused")
    monkeypatch.setattr(context, "config", Config(), raising=False)
    monkeypatch.setattr(context, "configure", forbidden)
    monkeypatch.setattr(sqlalchemy, "engine_from_config", forbidden)
    before = list(sys.path)
    try:
        with pytest.raises(ValueError) as error:
            runpy.run_path(str(root / "backend/alembic/env.py"))
        assert "PostgreSQL/pgvector" in str(error.value)
        assert "private-sentinel" not in str(error.value)
        assert calls == []
    finally:
        sys.path[:] = before
