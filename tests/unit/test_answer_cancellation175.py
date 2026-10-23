"""Local durable cancellation/accounting controls; no provider or real database."""

import threading
import time
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.modules.answering import cancellation, service
from app.modules.answering.models import AnswerRequest, Attempt, Job
from generation.types import RequestBudget


@pytest.fixture
def database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'owned-cancellation.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    for table in (AnswerRequest.__table__, Job.__table__, Attempt.__table__):
        table.create(engine)
    with Session(engine) as db:
        db.add(
            AnswerRequest(
                id="request",
                owner_id="synthetic-owner",
                route="/synthetic",
                idempotency_key="synthetic",
                body_hash="synthetic",
                mode="interactive_chat",
                response_schema="ChatResponseV1",
                state="processing",
                command={},
                trace={},
                budget=RequestBudget(consumed_calls=1).to_dict(),
            )
        )
        db.add(
            Job(
                id="job",
                request_id="request",
                owner_id="synthetic-owner",
                kind="answer",
                state="running",
                stage="generation",
                execution_token="token",
            )
        )
        db.commit()
    yield engine
    engine.dispose()


def wait_for(predicate, seconds=1):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        time.sleep(0.005)
    assert predicate()


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "cancelled", "execution_token": None},
        {"execution_token": "replacement-token"},
    ],
)
def test_fresh_read_observes_durable_stop_or_replaced_execution(database, changes):
    with cancellation.DurableCancellation(database, "job", "token", max_seconds=1) as observer:
        assert observer.cancelled.is_set() is False
        with Session(database) as db:
            db.execute(update(Job).where(Job.id == "job").values(**changes))
            db.commit()
        wait_for(observer.cancelled.is_set)
        assert observer.failure_type is None
    assert observer._thread.is_alive() is False
    with Session(database) as db:
        assert db.get(Job, "job").state == changes.get("state", "running")


def test_observer_closes_after_normal_generation_without_cancelling(database):
    with cancellation.DurableCancellation(database, "job", "token", max_seconds=1) as observer:
        time.sleep(0.03)
    assert observer._thread.is_alive() is False
    assert observer.cancelled.is_set() is False
    assert not any(thread.name == "answer-cancellation-job" for thread in threading.enumerate())


def test_observer_has_finite_lifetime_and_fails_closed_on_query_failure(database):
    with cancellation.DurableCancellation(database, "job", "token", max_seconds=0.02) as timed:
        wait_for(timed.cancelled.is_set)
    with cancellation.DurableCancellation(database, "absent-job", "token", max_seconds=1) as absent:
        wait_for(absent.cancelled.is_set)
    Job.__table__.drop(database)
    with cancellation.DurableCancellation(database, "job", "token", max_seconds=1) as failed:
        wait_for(failed.cancelled.is_set)
    assert failed.failure_type == "OperationalError"
    assert all(not item._thread.is_alive() for item in (timed, absent, failed))


def test_postgresql_observer_uses_dedicated_read_only_connection_with_timeouts(monkeypatch):
    calls = []
    watch_engine = SimpleNamespace(dispose=lambda: calls.append("disposed"))
    source = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"), url="synthetic-url")
    monkeypatch.setattr(
        cancellation,
        "create_engine",
        lambda *args, **kwargs: calls.append((args, kwargs)) or watch_engine,
    )
    monkeypatch.setattr(cancellation.DurableCancellation, "_observe", lambda self: None)
    with cancellation.DurableCancellation(source, "job", "token", max_seconds=1):
        pass
    args, kwargs = calls[0]
    assert args == ("synthetic-url",)
    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"] == {
        "connect_timeout": 1,
        "options": "-c statement_timeout=750 -c lock_timeout=250 -c default_transaction_read_only=on",
    }
    assert calls[-1] == "disposed"


def finish_event():
    return {
        "phase": "finish",
        "attempt_id": "request:attempt:1",
        "stage": "generation",
        "provider": "local",
        "model": "controlled-fixture",
        "request_submitted": True,
        "usage": {"input_tokens": None, "output_tokens": None, "cost": None},
        "budget": RequestBudget(consumed_calls=1, active_seconds=0.5).to_dict(),
        "error": {"code": "PROVIDER_CANCELLED", "retryable": False, "details": {"uncertain": True}},
        "diagnostic": {
            "request_submitted": True,
            "http_status": 200,
            "transport_cancellation": {"cleanup_confirmed": True, "child_exitcode": -15},
            "message": "private diagnostic text",
        },
        "raw_text": "private text",
        "raw_response": "private response",
        "messages": [{"content": "private prompt"}],
    }


