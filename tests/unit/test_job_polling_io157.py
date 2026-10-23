"""Polling projections preserve ownership, mutation locks and explicit retry gates."""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import get_args

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppError
from app.modules.answering import router, service
from app.modules.answering.models import Answer, AnswerRequest, Job, Message
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession
from app.modules.knowledge import service as knowledge
from contracts.models import JobOut
from generation.types import RequestBudget


def actor(id="owner", role="learner", workspace="workspace"):
    return SimpleNamespace(id=id, role=SimpleNamespace(name=role), workspace_id=workspace)


def job(state="running", **changes):
    return SimpleNamespace(
        **{
            "id": "job",
            "owner_id": "owner",
            "request_id": "request",
            "state": state,
            "stage": "generating",
            "error": None,
            "answer_id": None,
            "created_at": datetime(2026, 10, 14, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 10, 14, tzinfo=timezone.utc),
            **changes,
        }
    )


def request(**changes):
    return SimpleNamespace(
        **{
            "id": "request",
            "trace": {},
            "command": {},
            "mode": "interactive_chat",
            "state": "error",
            "regeneration_of": None,
            "session_id": None,
            "user_message_id": "user-message",
            "budget": RequestBudget().to_dict(),
            **changes,
        }
    )


class PollSession:
    def __init__(self, row, owner=None, req=None):
        self.row = row
        self.owner = owner
        self.req = req
        self.statements = []
        self.reads = []

    def scalar(self, statement):
        self.statements.append(statement)
        return self.row

    def get(self, model, id):
        self.reads.append((model, id))
        if model is User:
            return self.owner
        if model is AnswerRequest:
            return self.req
        if model is Job:
            return self.row
        raise AssertionError(f"Unexpected metadata read: {model.__name__}")


def test_get_poll_projects_exact_dto_and_frozen_mode_without_full_request_read():
    db = PollSession(job())
    result = router.job("job", db=db, actor=actor())
    assert JobOut.model_validate(result["data"]).can_retry is False
    assert db.reads == []
    assert len(db.statements) == 1
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert {column.keyname for column in compiled._result_columns} == {
        "id",
        "owner_id",
        "request_id",
        "state",
        "stage",
        "error",
        "answer_id",
        "created_at",
        "updated_at",
        "verification_mode",
    }
    assert "LEFT OUTER JOIN answer_requests" in str(compiled)
    assert "answer_requests.command ->>" in str(compiled)
    assert "jobs.id =" in str(compiled)
    assert sorted(compiled.params.values()) == ["job", "verification_mode"]


