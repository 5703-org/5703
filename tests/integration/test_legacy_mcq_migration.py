"""Replay real PostgreSQL revisions without relabelling historical MCQ data.

0001_initial had account/session/outbox tables, not an answer table. The first
fixture preserves an MCQ-shaped outbox event without claiming that historical
schema contained answers. Typed MCQ rows are inserted only after 3ae1ba39fe7f
creates their actual tables, then preserved through subsequent upgrades.
"""

from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import MetaData, create_engine, select, text

from app.core.config import Settings
from app.core.security import hash_password
from app.main import create_app
from app.worker import run_once
from contracts.models import MCQResponseV1

ROOT = Path(__file__).resolve().parents[2]
INITIAL = "0001_initial"
ANSWER_TABLES = "3ae1ba39fe7f"


@pytest.fixture
def migration_database(monkeypatch):
    base = os.environ.get(
        "TEST_DATABASE_SERVER",
        "postgresql+psycopg://learning:local-dev-database-only@127.0.0.1:55432",
    ).rstrip("/")
    # Only a generated disposable name can enter these identifier statements.
    name = "cs30_migration_" + uuid4().hex
    assert name.startswith("cs30_migration_") and name.replace("_", "").isalnum()
    admin = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    engine = None
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        url = base + "/" + name
        monkeypatch.setenv("DATABASE_URL", url)
        engine = create_engine(url)
        assert engine.dialect.name == "postgresql"
        yield url, engine, Config(str(ROOT / "backend/alembic.ini"))
    finally:
        if engine:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def metadata(engine):
    result = MetaData()
    result.reflect(bind=engine)
    return result


def insert(connection, tables, table_name, **values):
    if "created_at" in tables[table_name].columns:
        now = datetime(2026, 9, 2, 1, 2, 3, tzinfo=timezone.utc)
        values = {"created_at": now, "updated_at": now, "version": 7, **values}
        values = {key: value for key, value in values.items() if key in tables[table_name].columns}
    connection.execute(tables[table_name].insert().values(**values))


def snapshot(engine, tables, names):
    with engine.connect() as connection:
        return {
            name: [
                dict(row)
                for row in connection.execute(
                    select(tables[name]).order_by(tables[name].c.id)
                ).mappings()
            ]
            for name in names
        }


