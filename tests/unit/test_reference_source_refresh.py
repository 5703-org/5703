"""Reference retrieval rechecks live sources without discarding local changes."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401 -- register portable fixture metadata
from app.core.exceptions import AppError
from app.db.base import Base
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge import service
from app.modules.knowledge.models import (
    Chunk,
    Configuration,
    CorpusRelease,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
    SourceUnit,
)

QUERY = "photosynthesis light"
AUTHORED_SOURCE = (
    b"# Photosynthesis\nPhotosynthesis captures light energy and stores chemical "
    b"energy in sugars. Light supplies energy to convert carbon dioxide and "
    b"water into sugars. Oxygen is released.\n\n# Diffusion\nDiffusion is the net "
    b"movement of particles from higher concentration to lower concentration. "
    b"Dye spreading through water is an example."
)


@pytest.fixture
def source_fixture(tmp_path):
    """Use normal producers and mock vectors in a new, local-only SQLite file."""
    engine = create_engine("sqlite:///" + str(tmp_path / "source-refresh.sqlite"))
    try:
        Base.metadata.create_all(engine)
        settings = SimpleNamespace(storage_root=str(tmp_path / "storage"), max_upload_bytes=8192)
        with Session(engine, expire_on_commit=False) as db:
            workspace = Workspace(name="Source refresh fixture", slug="source-refresh")
            role = Role(name="admin")
            db.add_all([workspace, role])
            db.flush()
            owner = User(
                email="source-refresh@example.com",
                full_name="Authored administrator",
                hashed_password="unused-authored-test-value",
                role_id=role.id,
                workspace_id=workspace.id,
            )
            db.add(owner)
            db.flush()
            document, version, duplicate = service.ingest(
                db,
                settings,
                owner.id,
                "authored-biology.txt",
                AUTHORED_SOURCE,
                "Authored source refresh biology",
                license="Authored fixture",
            )
            assert not duplicate
            processing, _ = service.queue_process(db, document.id, owner.id)
            db.commit()
            service.execute_processing(db, settings, processing.id)
            assert db.get(ProcessingRun, processing.id).state == "ready"
            release, _ = service.queue_release(db, owner.id, [processing.id])
            db.commit()
            service.execute_release(db, release.id)
            service.activate(db, release.id)
            db.commit()
            assert release.configuration["embedding_provider"] == "mock"
            assert release.configuration["embedding_revision"] == "mock-hash-v1"
            ids = {
                "document": document.id,
                "version": version.id,
                "processing": processing.id,
                "release": release.id,
                "owner": owner.id,
            }
        yield SimpleNamespace(engine=engine, ids=ids)
    finally:
        engine.dispose()


def retained_sources(db, ids):
    # SQLAlchemy's identity map holds weak references. Keep all previously read
    # entities alive to exercise stale identities rather than a fresh read.
    return {
        "document": db.get(Document, ids["document"]),
        "version": db.get(DocumentVersion, ids["version"]),
        "processing": db.get(ProcessingRun, ids["processing"]),
        "release": db.get(CorpusRelease, ids["release"]),
        "chunks": list(db.scalars(select(Chunk))),
        "units": list(db.scalars(select(SourceUnit))),
        "vectors": list(db.scalars(select(ReleaseChunk))),
    }


def assert_current_boundary(db, ids, variant, mutation):
    if mutation in ("deactivate", "revoke"):
        assert service.retrieve(db, QUERY, ids["release"], variant, 5) == []
    else:
        with pytest.raises(AppError) as error:
            service.retrieve(db, QUERY, ids["release"], variant, 5)
        assert error.value.code == "SOURCE_UNAVAILABLE"


@pytest.mark.parametrize("variant", ["R1", "R0"])
@pytest.mark.parametrize("mutation", ["deactivate", "revoke", "chunk_text", "processing_state"])
def test_reference_retrieval_refreshes_independently_changed_sources(
    source_fixture, variant, mutation
):
    engine, ids = source_fixture.engine, source_fixture.ids
    with Session(engine, expire_on_commit=False) as holding:
        retained = retained_sources(holding, ids)
        assert service.retrieve(holding, QUERY, ids["release"], variant, 5)
        holding.commit()
        with Session(engine) as changing:
            if mutation in ("deactivate", "revoke"):
                source = changing.get(Document, ids["document"])
                source.active = False
                source.revoked = mutation == "revoke"
                source.version += 1
            elif mutation == "chunk_text":
                chunk = changing.get(Chunk, retained["chunks"][0].id)
                chunk.text = "Changed fixture text; original hash retained."
            else:
                changing.get(ProcessingRun, ids["processing"]).state = "failed"
            changing.commit()
        # A new Session establishes that the mutation changes the original
        # validation result; the retained Session must reach the same boundary.
        with Session(engine) as fresh:
            assert_current_boundary(fresh, ids, variant, mutation)
        assert_current_boundary(holding, ids, variant, mutation)
        assert retained["document"] is holding.get(Document, ids["document"])


@pytest.mark.parametrize("variant", ["R1", "R0"])
@pytest.mark.parametrize("autoflush", [True, False])
def test_reference_refresh_flushes_local_changes_without_committing(
    source_fixture, variant, autoflush
):
    engine, ids = source_fixture.engine, source_fixture.ids
    with Session(engine, expire_on_commit=False, autoflush=autoflush) as holding:
        retained = retained_sources(holding, ids)
        owner = holding.get(User, ids["owner"])
        assert service.retrieve(holding, QUERY, ids["release"], variant, 5)
        holding.commit()
        original_name = owner.full_name
        retained["document"].active = False
        owner.full_name = "Local pending administrator change"
        pending = Configuration(
            kind="authored_fixture",
            name="Uncommitted source refresh control",
            values={"authored": True},
            content_hash=service.digest({"authored_source_refresh_control": True}),
        )
        holding.add(pending)

        assert service.retrieve(holding, QUERY, ids["release"], variant, 5) == []
        assert pending.id is not None
        assert (
            holding.scalar(select(User.full_name).where(User.id == ids["owner"]))
            == "Local pending administrator change"
        )
        assert (
            holding.scalar(select(Document.active).where(Document.id == ids["document"])) is False
        )
        assert (
            holding.scalar(select(Configuration.name).where(Configuration.id == pending.id))
            == pending.name
        )

        # Refresh may flush inside the existing transaction, but must neither
        # commit the caller's changes nor discard their ability to roll back.
        holding.rollback()
    with Session(engine) as fresh:
        assert fresh.get(Document, ids["document"]).active is True
        assert fresh.get(User, ids["owner"]).full_name == original_name
        assert fresh.get(Configuration, pending.id) is None
        assert service.retrieve(fresh, QUERY, ids["release"], variant, 5)
