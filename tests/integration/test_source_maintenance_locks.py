"""Actual PostgreSQL source operations serialize without taking worker-lane locks."""

from contextlib import contextmanager
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.identity.models import User
from app.modules.knowledge import service
from app.modules.knowledge.models import Document, DocumentVersion, ProcessingRun
from app.operations import apply_cleanup, cleanup_plan
from app.platform_core.source_locks import SOURCE_MAINTENANCE_LOCK
from app.platform_core.worker_locks import QUEUE_LOCKS
from scripts.release import corpus_bundle

from .test_chat_runtime import corpus


@contextmanager
def _split_workers(engine):
    with engine.connect() as holder:
        assert holder.scalar(
            text("SELECT pg_try_advisory_lock_shared(:key)"), {"key": QUEUE_LOCKS["all"]}
        )
        for lane in ("interactive", "background"):
            assert holder.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": QUEUE_LOCKS[lane]}
            )
        holder.commit()
        try:
            yield holder
        finally:
            for lane in ("background", "interactive"):
                assert holder.scalar(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": QUEUE_LOCKS[lane]}
                )
            assert holder.scalar(
                text("SELECT pg_advisory_unlock_shared(:key)"), {"key": QUEUE_LOCKS["all"]}
            )


@contextmanager
def _maintenance(engine):
    with engine.connect() as holder:
        assert holder.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": SOURCE_MAINTENANCE_LOCK}
        )
        holder.commit()
        try:
            yield
        finally:
            assert holder.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": SOURCE_MAINTENANCE_LOCK}
            )