def cancelled_start(database, *, token="token", stage="generation"):
    with Session(database) as db:
        db.execute(
            update(Job)
            .where(Job.id == "job")
            .values(state="cancelled", stage="cancelled", execution_token=None)
        )
        db.get(AnswerRequest, "request").state = "cancelled"
        db.add(
            Attempt(
                job_id="job",
                sequence=1,
                payload={
                    "phase": "start",
                    "attempt_id": "request:attempt:1",
                    "stage": stage,
                    "execution_token_sha256": service._execution_token_hash(token),
                },
            )
        )
        db.commit()


def test_cancelled_finish_preserves_unknown_usage_and_cleanup_then_aborts(database):
    cancelled_start(database)
    with Session(database) as db:
        with pytest.raises(service.ExecutionCancelled):
            service._lock_attempt_execution(db, "job", "token", finish_event())
    with Session(database) as db:
        job = db.get(Job, "job")
        request = db.get(AnswerRequest, "request")
        rows = list(db.scalars(select(Attempt).order_by(Attempt.sequence)))
        assert (job.state, job.stage, job.execution_token, job.answer_id) == (
            "cancelled",
            "cancelled",
            None,
            None,
        )
        assert request.state == "cancelled"
        assert request.budget["active_seconds"] == 0.5
        event = rows[-1].payload
        assert len(rows) == 2 and event["accounting_only"] is True
        assert event["request_submitted"] is True
        assert event["usage"] == {"input_tokens": None, "output_tokens": None, "cost": None}
        assert event["error"]["details"]["uncertain"] is True
        assert event["diagnostic"]["transport_cancellation"]["cleanup_confirmed"] is True
        assert not {"messages", "raw_text", "raw_response"} & event.keys()
        assert "message" not in event["diagnostic"]


@pytest.mark.parametrize("change", ["wrong-token", "wrong-stage", "new-start", "duplicate"])
def test_cancelled_accounting_cannot_invent_or_replay_an_attempt(database, change):
    cancelled_start(database, token="different" if change == "wrong-token" else "token")
    event = finish_event()
    if change == "wrong-stage":
        event["stage"] = "joint_check"
    if change == "new-start":
        event["phase"] = "start"
    with Session(database) as db:
        job, request = db.get(Job, "job"), db.get(AnswerRequest, "request")
        if change == "duplicate":
            assert service._preserve_cancelled_attempt_finish(db, job, request, "token", event)
            db.commit()
        count_before = len(list(db.scalars(select(Attempt))))
        assert service._preserve_cancelled_attempt_finish(db, job, request, "token", event) is False
        db.commit()
        assert len(list(db.scalars(select(Attempt)))) == count_before
        assert job.state == "cancelled" and request.state == "cancelled"


def test_late_finish_keeps_completed_usage_and_later_retry_budget(database):
    cancelled_start(database)
    event = finish_event()
    event["usage"] = {"input_tokens": 12, "output_tokens": 4, "cost": 0.01}
    with Session(database) as db:
        request = db.get(AnswerRequest, "request")
        later_budget = RequestBudget(
            consumed_calls=3, active_seconds=9, transient_retries=1
        ).to_dict()
        request.budget = deepcopy(later_budget)
        assert service._preserve_cancelled_attempt_finish(
            db, db.get(Job, "job"), request, "token", event
        )
        db.commit()
        assert request.budget == later_budget
        assert (
            list(db.scalars(select(Attempt).order_by(Attempt.sequence)))[-1].payload["usage"]
            == event["usage"]
        )


def test_session_lock_wait_refreshes_cached_request_before_merging_late_finish(
    database, monkeypatch
):
    cancelled_start(database)
    later_budget = RequestBudget(consumed_calls=3, active_seconds=9).to_dict()

    def later_retry_commits_before_lock_returns(db, request):
        assert request.budget["consumed_calls"] == 1
        with Session(database) as other:
            other.get(AnswerRequest, "request").budget = deepcopy(later_budget)
            other.commit()

    monkeypatch.setattr(service, "lock_request_session", later_retry_commits_before_lock_returns)
    with Session(database) as db:
        with pytest.raises(service.ExecutionCancelled):
            service._lock_attempt_execution(db, "job", "token", finish_event())
    with Session(database) as db:
        assert db.get(AnswerRequest, "request").budget == later_budget
