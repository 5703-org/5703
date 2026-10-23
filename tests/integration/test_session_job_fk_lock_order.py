"""Authored real-PostgreSQL lock regressions; no provider or official data."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event, local
import time
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import event, select, text
from sqlalchemy.exc import OperationalError

from app.modules.answering import router, service
from app.modules.answering.models import AnswerRequest, Job, Snapshot
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession

from .test_answer_start_cancel_race import row_states
from .test_chat_runtime import call, session, submit


def test_postgres_negative_control_reproduces_job_session_fk_cycle(runtime):
    """The old Job -> FK Session order can deadlock native owner cancellation."""
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    try:
        worker_job, cancel_session = Event(), Event()
        observed = {}

        def old_worker_order():
            try:
                with rt.db() as db:
                    db.execute(text("SET LOCAL lock_timeout='8s'"))
                    row = db.scalar(
                        select(Job).where(Job.id == receipt["job_id"]).with_for_update()
                    )
                    req = db.get(AnswerRequest, row.request_id)
                    observed["worker_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
                    worker_job.set()
                    assert cancel_session.wait(10)
                    db.add(
                        Snapshot(
                            owner_id=req.owner_id,
                            session_id=req.session_id,
                            kind="authored_lock_probe",
                            payload={"test_only": True},
                            content_hash="0" * 64,
                        )
                    )
                    db.flush()  # A real FK check requires KEY SHARE on Session.
                    db.commit()
                    return "committed"
            except OperationalError as exc:
                return getattr(exc.orig, "sqlstate", None)
            finally:
                worker_job.set()

        def native_cancel_order():
            try:
                with rt.db() as db:
                    db.execute(text("SET LOCAL lock_timeout='8s'"))
                    req = db.get(AnswerRequest, receipt["request_id"])
                    actor = db.get(User, req.owner_id)
                    db.scalar(
                        select(ChatSession)
                        .where(ChatSession.id == req.session_id)
                        .with_for_update()
                    )
                    observed["cancel_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
                    cancel_session.set()
                    assert worker_job.wait(10)
                    router.cancel(receipt["job_id"], db=db, actor=actor)
                    return "committed"
            except OperationalError as exc:
                return getattr(exc.orig, "sqlstate", None)
            finally:
                cancel_session.set()

        with ThreadPoolExecutor(max_workers=2) as pool:
            worker = pool.submit(old_worker_order)
            cancel = pool.submit(native_cancel_order)
            results = [worker.result(timeout=20), cancel.result(timeout=20)]
        assert sorted(results) == ["40P01", "committed"], results
        assert observed["worker_backend"] != observed["cancel_backend"]
    finally:
        # Either deadlock victim is valid; this test must not leave its own
        # submitted answer queued in the session-scoped fixture database.
        cleaned = call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
        assert cleaned["state"] == "cancelled", cleaned


def test_real_answer_preparation_owns_session_before_job_and_fk_child(runtime, monkeypatch):
    """Actual execute_answer preparation and native HTTP Stop use one order."""
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    headers = rt.headers()
    token = str(uuid4())
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        req = db.get(AnswerRequest, receipt["request_id"])
        job.state, job.execution_token = "running", token
        original_command, original_budget = deepcopy(req.command), deepcopy(req.budget)
        db.commit()
    worker_in_preparation, owner_attempting = Event(), Event()
    state = local()
    observed = {}
    lock_session = service.lock_request_session
    prepare = service.prepare_query

    def capture_worker_context(db, req):
        result = lock_session(db, req)
        if req.id == receipt["request_id"]:
            state.db = db
        return result

    def before_sql(connection, cursor, statement, parameters, context, executemany):
        values = parameters.values() if isinstance(parameters, dict) else parameters
        if (
            worker_in_preparation.is_set()
            and "FROM sessions" in statement
            and "FOR UPDATE" in statement
            and conversation["id"] in values
        ):
            backend = connection.exec_driver_sql("SELECT pg_backend_pid()").scalar()
            if backend != observed["worker_backend"]:
                observed["cancel_backend"] = backend
                owner_attempting.set()

    def prepare_with_real_fk_probe(*args, **kwargs):
        db = state.db
        req = db.get(AnswerRequest, receipt["request_id"])
        observed["worker_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
        worker_in_preparation.set()
        assert owner_attempting.wait(10)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with rt.engine.connect() as observer:
                blockers = observer.scalar(
                    text("SELECT pg_blocking_pids(:pid)"),
                    {"pid": observed["cancel_backend"]},
                )
            if observed["worker_backend"] in blockers:
                break
            time.sleep(0.01)
        else:
            raise AssertionError("Owner did not actually wait behind the worker session lock")
        observed["native_session_block_observed"] = True
        db.add(
            Snapshot(
                owner_id=req.owner_id,
                session_id=req.session_id,
                kind="authored_lock_probe",
                payload={"test_only": True},
                content_hash="0" * 64,
            )
        )
        db.flush()
        observed["fk_child_inserted_with_owned_session"] = True
        return prepare(*args, **kwargs)

    def cancel_owner():
        assert worker_in_preparation.wait(10)
        return call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {}, headers)

    def execute():
        try:
            return service.execute_answer(rt.engine, rt.settings, receipt["job_id"], token)
        except service.ExecutionCancelled:
            return "cancelled_before_generation"

    monkeypatch.setattr(service, "lock_request_session", capture_worker_context)
    monkeypatch.setattr(service, "prepare_query", prepare_with_real_fk_probe)
    event.listen(rt.engine, "before_cursor_execute", before_sql)
    try:
        with (
            patch.object(service.GenerationService, "generate") as generation,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            worker = pool.submit(execute)
            cancellation = pool.submit(cancel_owner)
            assert cancellation.result(timeout=25)["state"] == "cancelled"
            worker.result(timeout=25)
            assert generation.call_count == 0
    finally:
        owner_attempting.set()
        event.remove(rt.engine, "before_cursor_execute", before_sql)
    after = row_states(rt, receipt)
    assert observed["worker_backend"] != observed["cancel_backend"]
    assert observed["native_session_block_observed"] is True
    assert observed["fk_child_inserted_with_owned_session"] is True
    assert after["job"] == after["request"] == after["message"] == "cancelled"
    assert after["execution_token"] is None and after["answers"] == after["attempts"] == 0
    assert after["answer_id"] is None and after["assistant_message_id"] is None
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command == original_command
        assert req.budget == original_budget
