"""Deterministic real-PostgreSQL cancellation races with no provider invocation."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import func, select, text

from app.modules.answering import service
from app.modules.answering.models import Answer, AnswerRequest, Attempt, Job, Message, Snapshot

from .test_chat_runtime import call, corpus, finish, session, submit


def row_states(rt, receipt):
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        req = db.get(AnswerRequest, receipt["request_id"])
        message = db.get(Message, req.user_message_id)
        return {
            "job": job.state,
            "stage": job.stage,
            "request": req.state,
            "message": message.state,
            "execution_token": job.execution_token,
            "answer_id": job.answer_id,
            "assistant_message_id": req.assistant_message_id,
            "trace": deepcopy(req.trace),
            "attempts": db.scalar(
                select(func.count()).select_from(Attempt).where(Attempt.job_id == job.id)
            ),
            "answers": db.scalar(
                select(func.count()).select_from(Answer).where(Answer.request_id == req.id)
            ),
            "active_job": service.active_job(db, req.session_id) is not None,
        }


def test_cancel_committed_after_initial_identity_read_stops_before_preparation(
    runtime, monkeypatch
):
    rt = runtime
    corpus(rt)
    conversation = session(rt)
    receipt = submit(rt, conversation)
    headers = rt.headers()
    token = str(uuid4())
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        job.state, job.execution_token = "running", token
        db.commit()
        original_trace = deepcopy(db.get(AnswerRequest, receipt["request_id"]).trace)
    initial_read, cancellation_committed = Event(), Event()
    observation = {}
    validate = service.validate_learning_context
    cancel = service.cancel_job

    def pause_before_job_lock(db, req, *, lock=False):
        if req.id == receipt["request_id"] and lock and not initial_read.is_set():
            cached_job = db.get(Job, receipt["job_id"])
            assert cached_job.state == "running" and cached_job.execution_token == token
            observation["worker_backend_pid"] = db.scalar(text("SELECT pg_backend_pid()"))
            initial_read.set()
            assert cancellation_committed.wait(15), "Owner cancellation did not finish"
            # It is deliberately the same stale ORM object, not a fresh query.
            assert cached_job.state == "running" and cached_job.execution_token == token
        return validate(db, req, lock=lock)

    def observe_owner_cancel(db, job):
        if job.id == receipt["job_id"]:
            observation["cancel_backend_pid"] = db.scalar(text("SELECT pg_backend_pid()"))
        return cancel(db, job)

    monkeypatch.setattr(service, "validate_learning_context", pause_before_job_lock)
    monkeypatch.setattr(service, "cancel_job", observe_owner_cancel)

    def execute():
        try:
            return service.execute_answer(rt.engine, rt.settings, receipt["job_id"], token)
        except service.ExecutionCancelled:
            return "late_cancellation_guard"

    with (
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieval,
        patch.object(service.GenerationService, "generate") as generation,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        worker = pool.submit(execute)
        assert initial_read.wait(15), "Worker did not reach the initial cached-read boundary"
        try:
            cancelled = call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {}, headers)
            assert cancelled["state"] == "cancelled"
            before_resume = row_states(rt, receipt)
            assert (
                before_resume["job"]
                == before_resume["request"]
                == before_resume["message"]
                == ("cancelled")
            )
        finally:
            cancellation_committed.set()
        observation["worker_result"] = worker.result(timeout=20)
        observation["retrieval_calls"] = retrieval.call_count
        observation["generation_calls"] = generation.call_count
    after = row_states(rt, receipt)
    observation["after"] = after
    print("CANCEL_RACE_OBSERVATION", observation)
    assert observation["worker_backend_pid"] != observation["cancel_backend_pid"]
    assert after["job"] == after["request"] == after["message"] == "cancelled"
    assert after["stage"] == "cancelled"
    assert after["execution_token"] is None
    assert after["trace"] == original_trace
    assert after["answer_id"] is None and after["assistant_message_id"] is None
    assert after["attempts"] == after["answers"] == 0 and after["active_job"] is False
    assert observation["retrieval_calls"] == observation["generation_calls"] == 0
    page = call(rt, "GET", "/sessions/" + conversation["id"] + "/messages", headers=headers)
    assert len(page["items"]) == 1 and page["items"][0]["state"] == "cancelled"


def test_owner_repeated_cancel_reconciles_latest_unanswered_orphan_once(runtime):
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        job = db.get(Job, receipt["job_id"])
        message = db.get(Message, req.user_message_id)
        req.state, message.state, job.stage = "processing", "processing", "preparing"
        req.trace = {**req.trace, "retained_fixture_marker": "orphan_reproduction"}
        before = {
            "command": deepcopy(req.command),
            "budget": deepcopy(req.budget),
            "context": deepcopy(db.get(Snapshot, req.context_snapshot_id).payload),
        }
        db.commit()
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    observed = row_states(rt, receipt)
    assert observed["job"] == observed["request"] == observed["message"] == "cancelled"
    assert observed["stage"] == "cancelled"
    assert observed["execution_token"] is None and observed["answers"] == 0
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        job = db.get(Job, receipt["job_id"])
        assert req.command == before["command"] and req.budget == before["budget"]
        assert db.get(Snapshot, req.context_snapshot_id).payload == before["context"]
        assert req.trace["retained_fixture_marker"] == "orphan_reproduction"
        assert req.trace.get("terminal_state_reconciliation")
        stable = deepcopy(req.trace), req.updated_at, job.updated_at
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        job = db.get(Job, receipt["job_id"])
        assert (req.trace, req.updated_at, job.updated_at) == stable


def test_cancelling_old_job_does_not_cancel_current_retry_or_change_frozen_inputs(runtime):
    rt = runtime
    conversation = session(rt)
    original = submit(rt, conversation, "Hello")
    call(rt, "POST", "/jobs/" + original["job_id"] + "/cancel", {})
    retry_headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    current = call(
        rt,
        "POST",
        "/answer-requests/" + original["request_id"] + "/retry",
        {},
        retry_headers,
        202,
    )
    with rt.db() as db:
        req = db.get(AnswerRequest, current["request_id"])
        before = deepcopy(req.command), deepcopy(req.budget), deepcopy(req.trace), req.updated_at
    call(rt, "POST", "/jobs/" + original["job_id"] + "/cancel", {})
    observed = row_states(rt, current)
    assert observed["job"] == observed["request"] == observed["message"] == "queued"
    with rt.db() as db:
        req = db.get(AnswerRequest, current["request_id"])
        assert (req.command, req.budget, req.trace, req.updated_at) == before
    finished = finish(rt, current)
    assert finished["response"]["response_type"] == "social"
    call(rt, "POST", "/jobs/" + original["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, current["request_id"])
        assert req.state == "answered"
        assert db.get(Message, req.user_message_id).state == "completed"
        assert db.get(Message, req.assistant_message_id).active_answer_id == finished["id"]
    assert call(rt, "GET", "/jobs/" + original["job_id"])["state"] == "cancelled"


def test_regeneration_cancel_preserves_existing_answer_and_successful_messages(runtime):
    rt = runtime
    conversation = session(rt)
    original = finish(rt, submit(rt, conversation, "Hello"))
    regeneration = call(
        rt,
        "POST",
        "/answers/" + original["id"] + "/regenerate",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    call(rt, "POST", "/jobs/" + regeneration["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, regeneration["request_id"])
        message = db.get(Message, req.user_message_id)
        assistant = db.get(Message, req.assistant_message_id)
        before = message.state, assistant.state, assistant.active_answer_id, deepcopy(req.trace)
    call(rt, "POST", "/jobs/" + regeneration["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, regeneration["request_id"])
        message = db.get(Message, req.user_message_id)
        assistant = db.get(Message, req.assistant_message_id)
        assert (message.state, assistant.state, assistant.active_answer_id, req.trace) == before
        assert message.state == assistant.state == "completed"
        assert assistant.active_answer_id == original["id"]
        assert db.get(Answer, original["id"]).response == original["response"]


def test_cancelled_job_with_published_answer_cannot_reconcile_completed_history(runtime):
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    original = finish(rt, receipt)
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        req = db.get(AnswerRequest, receipt["request_id"])
        # A deliberately inconsistent legacy fixture, never an installed row.
        job.state, job.stage = "cancelled", "cancelled"
        before = deepcopy(req.trace), req.updated_at
        db.commit()
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.state == "answered" and (req.trace, req.updated_at) == before
        assert db.get(Message, req.user_message_id).state == "completed"
        assert db.get(Message, req.assistant_message_id).active_answer_id == original["id"]
        assert db.get(Answer, original["id"]).response == original["response"]