def _fixture_orphan(settings):
    raw = ("Disposable orphan " + uuid4().hex).encode()
    path = Path(settings.storage_root) / "originals" / (hashlib.sha256(raw).hexdigest() + ".txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    old = time.time() - 7200
    os.utime(path, (old, old))
    return path


@pytest.mark.parametrize("operation", ["ingest", "activate", "cleanup"])
def test_source_operations_complete_while_both_split_worker_lanes_are_held(runtime, operation):
    # Build an actual validated fixture release before simulating long-lived lanes.
    _document, release = corpus(runtime)
    orphan = _fixture_orphan(runtime.settings) if operation == "cleanup" else None
    with runtime.db() as db:
        owner = db.scalar(select(User.id).where(User.email == "admin@example.com"))
    with _split_workers(runtime.engine), runtime.db() as db:
        db.execute(text("SET LOCAL lock_timeout = '750ms'"))
        if operation == "ingest":
            raw = ("# New registration\nAuthored lock regression. " + uuid4().hex).encode()
            document, version, duplicate = service.ingest(
                db,
                runtime.settings,
                owner,
                "registration.txt",
                raw,
                "New registration fixture",
                "",
                "",
                "Authored fixture",
            )
            assert not duplicate and document.owner_id == owner
            assert version.raw_hash == hashlib.sha256(raw).hexdigest()
            db.commit()
        elif operation == "activate":
            actual = service.activate(db, release["release_id"])
            assert actual.id == release["release_id"] and actual.state == "active"
            db.commit()
        else:
            plan = cleanup_plan(db, runtime.settings)
            assert orphan.relative_to(Path(runtime.settings.storage_root)).as_posix() in {
                item["path"] for item in plan["candidates"]
            }
            assert apply_cleanup(db, runtime.settings, plan)["removed"] == 1
            assert not orphan.exists()


@pytest.mark.parametrize("operation", ["ingest", "activate", "cleanup"])
def test_source_operations_still_wait_for_the_shared_maintenance_transaction(runtime, operation):
    _document, release = corpus(runtime)
    orphan = _fixture_orphan(runtime.settings) if operation == "cleanup" else None
    with runtime.db() as db:
        owner = db.scalar(select(User.id).where(User.email == "admin@example.com"))
        before_documents = list(db.scalars(select(Document.id).order_by(Document.id)))
        before_versions = list(db.scalars(select(DocumentVersion.id).order_by(DocumentVersion.id)))
        plan = cleanup_plan(db, runtime.settings)
    before_files = {
        path.relative_to(Path(runtime.settings.storage_root)).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in Path(runtime.settings.storage_root).rglob("*")
        if path.is_file()
    }
    with _maintenance(runtime.engine), runtime.db() as db:
        db.execute(text("SET LOCAL lock_timeout = '150ms'"))
        with pytest.raises(DBAPIError) as error:
            if operation == "ingest":
                service.ingest(
                    db,
                    runtime.settings,
                    owner,
                    "blocked.txt",
                    ("A new registration " + uuid4().hex).encode(),
                    "Blocked fixture",
                    "",
                    "",
                    "Authored fixture",
                )
            elif operation == "activate":
                service.activate(db, release["release_id"])
            else:
                apply_cleanup(db, runtime.settings, plan)
        assert getattr(error.value.orig, "sqlstate", None) == "55P03"
        db.rollback()
    with runtime.db() as db:
        assert list(db.scalars(select(Document.id).order_by(Document.id))) == before_documents
        assert (
            list(db.scalars(select(DocumentVersion.id).order_by(DocumentVersion.id)))
            == before_versions
        )
    after_files = {
        path.relative_to(Path(runtime.settings.storage_root)).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in Path(runtime.settings.storage_root).rglob("*")
        if path.is_file()
    }
    assert after_files == before_files
    assert orphan is None or orphan.exists()


@pytest.fixture
def empty_import_settings(postgres_url, tmp_path, monkeypatch):
    """A second separately migrated fixture database, never a product installation."""
    from sqlalchemy.engine import make_url

    fixture_url = make_url(postgres_url)
    configured_server = make_url(
        os.environ.get(
            "TEST_DATABASE_SERVER",
            "postgresql+psycopg://learning:local-dev-database-only@127.0.0.1:55432",
        )
    )
    assert fixture_url.host in {"127.0.0.1", "localhost", "::1"}
    assert fixture_url.set(database="") == configured_server.set(database="")
    assert fixture_url.database.startswith("cs30_test_")
    name = "cs30_test_import_lock_" + uuid4().hex[:12]
    admin_url = fixture_url.set(database="postgres")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as db:
        db.execute(text(f'CREATE DATABASE "{name}"'))
    target = fixture_url.set(database=name)
    target_string = target.render_as_string(hide_password=False)
    try:
        with monkeypatch.context() as local:
            local.setenv("DATABASE_URL", target_string)
            command.upgrade(
                Config(str(Path(__file__).resolve().parents[2] / "backend/alembic.ini")), "head"
            )
        yield Settings(
            _env_file=None,
            env="test",
            model_mode="mock",
            llm_provider="mock",
            llm_api_key=None,
            database_url=target.update_query_dict(
                {"options": "-c lock_timeout=750ms"}
            ).render_as_string(hide_password=False),
            storage_root=str(tmp_path / "import-storage"),
        )
    finally:
        with admin.connect() as db:
            db.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def _authored_bundle(runtime, directory):
    """Build a labelled authored fixture bundle with real validated mock-corpus rows."""
    document, release = corpus(runtime)
    files = []
    queries = {}
    with runtime.db() as db:
        versions = list(
            db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document["id"]))
        )
        runs = list(
            db.scalars(
                select(ProcessingRun).where(
                    ProcessingRun.document_version_id.in_([version.id for version in versions])
                )
            )
        )
        run_ids = [run.id for run in runs]
        for model in corpus_bundle.TABLES:
            table = model.__table__
            query = select(table)
            if table.name == "documents":
                query = query.where(table.c.id == document["id"])
            elif table.name == "document_versions":
                query = query.where(table.c.document_id == document["id"])
            elif table.name == "processing_runs":
                query = query.where(table.c.id.in_(run_ids))
            elif table.name in {"source_units", "chunks"}:
                query = query.where(table.c.processing_id.in_(run_ids))
            elif table.name == "configurations":
                query = query.where(text("false"))
            elif table.name in {"corpus_releases", "release_chunks"}:
                key = table.c.id if table.name == "corpus_releases" else table.c.release_id
                query = query.where(key == release["release_id"])
            queries[table.name] = [dict(row) for row in db.execute(query).mappings()]
        for version in versions:
            relative = Path(version.storage_path)
            source = Path(runtime.settings.storage_root) / relative
            target = directory / "storage" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            files.append(
                {
                    "path": target.relative_to(directory).as_posix(),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "bytes": target.stat().st_size,
                }
            )
    data = directory / "corpus.jsonl.gz"
    with gzip.open(data, "wt", encoding="utf-8") as stream:
        for model in corpus_bundle.TABLES:
            for original in queries[model.__tablename__]:
                row = dict(original)
                if model is Document:
                    row.pop("owner_id")
                stream.write(
                    json.dumps(
                        {"table": model.__tablename__, "row": row}, default=corpus_bundle.json_value
                    )
                    + "\n"
                )
    manifest = {
        "schema": "official-corpus-bundle-v1",
        "fixture": "authored-test-only-not-OpenStax",
        "data": {"path": data.name, "sha256": hashlib.sha256(data.read_bytes()).hexdigest()},
        "files": files,
        "counts": {key: len(rows) for key, rows in queries.items()},
        "active_release_id": release["release_id"],
        "active_vector_count": len(queries["release_chunks"]),
    }
    (directory / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.mark.parametrize("held", ["workers", "maintenance"])
def test_corpus_import_uses_maintenance_lock_without_colliding_with_worker_lanes(
    runtime, empty_import_settings, tmp_path, monkeypatch, held
):
    source = tmp_path / "authored-bundle"
    source.mkdir()
    manifest = _authored_bundle(runtime, source)
    monkeypatch.setenv("CS30_PORTABLE_INITIAL_PASSWORD", "Disposable-test-import-password-123!")
    engine = create_engine(empty_import_settings.database_url)
    try:
        holding = _split_workers(engine) if held == "workers" else _maintenance(engine)
        with holding:
            if held == "workers":
                result = corpus_bundle.import_bundle(source, empty_import_settings)
                assert result["status"] == "passed"
                with Session(engine) as db:
                    assert (
                        db.scalar(select(func.count()).select_from(Document))
                        == manifest["counts"]["documents"]
                    )
            else:
                with pytest.raises(DBAPIError) as error:
                    corpus_bundle.import_bundle(source, empty_import_settings)
                assert getattr(error.value.orig, "sqlstate", None) == "55P03"
                with Session(engine) as db:
                    assert db.scalar(select(Document.id)) is None
                assert not list(Path(empty_import_settings.storage_root).rglob("*.txt"))
        # The original worker namespace and layout incompatibilities remain intact.
        assert QUEUE_LOCKS == {"all": 5703001, "interactive": 5703002, "background": 5703003}
        assert SOURCE_MAINTENANCE_LOCK not in QUEUE_LOCKS.values()
    finally:
        engine.dispose()
