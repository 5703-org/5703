"""Diagnostics expose actionable workspace records without private transport data."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.cli import seed
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.main import create_app
from app.modules.answering.models import Answer, AnswerRequest, Attempt, Evidence, Job
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge.models import Document
from app.modules.learning.models import ChatSession

SECRET = "private-provider-credential-must-not-be-returned"
ROOT = "/api/v1/admin/failures"


@pytest.fixture
def diagnosis(tmp_path):
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="sqlite:///" + str(tmp_path / "diagnostics.db"),
        jwt_secret="diagnostics-test-secret-at-least-thirty-two",
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
        workspace = Workspace(name="Foreign", slug="foreign")
        db.add(workspace)
        db.flush()
        db.add(
            User(
                email="foreign@example.com",
                full_name="Foreign admin",
                hashed_password=hash_password("Passw0rd!"),
                role_id=db.scalar(select(Role.id).where(Role.name == "admin")),
                workspace_id=workspace.id,
            )
        )
        db.commit()
    client = TestClient(app)

    def headers(email="admin@example.com"):
        result = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert result.status_code == 200
        return {"Authorization": "Bearer " + result.json()["data"]["access_token"]}

    def record(email="student@example.com", state="refused", deleted=False, traced=True):
        with factory() as db:
            owner = db.scalar(select(User).where(User.email == email))
            session = ChatSession(
                user_id=owner.id,
                workspace_id=owner.workspace_id,
                title="A diagnosis fixture",
                deleted_at=datetime.now(timezone.utc) if deleted else None,
            )
            db.add(session)
            db.flush()
            req = AnswerRequest(
                owner_id=owner.id,
                session_id=session.id,
                route="fixture",
                idempotency_key=uuid4().hex,
                body_hash="0" * 64,
                mode="interactive_chat",
                response_schema="chat_response_v1",
                state=state,
                command={
                    "question": "Why does water move across a membrane?",
                    "model_config": {
                        "provider": "openai_compatible",
                        "model": "fixture",
                        "api_key": SECRET,
                    },
                    "private_gold": SECRET,
                },
                trace={"private_prompt": SECRET},
                budget={"consumed_calls": 1, "raw_error": SECRET},
            )
            if traced:
                req.trace = {
                    **req.trace,
                    "prepared_query": {"intent": "new_question", "retrieval_query": "osmosis"},
                    "evidence_selection": {
                        "candidate_count": 5,
                        "submitted_count": 2,
                        "cited_count": 1,
                        "candidate_chunk_ids": ["c1", "c2", "c3", "c4", "c5"],
                    },
                }
            db.add(req)
            db.flush()
            job = Job(
                request_id=req.id,
                owner_id=owner.id,
                state="failed" if state == "error" else "succeeded",
                stage="generation",
                error={"code": "PROVIDER_AUTH_ERROR", "message": SECRET, "raw_body": SECRET}
                if state == "error"
                else None,
            )
            db.add(job)
            db.flush()
            db.add(
                Attempt(
                    job_id=job.id,
                    sequence=1,
                    payload={
                        "stage": "generation",
                        "phase": "initial",
                        "latency_ms": 12,
                        "raw_body": SECRET,
                        "error": {"code": "PROVIDER_AUTH_ERROR", "message": SECRET},
                    },
                )
            )
            if state != "error":
                answer = Answer(
                    request_id=req.id,
                    job_id=job.id,
                    response_schema="chat_response_v1",
                    response={
                        "response_type": "answer",
                        "answer_text": "Water moves down its water potential gradient.",
                        "citations": ["ev1"],
                    },
                    model_mode="mock",
                )
                db.add(answer)
                document = Document(owner_id=owner.id, title="Authored diagnostic fixture")
                db.add(document)
                db.flush()
                for index in (1, 2):
                    db.add(
                        Evidence(
                            answer_id=answer.id,
                            evidence_id=f"ev{index}",
                            document_id=document.id,
                            chunk_id=f"c{index}",
                            payload={"text": "Authored transport fixture"},
                        )
                    )
            db.commit()
            return req.id

    yield SimpleNamespace(client=client, headers=headers, record=record)
    client.close()
    app.state.engine.dispose()


def test_diagnostics_scope_and_permissions(diagnosis):
    runtime = diagnosis
    visible = runtime.record()
    foreign = runtime.record(email="foreign@example.com")
    deleted = runtime.record(deleted=True)
    assert runtime.client.get(ROOT).status_code == 401
    assert (
        runtime.client.get(ROOT, headers=runtime.headers("student@example.com")).status_code == 403
    )
    response = runtime.client.get(ROOT, headers=runtime.headers())
    assert response.status_code == 200
    assert [row["request_id"] for row in response.json()["data"]["items"]] == [visible]
    for request_id in (foreign, deleted, "missing"):
        assert (
            runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers()).status_code == 404
        )


def test_actual_citations_and_distinct_evidence_counts(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(state="answered")
    assert runtime.client.get(ROOT, headers=runtime.headers()).json()["data"]["total"] == 0
    response = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert response.status_code == 200
    row = response.json()["data"]
    assert row["counts"] == {"candidates": 5, "submitted": 2, "cited": 1}
    assert row["evidence"] == {
        "candidate_chunk_ids": ["c1", "c2", "c3", "c4", "c5"],
        "submitted_chunk_ids": ["c1", "c2"],
        "cited_chunk_ids": ["c1"],
    }
    assert row["retrieval_query"] == "osmosis"
    assert SECRET not in response.text
    assert row["budget"] == {"consumed_calls": 1}


def test_unrecorded_counts_remain_unknown_and_errors_are_safe(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(state="error", traced=False)
    response = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert response.status_code == 200
    row = response.json()["data"]
    assert row["counts"] == {"candidates": None, "submitted": None, "cited": None}
    assert SECRET not in response.text
    assert row["error_message"]
    assert row["attempts"][0]["error_code"] == "PROVIDER_AUTH_ERROR"
    assert row["evidence"] == {
        "candidate_chunk_ids": [],
        "submitted_chunk_ids": [],
        "cited_chunk_ids": [],
    }


def test_paginated_failure_list(diagnosis):
    runtime = diagnosis
    ids = {runtime.record(), runtime.record(state="error"), runtime.record(state="answered")}
    first = runtime.client.get(
        ROOT, params={"state": "all", "limit": 2}, headers=runtime.headers()
    ).json()["data"]
    second = runtime.client.get(
        ROOT, params={"state": "all", "limit": 2, "offset": 2}, headers=runtime.headers()
    ).json()["data"]
    assert first["total"] == second["total"] == 3
    assert {row["request_id"] for row in first["items"] + second["items"]} == ids
    assert (
        runtime.client.get(ROOT, params={"limit": 101}, headers=runtime.headers()).status_code
        == 422
    )
