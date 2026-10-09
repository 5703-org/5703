"""Durable queue workers with atomic claims and explicit recovery."""

import argparse
import time
import datetime as dt
import socket
from sqlalchemy import case, select, text
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.db.base import new_uuid, utcnow
from app.platform_core.worker_locks import QUEUE_LOCKS
from app.modules.answering.models import AnswerRequest, Job
from app.modules.answering.service import (
    execute_answer,
    fail_job,
    ExecutionCancelled,
    lock_request_session,
)
from app.modules.knowledge.service import (
    execute_processing,
    execute_release,
    CorpusExecutionCancelled,
    mark_operation_interrupted,
)
from app.modules.experiment.bridge import execute_teaching, interrupt_teaching
from app.modules.learning_state.memory import execute_memory


def _interrupt_artifact(db, job, error):
    mark_operation_interrupted(db, job, error)
    if job.kind == "teaching":
        interrupt_teaching(db, job, error)


QUEUE_KINDS = {
    "interactive": ("answer",),
    "background": ("teaching", "memory", "process", "release"),
}


def _queued_jobs(queue):
    if queue not in QUEUE_LOCKS:
        raise ValueError("Unknown worker queue")
    query = select(Job).where(Job.state == "queued")
    if queue == "interactive":
        query = query.where(Job.kind.in_(QUEUE_KINDS["interactive"]))
    elif queue == "background":
        # Unknown durable kinds must fail visibly instead of waiting forever.
        query = query.where(Job.kind != "answer")
    return query.order_by(
        case(
            (Job.kind == "answer", 0),
            (Job.kind == "memory", 1),
            (Job.kind == "teaching", 2),
            (Job.kind == "process", 3),
            (Job.kind == "release", 4),
            else_=5,
        ),
        Job.created_at,
        Job.id,
    )


def _lock_terminal_job(db, job_id):
    """Take a request's parent before its job in a short terminal transaction."""
    with db.no_autoflush:
        initial = db.get(Job, job_id)
        if initial and initial.request_id:
            request = db.get(AnswerRequest, initial.request_id)
            if request:
                lock_request_session(db, request)
        return db.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )


def run_once(engine, settings, *, queue="all"):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        job = db.scalar(_queued_jobs(queue).with_for_update(skip_locked=True).limit(1))
        if not job:
            return False
        job.state = "running"
        job.execution_token = new_uuid()
        job.worker_id = f"{socket.gethostname()}:{queue}"[:80]
        job.attempts += 1
        job.updated_at = utcnow()
        id, token, kind, payload = job.id, job.execution_token, job.kind, job.payload
        db.commit()
    try:
        if kind == "answer":
            execute_answer(engine, settings, id, token)
        elif kind == "teaching":
            execute_teaching(engine, settings, id, token)
        elif kind == "memory":
            execute_memory(engine, settings, id, token)
        else:
            with factory() as db:
                if kind == "process":
                    execute_processing(
                        db,
                        settings,
                        payload["processing_id"],
                        execution=(id, token),
                        parser_policy=payload.get("parser_execution"),
                    )
                elif kind == "release":
                    execute_release(db, payload["release_id"], execution=(id, token))
                else:
                    raise ValueError("Unsupported job kind")
            with factory() as db:
                job = db.scalar(select(Job).where(Job.id == id).with_for_update())
                if job.execution_token == token and job.state == "running":
                    job.state = "succeeded"
                    job.stage = "complete"
                    job.execution_token = None
                    db.commit()
    except (ExecutionCancelled, CorpusExecutionCancelled):
        with factory() as db:
            job = _lock_terminal_job(db, id)
            if job and job.state in ("cancelled", "failed"):
                _interrupt_artifact(
                    db,
                    job,
                    job.error
                    or {
                        "code": "CANCELLED",
                        "message": "The operation stopped before publication.",
                    },
                )
                db.commit()
        return True
    except Exception as exc:
        with factory() as db:
            job = _lock_terminal_job(db, id)
            if job and job.execution_token == token and job.state == "running":
                code = getattr(exc, "code", "EXECUTION_FAILED")
                message = (
                    getattr(exc, "detail", None)
                    or "The operation failed. Inspect its trace or retry if eligible."
                )
                error = {
                    "code": code,
                    "message": message,
                    "details": {"error_type": type(exc).__name__},
                }
                fail_job(db, job, error)
                _interrupt_artifact(db, job, error)
                db.commit()
        # Log the class and job identity, never provider request content or secrets.
        print(f"job={id} error={type(exc).__name__}", flush=True)
    return True


