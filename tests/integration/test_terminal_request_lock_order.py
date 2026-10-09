"""Authored PostgreSQL recovery and exception cancellation regressions."""

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from uuid import uuid4

import pytest
from sqlalchemy import event, select, text

from app import worker
from app.db.base import utcnow
from app.modules.answering.models import AnswerRequest, Job
from app.modules.learning.models import ChatSession

from .conftest import disposable_postgres_url
from .test_answer_start_cancel_race import row_states
from .test_chat_runtime import call, session, submit


@pytest.fixture(scope="module")
def postgres_url():
    """Keep global recovery counts independent of jobs in other modules."""
    with disposable_postgres_url() as url:
        yield url


def stale_job(rt, receipt, *, age=300):
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        job.state, job.execution_token = "running", str(uuid4())
        job.updated_at = utcnow() - dt.timedelta(seconds=age)
        db.commit()


def test_stale_recovery_skips_occupied_parent_then_recovers_once(runtime):
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    stale_job(rt, receipt)
    with rt.db() as occupied:
        occupied.scalar(
            select(ChatSession).where(ChatSession.id == conversation["id"]).with_for_update()
        )
        with rt.db() as observer:
            before = observer.get(Job, receipt["job_id"]).execution_token
        assert worker.recover_stale(rt.engine, 240) == 0
        with rt.db() as observer:
            row = observer.get(Job, receipt["job_id"])
            assert row.state == "running" and row.execution_token == before
        occupied.rollback()
    assert worker.recover_stale(rt.engine, 240) == 1
    assert worker.recover_stale(rt.engine, 240) == 0
    after = row_states(rt, receipt)
    assert after["job"] == "failed" and after["request"] == after["message"] == "error"
    assert after["execution_token"] is None and after["answers"] == 0
    with rt.db() as db:
        assert db.get(Job, receipt["job_id"]).error["code"] == "WORKER_INTERRUPTED"


def test_stale_recovery_preserves_fresh_lease_and_cancelled_terminal(runtime):
    rt = runtime
    stale = submit(rt, session(rt), "Hello")
    fresh = submit(rt, session(rt), "Hello")
    cancelled = submit(rt, session(rt), "Hello")
    stale_job(rt, stale)
    stale_job(rt, fresh, age=30)
    call(rt, "POST", "/jobs/" + cancelled["job_id"] + "/cancel", {}, rt.headers())
    with rt.db() as db:
        token = db.get(Job, fresh["job_id"]).execution_token
    assert worker.recover_stale(rt.engine, 240) == 1
    assert row_states(rt, stale)["job"] == "failed"
    assert row_states(rt, cancelled)["job"] == "cancelled"
    after = row_states(rt, fresh)
    assert after["job"] == "running" and after["execution_token"] == token
    assert after["answers"] == 0


def test_actual_worker_exception_and_owner_stop_share_session_before_job(runtime, monkeypatch):
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    headers = rt.headers()
    session_owned, cancel_waiting = Event(), Event()
    observed = {}
    original = worker.lock_request_session

    def hold_parent(db, req, *, skip_locked=False):
        value = original(db, req, skip_locked=skip_locked)
        if req.id == receipt["request_id"]:
            observed["worker_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
            session_owned.set()
            assert cancel_waiting.wait(10)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                with rt.engine.connect() as probe:
                    blockers = probe.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": observed["cancel_backend"]}
                    )
                if observed["worker_backend"] in blockers:
                    observed["parent_wait_observed"] = True
                    break
                time.sleep(0.01)
            else:
                raise AssertionError("Native Stop never waited for the owned parent")
        return value

    def before_sql(connection, cursor, statement, parameters, context, executemany):
        values = parameters.values() if isinstance(parameters, dict) else parameters
        if (
            session_owned.is_set()
            and "FROM sessions" in statement
            and "FOR UPDATE" in statement
            and conversation["id"] in values
        ):
            observed["cancel_backend"] = connection.exec_driver_sql(
                "SELECT pg_backend_pid()"
            ).scalar()
            cancel_waiting.set()

    def fail(*args, **kwargs):
        raise RuntimeError("Authored execution failure; no provider submitted")

    def stop():
        assert session_owned.wait(10)
        return call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {}, headers)

    monkeypatch.setattr(worker, "execute_answer", fail)
    monkeypatch.setattr(worker, "lock_request_session", hold_parent)
    event.listen(rt.engine, "before_cursor_execute", before_sql)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            task = pool.submit(worker.run_once, rt.engine, rt.settings, queue="interactive")
            cancel = pool.submit(stop)
            assert task.result(timeout=25) is True
            assert cancel.result(timeout=25)["state"] == "failed"
    finally:
        cancel_waiting.set()
        event.remove(rt.engine, "before_cursor_execute", before_sql)
    after = row_states(rt, receipt)
    assert observed["parent_wait_observed"] is True
    assert after["job"] == "failed" and after["request"] == after["message"] == "error"
    assert after["execution_token"] is None and after["answers"] == after["attempts"] == 0
    with rt.db() as db:
        assert db.get(Job, receipt["job_id"]).error["details"]["error_type"] == "RuntimeError"
