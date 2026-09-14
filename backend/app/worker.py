"""One durable worker with atomic claims, explicit recovery and publication tokens."""

import argparse
import time
import datetime as dt
import socket
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.db.base import new_uuid, utcnow
from app.modules.answering.models import Job
from app.modules.answering.service import execute_answer, fail_job, ExecutionCancelled
from app.modules.knowledge.service import (
    execute_processing,
    execute_release,
    CorpusExecutionCancelled,
    mark_operation_interrupted,
)
from app.modules.experiment.bridge import execute_teaching, interrupt_teaching


def _interrupt_artifact(db, job, error):
    mark_operation_interrupted(db, job, error)
    if job.kind == "teaching":
        interrupt_teaching(db, job, error)


def run_once(engine, settings):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        job = db.scalar(
            select(Job)
            .where(Job.state == "queued")
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return False
        job.state = "running"
        job.execution_token = new_uuid()
        job.worker_id = socket.gethostname()
        job.attempts += 1
        job.updated_at = utcnow()
        id, token, kind, payload = job.id, job.execution_token, job.kind, job.payload
        db.commit()
    try:
        if kind == "answer":
            execute_answer(engine, settings, id, token)
        elif kind == "teaching":
            execute_teaching(engine, settings, id, token)
        else:
            with factory() as db:
                if kind == "process":
                    execute_processing(
                        db, settings, payload["processing_id"], execution=(id, token)
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
            job = db.scalar(select(Job).where(Job.id == id).with_for_update())
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
            job = db.scalar(select(Job).where(Job.id == id).with_for_update())
            if job.execution_token == token and job.state == "running":
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
        rows = list(
            db.scalars(
                select(Job)
                .where(Job.state == "running", Job.updated_at < cutoff)
                .with_for_update(skip_locked=True)
            )
        )
        for job in rows:
            error = {
                "code": "WORKER_INTERRUPTED",
                "message": "Execution was interrupted. No late result can publish; review before an explicit rerun.",
                "details": {
                    "uncertain_external_execution": job.kind in ("answer", "teaching", "release")
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
    args = parser.parse_args()
    settings = Settings()
    engine = init_engine(settings.database_url)
    lock = engine.connect()
    try:
        if engine.dialect.name == "postgresql":
            if not lock.scalar(text("SELECT pg_try_advisory_lock(5703001)")):
                raise SystemExit("Another worker already owns the project worker lock")
            lock.commit()
        if args.recover_stale:
            print(f"Recovered {recover_stale(engine, settings.worker_stale_seconds)} stale jobs")
        while True:
            worked = run_once(engine, settings)
            if args.once:
                break
            if not worked:
                time.sleep(settings.worker_poll_seconds)
    finally:
        if engine.dialect.name == "postgresql":
            lock.execute(text("SELECT pg_advisory_unlock(5703001)"))
            lock.commit()
        lock.close()


if __name__ == "__main__":
    main()