@pytest.mark.parametrize("state", ["queued", "running", "retry_wait", "succeeded"])
def test_non_retryable_poll_states_never_read_request_or_evaluate_retry(state, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An active or successful poll evaluated retry eligibility")

    monkeypatch.setattr(service, "can_retry", forbidden)
    db = PollSession(job(state))
    output = JobOut.model_validate(service.job_out(db, db.row))
    assert output.state == state
    assert output.can_retry is False
    assert db.reads == []


def test_all_contract_job_states_are_covered_by_poll_or_terminal_controls():
    assert set(get_args(JobOut.model_fields["state"].annotation)) == {
        "queued",
        "running",
        "retry_wait",
        "succeeded",
        "failed",
        "cancelled",
    }


@pytest.mark.parametrize("state", ["failed", "cancelled"])
@pytest.mark.parametrize("eligible", [False, True])
def test_terminal_poll_delegates_to_full_retry_validator(state, eligible, monkeypatch):
    req = request(state="cancelled" if state == "cancelled" else "error")
    db = PollSession(job(state), req=req)
    calls = []

    def validate_retry(current_db, current_request):
        calls.append((current_db, current_request))
        return eligible

    monkeypatch.setattr(service, "can_retry", validate_retry)
    assert service.job_out(db, db.row)["can_retry"] is eligible
    assert db.reads == [(AnswerRequest, "request")]
    assert calls == [(db, req)]


@pytest.mark.parametrize("state", ["failed", "cancelled"])
def test_terminal_poll_with_missing_request_remains_non_retryable(state):
    db = PollSession(job(state))
    assert service.job_out(db, db.row)["can_retry"] is False
    assert db.reads == [(AnswerRequest, "request")]


@pytest.mark.parametrize(
    "viewer,owner,allowed",
    [
        (actor(), None, True),
        (actor("other"), actor(), False),
        (actor("admin", "admin"), actor(), True),
        (actor("admin", "admin"), actor(workspace="other-workspace"), False),
        (actor("admin", "admin"), None, False),
    ],
)
def test_projected_poll_retains_existing_owner_and_workspace_authorization(viewer, owner, allowed):
    db = PollSession(job(), owner=owner)
    if allowed:
        assert service.job_owned(db, "job", viewer, metadata_only=True) is db.row
    else:
        with pytest.raises(AppError, match="NOT_FOUND"):
            service.job_owned(db, "job", viewer, metadata_only=True)
    assert all(model is User for model, _ in db.reads)


def test_projected_poll_hides_missing_job():
    with pytest.raises(AppError, match="NOT_FOUND"):
        service.job_owned(PollSession(None), "missing", actor(), metadata_only=True)


def test_default_job_lookup_retains_full_mutation_object():
    complete = job(payload={"saved": "payload"}, execution_token="token", worker_id="worker")
    db = PollSession(complete)
    assert service.job_owned(db, "job", actor()) is complete
    assert db.reads == [(Job, "job")]
    assert db.statements == []
    assert complete.payload == {"saved": "payload"}


def test_terminal_poll_keeps_current_source_failure_gate(monkeypatch):
    db = PollSession(job("failed"), req=request())

    def revoked(current_db, current_request):
        raise AppError("SOURCE_UNAVAILABLE")

    monkeypatch.setattr(service, "validate_learning_context", revoked)
    assert service.job_out(db, db.row)["can_retry"] is False
    assert db.statements == []


def test_terminal_poll_keeps_exhausted_request_budget_gate(monkeypatch):
    db = PollSession(job("failed"), req=request(budget=RequestBudget(consumed_calls=4).to_dict()))
    monkeypatch.setattr(service, "validate_learning_context", lambda *args: None)
    db.scalar = lambda statement: None
    assert service.job_out(db, db.row)["can_retry"] is False


def test_terminal_poll_keeps_active_session_job_gate(monkeypatch):
    db = PollSession(job("failed"), req=request(session_id="session"))
    original_get = db.get
    db.get = lambda model, id: (
        SimpleNamespace(status="active", deleted_at=None)
        if model is ChatSession
        else original_get(model, id)
    )
    monkeypatch.setattr(service, "validate_learning_context", lambda *args: None)
    monkeypatch.setattr(service, "tail_user", lambda *args: SimpleNamespace(id="user-message"))
    monkeypatch.setattr(service, "active_job", lambda *args: job())
    assert service.job_out(db, db.row)["can_retry"] is False
    assert db.statements == []


def test_cancel_keeps_full_job_and_parent_before_job_lock_order(monkeypatch):
    row = job(payload={"saved": "payload"}, execution_token="token", kind="answer")
    req = request(session_id="session")
    message = SimpleNamespace(state="queued")
    db = PollSession(row, req=req)
    events = []
    original_get = db.get

    def get(model, id):
        events.append(("get", model.__name__))
        return message if model is Message else original_get(model, id)

    def lock_parent(statement):
        compiled = statement.compile(dialect=postgresql.dialect())
        assert "sessions.id =" in str(compiled)
        assert "FOR UPDATE" in str(compiled)
        events.append(("lock", "session"))
        return SimpleNamespace(id="session")

    def lock_job(current, *, with_for_update):
        assert current is row and with_for_update is True
        assert current.payload == {"saved": "payload"}
        events.append(("lock", "job"))

    db.get = get
    db.scalar = lock_parent
    db.refresh = lock_job
    db.flush = lambda: events.append(("flush", "cancel"))
    db.commit = lambda: events.append(("commit", "cancel"))
    monkeypatch.setattr(knowledge, "mark_operation_interrupted", lambda *args: None)
    monkeypatch.setattr(service, "can_retry", lambda current_db, current_req: False)
    output = router.cancel("job", db=db, actor=actor())
    assert JobOut.model_validate(output["data"]).state == "cancelled"
    assert row.execution_token is None
    assert req.state == message.state == "cancelled"
    assert events.index(("lock", "session")) < events.index(("lock", "job"))
    assert events[0] == ("get", "Job")
    assert row.payload == {"saved": "payload"}


def test_job_route_preserves_canonical_response_contract():
    import json
    from pathlib import Path
    from fastapi import FastAPI

    # Router schema generation has no application startup, Engine or transport.
    app = FastAPI()
    app.include_router(router.router, prefix="/api/v1")
    generated = app.openapi()
    canonical = json.loads(
        (Path(__file__).resolve().parents[2] / "contracts/openapi.json").read_text("utf-8")
    )
    assert (
        generated["components"]["schemas"]["JobOut"] == canonical["components"]["schemas"]["JobOut"]
    )
    assert (
        generated["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]["200"]
        == canonical["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]["200"]
    )