def recover_stale(engine, seconds):
    cutoff = utcnow() - dt.timedelta(seconds=seconds)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        # Read candidate identities before taking any job locks. Every request
        # parent is acquired first; occupied sessions retain their leases.
        with db.no_autoflush:
            candidates = list(
                db.scalars(select(Job).where(Job.state == "running", Job.updated_at < cutoff))
            )
            parents = {
                job.id: db.get(AnswerRequest, job.request_id) if job.request_id else None
                for job in candidates
            }
            requests = {
                request.session_id: request
                for request in parents.values()
                if request and request.session_id
            }
            owned_sessions = {
                session_id
                for session_id, request in sorted(requests.items())
                if lock_request_session(db, request, skip_locked=True) is not None
            }
            eligible_ids = [
                job.id
                for job in candidates
                if not parents[job.id]
                or not parents[job.id].session_id
                or parents[job.id].session_id in owned_sessions
            ]
            rows = list(
                db.scalars(
                    select(Job)
                    .where(
                        Job.id.in_(eligible_ids), Job.state == "running", Job.updated_at < cutoff
                    )
                    .order_by(Job.id)
                    .with_for_update(skip_locked=True)
                    .execution_options(populate_existing=True)
                )
            )
        for job in rows:
            error = {
                "code": "WORKER_INTERRUPTED",
                "message": "Execution was interrupted. No late result can publish; review before an explicit rerun.",
                "details": {
                    "uncertain_external_execution": job.kind
                    in ("answer", "teaching", "release", "memory")
                },
            }
            fail_job(db, job, error)
            _interrupt_artifact(db, job, error)
        db.commit()
        return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--recover-stale", action="store_true")
    parser.add_argument("--queue", choices=tuple(QUEUE_LOCKS), default="all")
    args = parser.parse_args()
    settings = Settings()
    engine = init_engine(settings.database_url)
    lock = engine.connect()
    try:
        if engine.dialect.name == "postgresql":
            # The legacy all-queue worker takes an exclusive project lock.
            # Specialized workers share that lock and take separate exclusive
            # queue locks. This prevents an old all-queue process from racing
            # an interactive/background pair on the same installation.
            if args.queue == "all":
                granted = lock.scalar(text("SELECT pg_try_advisory_lock(5703001)"))
            else:
                granted = lock.scalar(text("SELECT pg_try_advisory_lock_shared(5703001)"))
            if not granted:
                raise SystemExit("Another worker layout already owns the project lock")
            if args.queue != "all" and not lock.scalar(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": QUEUE_LOCKS[args.queue]},
            ):
                raise SystemExit("Another worker already owns this queue")
            lock.commit()
        if args.recover_stale:
            print(f"Recovered {recover_stale(engine, settings.worker_stale_seconds)} stale jobs")
        while True:
            worked = run_once(engine, settings, queue=args.queue)
            if args.once:
                break
            if not worked:
                time.sleep(settings.worker_poll_seconds)
    finally:
        if engine.dialect.name == "postgresql":
            if args.queue != "all":
                lock.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": QUEUE_LOCKS[args.queue]},
                )
                lock.execute(text("SELECT pg_advisory_unlock_shared(5703001)"))
            else:
                lock.execute(text("SELECT pg_advisory_unlock(5703001)"))
            lock.commit()
        lock.close()


if __name__ == "__main__":
    main()