def test_initial_data_and_typed_mcq_survive_additive_migrations(migration_database, tmp_path):
    url, engine, config = migration_database
    command.upgrade(config, INITIAL)
    assert not logging.getLogger("app.errors").disabled, (
        "Migrations disabled application error logging"
    )
    tables = metadata(engine).tables
    assert "answers" not in tables and "answer_requests" not in tables
    user_id, workspace_id, session_id = [str(uuid4()) for _ in range(3)]
    options = {
        "A": "  Original alpha  ",
        "B": "Original beta",
        "C": "Original gamma",
        "D": "Original delta",
    }
    response = {
        "question_id": "historical-question-001",
        "answer": "A",
        "answer_text": options["A"],
        "citations": ["ev_007"],
        "confidence": 0.75,
        "refused": False,
        "refusal_reason": None,
        "short_explanation": "Original explanation.",
    }
    legacy_event = {
        "mode": "benchmark_mcq",
        "response_schema": "mcq_response_v1",
        "options": options,
        "response": response,
    }
    with engine.begin() as connection:
        insert(
            connection,
            tables,
            "workspaces",
            id=workspace_id,
            name="Legacy workspace",
            slug="legacy-workspace",
            status="active",
        )
        insert(connection, tables, "roles", id=1, name="student", description="Legacy student")
        insert(
            connection,
            tables,
            "users",
            id=user_id,
            email="legacy@example.com",
            full_name="Legacy learner",
            hashed_password=hash_password("Passw0rd!"),
            status="active",
            role_id=1,
            workspace_id=workspace_id,
        )
        insert(
            connection,
            tables,
            "student_profiles",
            id=str(uuid4()),
            user_id=user_id,
            level="advanced",
            style="detailed",
            language="en",
            topics=["Original topic"],
        )
        insert(
            connection,
            tables,
            "sessions",
            id=session_id,
            user_id=user_id,
            workspace_id=workspace_id,
            title="Original MCQ session",
            status="active",
            deleted_at=None,
        )
        insert(
            connection,
            tables,
            "outbox_events",
            id=str(uuid4()),
            event_type="authored.legacy.mcq.completed",
            event_version="1",
            workspace_id=workspace_id,
            trace_id="preserve-this-trace",
            payload=legacy_event,
            status="delivered",
            attempts=2,
        )
    initial_names = [
        "workspaces",
        "roles",
        "users",
        "student_profiles",
        "sessions",
        "outbox_events",
    ]
    original = snapshot(engine, tables, initial_names)
    command.upgrade(config, ANSWER_TABLES)
    tables = metadata(engine).tables
    after = snapshot(engine, tables, initial_names)
    for name, rows in original.items():
        assert [{key: row[key] for key in rows[0]} for row in after[name]] == rows
    assert after["users"][0]["token_version"] == 1
    document_id = str(uuid4())
    evidence_text = "An authored historical source passage. Exact whitespace is retained."
    evidence_payload = {
        "evidence_id": "ev_007",
        "chunk_id": "legacy-chunk-17",
        "asset_id": document_id,
        "processing_id": "legacy-processing-9",
        "source_title": "Original evidence title",
        "source_url": "https://example.org/authored-source",
        "license": "Authored software fixture",
        "section": "Original section",
        "pages": [17],
        "locator": "Physical page 17",
        "text": evidence_text,
        "text_hash": hashlib.sha256(evidence_text.encode()).hexdigest(),
        "context_order": 1,
        "inherited_from": None,
    }
    answers = {}
    with engine.begin() as connection:
        insert(
            connection,
            tables,
            "documents",
            id=document_id,
            owner_id=user_id,
            title="Original evidence title",
            edition="authored-legacy",
            source_url=evidence_payload["source_url"],
            license=evidence_payload["license"],
            active=True,
            revoked=False,
        )
        for refused in [False, True]:
            request_id, job_id, answer_id = [str(uuid4()) for _ in range(3)]
            saved_response = (
                {
                    **response,
                    "question_id": "historical-refusal-002",
                    "answer": None,
                    "answer_text": None,
                    "citations": [],
                    "confidence": None,
                    "refused": True,
                    "refusal_reason": "NO_EVIDENCE",
                }
                if refused
                else response
            )
            MCQResponseV1.model_validate(saved_response)
            saved_command = {
                "mode": "benchmark_mcq",
                "question_id": saved_response["question_id"],
                "question_text": "Authored historical question?",
                "options": options,
            }
            insert(
                connection,
                tables,
                "answer_requests",
                id=request_id,
                owner_id=user_id,
                route="legacy/mcq",
                idempotency_key=str(uuid4()),
                body_hash="a" * 64,
                mode="benchmark_mcq",
                response_schema="mcq_response_v1",
                state="succeeded",
                command=saved_command,
                budget={"consumed_calls": 2, "active_seconds": 3.5},
                trace={"legacy_marker": "must-survive"},
            )
            insert(
                connection,
                tables,
                "jobs",
                id=job_id,
                request_id=request_id,
                owner_id=user_id,
                kind="answer",
                payload={},
                state="succeeded",
                stage="published",
                attempts=1,
                answer_id=answer_id,
            )
            insert(
                connection,
                tables,
                "answers",
                id=answer_id,
                request_id=request_id,
                job_id=job_id,
                response_schema="mcq_response_v1",
                response=saved_response,
                model_mode="mock",
                timing={"total_ms": 3500},
            )
            if not refused:
                evidence_id = str(uuid4())
                insert(
                    connection,
                    tables,
                    "evidence_snapshots",
                    id=evidence_id,
                    answer_id=answer_id,
                    evidence_id="ev_007",
                    document_id=document_id,
                    chunk_id="legacy-chunk-17",
                    payload=evidence_payload,
                )
                insert(
                    connection,
                    tables,
                    "citations",
                    id=str(uuid4()),
                    answer_id=answer_id,
                    evidence_id=evidence_id,
                )
            answers[answer_id] = saved_response
    preserved_names = initial_names + [
        "documents",
        "answer_requests",
        "jobs",
        "answers",
        "evidence_snapshots",
        "citations",
    ]
    before_later_migrations = snapshot(engine, tables, preserved_names)
    for _ in range(2):
        command.upgrade(config, "head")
        tables = metadata(engine).tables
        assert snapshot(engine, tables, preserved_names) == before_later_migrations

    settings = Settings(
        env="test",
        database_url=url,
        storage_root=str(tmp_path / "storage"),
        model_mode="mock",
        llm_provider="mock",
        mock_delay_seconds=0,
    )
    app = create_app(settings)
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login", json={"email": "legacy@example.com", "password": "Passw0rd!"}
            )
            assert login.status_code == 200
            headers = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}
            for answer_id, expected in answers.items():
                result = client.get("/api/v1/answers/" + answer_id, headers=headers)
                assert result.status_code == 200, result.text
                payload = result.json()["data"]
                assert payload["response_schema"] == "mcq_response_v1"
                assert payload["mode"] == "benchmark_mcq"
                assert payload["response"] == expected
                assert payload["can_regenerate"] is False
                assert "schema_version" not in payload["response"]
                if not expected["refused"]:
                    assert payload["evidence"] == [evidence_payload]
                    citation = client.get(
                        f"/api/v1/answers/{answer_id}/evidence/ev_007", headers=headers
                    )
                    assert citation.status_code == 200
                    assert citation.json()["data"] == evidence_payload
            receipt = client.post(
                f"/api/v1/sessions/{session_id}/messages",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={"content": "Hello", "use_profile": False},
            )
            assert receipt.status_code == 202, receipt.text
            assert run_once(app.state.engine, settings)
            job = client.get(
                "/api/v1/jobs/" + receipt.json()["data"]["job_id"], headers=headers
            ).json()["data"]
            assert job["state"] == "succeeded", job
            chat = client.get("/api/v1/answers/" + job["answer_id"], headers=headers).json()["data"]
            assert chat["mode"] == "interactive_chat"
            assert chat["response_schema"] == "chat_response_v1"
            assert chat["response"]["response_type"] == "social"
            assert "options" not in chat["response"] and "answer" not in chat["response"]
    finally:
        app.state.engine.dispose()
