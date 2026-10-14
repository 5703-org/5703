"""Real PostgreSQL downgrades must preserve populated additive learning records."""

from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.cli import seed
from app.modules.identity.models import User
from app.modules.knowledge.models import CorpusRelease, Document
from app.modules.learning_product.models import StudyConceptRelation, StudyNote


@contextmanager
def isolated_schema(postgres_url, monkeypatch, revision):
    server = postgres_url.rsplit("/", 1)[0]
    name = "cs30_test_" + uuid4().hex[:12]
    admin = create_engine(server + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {name}"))
    engine = create_engine(server + "/" + name)
    config = Config(str(Path(__file__).resolve().parents[2] / "backend/alembic.ini"))
    monkeypatch.setenv("DATABASE_URL", server + "/" + name)
    try:
        command.upgrade(config, revision)
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            seed(db)
        yield engine, config
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f"DROP DATABASE {name}"))
        admin.dispose()


def rows(engine, table):
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings()
        ]


def head(engine):
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def test_personal_review_upgrade_and_refused_downgrade_preserve_saved_note(
    postgres_url, monkeypatch
):
    with isolated_schema(postgres_url, monkeypatch, "f4a18bc67d20") as (engine, config):
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            owner = db.scalar(select(User).where(User.email == "student@example.com"))
            db.add(
                StudyNote(
                    owner_id=owner.id,
                    title="Migration preservation fixture",
                    content="Saved source-independent card.",
                    kind="review_card",
                    concepts=["fixture"],
                )
            )
            db.commit()
        note_before = rows(engine, "study_notes")
        command.upgrade(config, "f5b61c9247de")
        queue_before = rows(engine, "study_review_entries")
        assert len(queue_before) == 1 and queue_before[0]["note_id"] == note_before[0]["id"]
        assert rows(engine, "study_notes") == note_before
        with pytest.raises(RuntimeError, match="Remove personal review-card queue entries"):
            command.downgrade(config, "f4a18bc67d20")
        assert head(engine) == "f5b61c9247de"
        assert rows(engine, "study_notes") == note_before
        assert rows(engine, "study_review_entries") == queue_before
        # A deliberate test-only removal of the queue permits the documented rollback.
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM study_review_entries WHERE note_id IS NOT NULL"))
        command.downgrade(config, "f4a18bc67d20")
        assert head(engine) == "f4a18bc67d20" and rows(engine, "study_notes") == note_before
        command.upgrade(config, "f5b61c9247de")
        assert len(rows(engine, "study_review_entries")) == 1
        assert rows(engine, "study_notes") == note_before


def test_relation_downgrade_preserves_proposals_and_allows_empty_table(postgres_url, monkeypatch):
    with isolated_schema(postgres_url, monkeypatch, "f6c72db859ae") as (engine, config):
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            actor = db.scalar(select(User).where(User.email == "admin@example.com"))
            document = Document(title="Migration-only labelled source fixture", owner_id=actor.id)
            release = CorpusRelease(
                name="Unpublished migration fixture", configuration={}, manifest={}
            )
            db.add_all([document, release])
            db.flush()
            db.add(
                StudyConceptRelation(
                    workspace_id=actor.workspace_id,
                    document_id=document.id,
                    release_id=release.id,
                    from_section_id="fixture-a",
                    to_section_id="fixture-b",
                    from_concept="fixture a",
                    to_concept="fixture b",
                    relation_type="related",
                    source={},
                    source_quote="Migration-only fixture",
                    source_quote_hash="0" * 64,
                    reason="Preserve proposed records during refused rollback.",
                    state="proposed",
                    proposer_id=actor.id,
                )
            )
            db.commit()
        relation_before = rows(engine, "study_concept_relations")
        documents_before = rows(engine, "documents")
        with pytest.raises(RuntimeError, match="Preserve reviewed concept relation records"):
            command.downgrade(config, "f5b61c9247de")
        assert head(engine) == "f6c72db859ae"
        assert rows(engine, "study_concept_relations") == relation_before
        assert rows(engine, "documents") == documents_before
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM study_concept_relations"))
        command.downgrade(config, "f5b61c9247de")
        assert head(engine) == "f5b61c9247de"
        assert rows(engine, "documents") == documents_before
        command.upgrade(config, "f6c72db859ae")
        assert rows(engine, "study_concept_relations") == []
