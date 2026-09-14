"""Real PostgreSQL contention, publication rollback and uncertain execution."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4
import json
from sqlalchemy import event, func, select
from app.db.base import utcnow
from app.modules.answering.models import (
    Answer,
    AnswerRequest,
    Attempt,
    Job,
    Message,
    SessionSummary,
)
from app.modules.answering import service
from app.worker import recover_stale
from generation import GenerationService
from generation.adapters import LLMAdapter
from generation.types import ProviderResult, failure
from .test_chat_runtime import call, corpus, session, submit, finish


def parallel_requests(rt, method, path, bodies, headers):
    barrier = Barrier(len(bodies))

    def send(body):
        barrier.wait(timeout=5)
        return rt.client.request(method, "/api/v1" + path, json=body, headers=headers)

    with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
        return list(pool.map(send, bodies))


def test_simultaneous_duplicate_submit_and_optimistic_updates(runtime):
    rt = runtime
    s = session(rt)
    headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    responses = parallel_requests(
        rt, "POST", f"/sessions/{s['id']}/messages", [{"content": "Hello"}] * 2, headers
    )
    assert [r.status_code for r in responses] == [202, 202]
    assert responses[0].json()["data"] == responses[1].json()["data"]
    finish(rt, responses[0].json()["data"])
    current = call(rt, "GET", "/sessions/" + s["id"])
    responses = parallel_requests(
        rt,
        "PATCH",
        "/sessions/" + s["id"],
        [{"title": name, "version": current["version"]} for name in ("First", "Second")],
        headers,
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    profile = call(rt, "GET", "/profiles/me")
    responses = parallel_requests(
        rt,
        "PUT",
        "/profiles/me",
        [{**profile, "level": level} for level in ("beginner", "advanced")],
        headers,
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    with rt.db() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.session_id == s["id"])
            )
            == 2
        )


def test_provider_format_repair_counts_survive_retry(runtime, monkeypatch):
    rt = runtime
    s = session(rt)

    class InvalidAdapter:
        calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            return ProviderResult(raw_text="```not valid JSON```", finish_reason="stop")

    adapter = InvalidAdapter()
    monkeypatch.setattr(
        service, "GenerationService", lambda **kwargs: GenerationService(adapter=adapter, **kwargs)
    )
    receipt = submit(rt, s, "Hello")
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["can_retry"]
    headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    retry = call(
        rt, "POST", "/answer-requests/" + receipt["request_id"] + "/retry", {}, headers, 202
    )
    assert rt.work()
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.budget["consumed_calls"] == 3
        assert request.budget["format_repairs"] == 1
        assert (
            db.scalar(
                select(func.count()).select_from(Answer).where(Answer.request_id == request.id)
            )
            == 0
        )
    assert adapter.calls == 3
    assert call(rt, "GET", "/jobs/" + retry["job_id"])["state"] == "failed"


def test_cancel_during_provider_call_fences_late_output(runtime, monkeypatch):
    rt = runtime
    s = session(rt)
    receipt = submit(rt, s, "Hello")
    original = LLMAdapter.generate

    def cancelling(adapter, messages, **kwargs):
        cancelled = call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
        assert cancelled["state"] == "cancelled"
        return original(adapter, messages, **kwargs)

    monkeypatch.setattr(LLMAdapter, "generate", cancelling)
    assert rt.work()
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.state == "cancelled"
        assert request.budget["consumed_calls"] == 1
        assert (
            db.scalar(
                select(func.count()).select_from(Answer).where(Answer.request_id == request.id)
            )
            == 0
        )
    page = call(rt, "GET", f"/sessions/{s['id']}/messages")
    assert len(page["items"]) == 1 and page["items"][0]["state"] == "cancelled"


def test_stop_during_retrieval_model_work_does_not_wait_for_job_lock(runtime, monkeypatch):
    rt = runtime
    corpus(rt)
    s = session(rt)
    receipt = submit(rt, s)
    original = service.retrieve

    def cancellable(db, *args, **kwargs):
        assert (
            call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})["state"] == "cancelled"
        )
        return original(db, *args, **kwargs)

    monkeypatch.setattr(service, "retrieve", cancellable)
    assert rt.work()
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).state == "cancelled"
        assert (
            db.scalar(
                select(func.count())
                .select_from(Answer)
                .where(Answer.request_id == receipt["request_id"])
            )
            == 0
        )


def test_database_failure_publishes_no_partial_answer(runtime):
    rt = runtime
    s = session(rt)
    receipt = submit(rt, s, "Hello")
    fired = []

    def fail_once(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO answers ") and not fired:
            fired.append(True)
            raise RuntimeError("Injected database publication failure")

    event.listen(rt.engine, "before_cursor_execute", fail_once)
    try:
        assert rt.work()
    finally:
        event.remove(rt.engine, "before_cursor_execute", fail_once)
    assert fired
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.state == "error" and request.budget["consumed_calls"] == 1
        assert (
            db.scalar(
                select(func.count()).select_from(Answer).where(Answer.request_id == request.id)
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.session_id == s["id"], Message.role == "assistant")
            )
            == 0
        )
    headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    retry = call(
        rt, "POST", "/answer-requests/" + receipt["request_id"] + "/retry", {}, headers, 202
    )
    finish(rt, retry)
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 2


def test_stale_recovery_preserves_exhausted_budget(runtime):
    rt = runtime
    s = session(rt)
    receipt = submit(rt, s, "Hello")
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        request = db.get(AnswerRequest, receipt["request_id"])
        job.state = "running"
        job.execution_token = str(uuid4())
        job.updated_at = utcnow() - timedelta(minutes=10)
        request.state = "processing"
        request.budget = {**request.budget, "consumed_calls": 4}
        db.commit()
    assert recover_stale(rt.engine, 240) >= 1
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and not job["can_retry"]
    assert job["error"]["code"] == "WORKER_INTERRUPTED"
    assert job["error"]["details"]["uncertain_external_execution"] is True
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 4


def test_account_credential_revocation_and_admin_reset(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    email = uuid4().hex + "@example.com"
    password = "New-Password-123!"
    user = call(
        rt,
        "POST",
        "/admin/users",
        {"email": email, "full_name": "Disposable account", "password": password},
        admin,
        201,
    )

    def token(secret):
        data = call(rt, "POST", "/auth/login", {"email": email, "password": secret}, admin)
        return {"Authorization": "Bearer " + data["access_token"]}

    old = token(password)
    call(
        rt,
        "POST",
        "/users/me/password",
        {"old_password": password, "new_password": "Changed-Password-456!"},
        old,
    )
    call(rt, "GET", "/users/me", headers=old, status=401)
    fresh = token("Changed-Password-456!")
    updated = call(rt, "GET", "/users/me", headers=fresh)
    disabled = call(
        rt,
        "PATCH",
        "/admin/users/" + user["id"],
        {"version": updated["version"], "status": "deactivated"},
        admin,
    )
    call(rt, "GET", "/users/me", headers=fresh, status=401)
    call(
        rt,
        "PATCH",
        "/admin/users/" + user["id"],
        {"version": disabled["version"], "status": "active", "password": password},
        admin,
    )
    assert call(rt, "GET", "/users/me", headers=token(password))["id"] == user["id"]
    assert "hashed_password" not in disabled


def test_long_context_summary_is_persisted_and_attributable(runtime):
    rt = runtime
    s = session(rt)
    for _ in range(9):
        finish(rt, submit(rt, s, "Hello"))
    summary = call(rt, "POST", f"/sessions/{s['id']}/summary", {})
    assert summary["summary_id"] and summary["summary_text"]
    assert call(rt, "POST", f"/sessions/{s['id']}/summary", {}) == summary
    with rt.db() as db:
        stored = db.get(SessionSummary, summary["summary_id"])
        assert stored.content_hash == summary["summary_hash"] and not stored.invalidated
        assert stored.token_count <= 512 and stored.source_message_ids
        for identifier in stored.source_message_ids:
            message = db.get(Message, identifier)
            assert (
                message.session_id == s["id"] and message.sequence <= stored.covered_until_sequence
            )


def test_regeneration_keeps_configured_caps_and_benchmark_retry_is_blocked(runtime):
    rt = runtime
    s = session(rt)
    rt.settings.max_provider_calls = 1
    rt.settings.request_timeout_seconds = 30
    answer = finish(rt, submit(rt, s, "Hello"))
    receipt = call(
        rt,
        "POST",
        "/answers/" + answer["id"] + "/regenerate",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.budget["max_calls"] == 1 and req.budget["max_active_seconds"] == 30
        assert req.budget["consumed_calls"] == 0
    finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        req.mode = "benchmark_openqa"
        req.state = "error"
        req.regeneration_of = None
        assert service.can_retry(db, req) is False
        db.rollback()
