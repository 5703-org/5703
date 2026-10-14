"""Authored PostgreSQL diagnostic of the actual UPDATE-trace waiting statement."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.modules.answering import router
from app.modules.answering.models import AnswerRequest, Job
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession

from .test_chat_runtime import session, submit


@pytest.mark.parametrize("prior_update_in_same_transaction", [False, True])
def test_native_trace_update_lock_probe(runtime, prior_update_in_same_transaction):
    rt = runtime
    conversation = session(rt)
    receipt = submit(rt, conversation, "Hello")
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        job.state = "running"
        job.execution_token = str(uuid4())
        db.commit()
    job_locked, session_locked = Event(), Event()
    observed = {"prior_update_in_same_transaction": prior_update_in_same_transaction}

    def worker():
        try:
            with rt.db() as db:
                db.execute(text("SET LOCAL lock_timeout='8s'"))
                job = db.scalar(select(Job).where(Job.id == receipt["job_id"]).with_for_update())
                req = db.get(AnswerRequest, job.request_id)
                observed["worker_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
                if prior_update_in_same_transaction:
                    req.state = "processing"
                    db.flush()
                job_locked.set()
                assert session_locked.wait(10)
                req.trace = {**req.trace, "authored_lock_probe": True}
                db.flush()  # Same UPDATE trace + updated_at shape as the actual log.
                db.commit()
                return "committed"
        except OperationalError as error:
            return getattr(error.orig, "sqlstate", None)
        finally:
            job_locked.set()

    def cancel():
        try:
            with rt.db() as db:
                db.execute(text("SET LOCAL lock_timeout='8s'"))
                req = db.get(AnswerRequest, receipt["request_id"])
                actor = db.get(User, req.owner_id)
                db.scalar(
                    select(ChatSession).where(ChatSession.id == req.session_id).with_for_update()
                )
                observed["cancel_backend"] = db.scalar(text("SELECT pg_backend_pid()"))
                session_locked.set()
                assert job_locked.wait(10)
                router.cancel(receipt["job_id"], db=db, actor=actor)
                return "committed"
        except OperationalError as error:
            return getattr(error.orig, "sqlstate", None)
        finally:
            session_locked.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(worker)
        b = pool.submit(cancel)
        observed["results"] = [a.result(timeout=20), b.result(timeout=20)]
    print("ACTUAL_TRACE_UPDATE_LOCK_PROBE", observed)
    assert observed["worker_backend"] != observed["cancel_backend"]
    expected = (
        ["40P01", "committed"] if prior_update_in_same_transaction else ["committed", "committed"]
    )
    assert sorted(observed["results"]) == expected, observed
