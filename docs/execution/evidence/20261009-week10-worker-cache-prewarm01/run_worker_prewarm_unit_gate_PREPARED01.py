"""Run only the affected synthetic unit tests under pre-import isolation guards.

This file is a prepared runner, not an execution receipt. It permits SQLite
:memory: and files inside this runner's new pytest temp directory. Every other
database transport, socket connection, pool bypass and dotenv path read stops.
"""

from __future__ import annotations

import contextvars
import os
from pathlib import Path
import socket
import sqlite3
import sqlite3.dbapi2
import sys


MAIN = Path(r"E:\5703\learning-assistant")
VERIFICATION = Path(__file__).resolve().parent
TEMP = VERIFICATION / "pytest-temp-prewarm01"
JUNIT = VERIFICATION / "worker-prewarm-junit01.xml"
TESTS = (
    MAIN / "tests/unit/test_worker_retrieval_prewarm.py",
    MAIN / "tests/unit/test_retrieval_cache.py",
    MAIN / "tests/unit/test_worker_queues.py",
)

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
if TEMP.exists() or JUNIT.exists():
    raise SystemExit("Create-only unit gate refuses to overwrite an earlier run")
if not all(path.is_file() for path in TESTS):
    raise SystemExit("All three adopted and existing unit test files must exist")


def no_network(*_, **__):
    raise AssertionError("Network connections are prohibited in this synthetic unit gate")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network


def allowed_sqlite_filename(filename):
    value = os.fsdecode(filename)
    if value == ":memory:":
        return True
    if value.lower().startswith("file:"):
        return False
    candidate = Path(value).resolve()
    return candidate.is_relative_to(TEMP.resolve()) and candidate != TEMP.resolve()


original_sqlite_connect = sqlite3.connect


def isolated_sqlite_connect(database, *args, **kwargs):
    if not allowed_sqlite_filename(database) or kwargs.get("uri", False):
        raise AssertionError("SQLite files must stay within this new synthetic pytest directory")
    return original_sqlite_connect(database, *args, **kwargs)


sqlite3.connect = isolated_sqlite_connect
sqlite3.dbapi2.connect = isolated_sqlite_connect

# Import database libraries only after all socket transports have been blocked.
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool


sqlite_scope = contextvars.ContextVar("synthetic_sqlite_scope", default=False)
original_engine_connect = Engine.connect
original_raw_connection = Engine.raw_connection
original_pool_connect = Pool.connect


def require_isolated_sqlite(engine):
    url = engine.url
    if url.get_backend_name() != "sqlite" or url.query:
        raise AssertionError("Only isolated synthetic SQLite engines may connect")
    if not allowed_sqlite_filename(url.database or ":memory:"):
        raise AssertionError("Ambient, Main and preserved fixture databases are prohibited")


def engine_connect(engine, *args, **kwargs):
    require_isolated_sqlite(engine)
    token = sqlite_scope.set(True)
    try:
        return original_engine_connect(engine, *args, **kwargs)
    finally:
        sqlite_scope.reset(token)


def raw_connection(engine, *args, **kwargs):
    require_isolated_sqlite(engine)
    token = sqlite_scope.set(True)
    try:
        return original_raw_connection(engine, *args, **kwargs)
    finally:
        sqlite_scope.reset(token)


def pool_connect(pool, *args, **kwargs):
    if not sqlite_scope.get():
        raise AssertionError("A direct database pool connection cannot bypass the Engine guard")
    return original_pool_connect(pool, *args, **kwargs)


Engine.connect = engine_connect
Engine.raw_connection = raw_connection
Pool.connect = pool_connect

from dotenv.main import DotEnv
from pydantic_settings.sources.providers.dotenv import DotEnvSettingsSource


def no_dotenv_path(*_, **__):
    raise AssertionError("Actual dotenv paths may not be read in this synthetic unit gate")


def no_env_files(source):
    if source.env_file is not None:
        raise AssertionError("Settings in this gate must use _env_file=None")
    return {}


DotEnv._get_stream = no_dotenv_path
DotEnvSettingsSource._read_env_file = no_dotenv_path
DotEnvSettingsSource._read_env_files = no_env_files

sys.path.insert(0, str(MAIN))
sys.path.insert(0, str(MAIN / "backend"))

# Clear process-local application settings before app.worker or any test import.
# No environment values are logged, copied, persisted or changed outside this process.
from app.core import config


for field_name, field in config.Settings.model_fields.items():
    aliases = [field_name]
    if isinstance(field.validation_alias, str):
        aliases.append(field.validation_alias)
    else:
        aliases.extend(
            alias
            for alias in getattr(field.validation_alias, "choices", [])
            if isinstance(alias, str)
        )
    for alias in aliases:
        os.environ.pop(alias, None)
        os.environ.pop(alias.upper(), None)
for name in ("TEST_DATABASE_SERVER", "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGPASSFILE"):
    os.environ.pop(name, None)
os.environ.update(
    DATABASE_URL="sqlite:///:memory:",
    APP_ENV="test",
    MODEL_MODE="mock",
    LLM_PROVIDER="mock",
    LLM_MODEL="authored-extractive-v1",
    LLM_API_KEY="",
    LOCAL_MODEL_DEVICE="recorded",
    SECRET_KEY="synthetic-unit-secret-at-least-thirty-two-characters",
    STORAGE_ROOT=str(VERIFICATION / "synthetic-storage-unused01"),
    MODEL_CONFIG_KEY_FILE=str(VERIFICATION / "synthetic-key-unused01"),
)
config.get_settings.cache_clear()

import pytest


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [
                "-c", str(MAIN / "pytest.ini"),
                "-p", "no:cacheprovider",
                "-o", "addopts=",
                "--basetemp", str(TEMP),
                "--junitxml", str(JUNIT),
                "-q",
                *(str(path) for path in TESTS),
            ]
        )
    )
