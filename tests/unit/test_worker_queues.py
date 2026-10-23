"""Interactive answers remain claimable while background work is queued."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db import models as all_models  # noqa: F401
from app.db.base import Base
from app.modules.answering.models import Job
from app.modules.identity.models import Role, User, Workspace
from app import worker


def test_queue_workers_claim_distinct_durable_jobs_in_priority_order(tmp_path, monkeypatch):
    database = tmp_path / "queue.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(_env_file=None, env="test", database_url=f"sqlite:///{database}")
    with factory() as db:
        workspace = Workspace(name="Queue test", slug="queue-test")
        role = Role(name="admin")
        db.add_all([workspace, role])
        db.flush()
        actor = User(
            email="queue@example.test",
            full_name="Queue test",
            hashed_password="unused",
            workspace_id=workspace.id,
            role_id=role.id,
        )
        db.add(actor)
        db.flush()
        process = Job(owner_id=actor.id, kind="process", payload={"processing_id": "fixture"})
        answer = Job(owner_id=actor.id, kind="answer", payload={})
        memory = Job(owner_id=actor.id, kind="memory", payload={})
        db.add_all([process, answer, memory])
        db.commit()
        identities = {"process": process.id, "answer": answer.id, "memory": memory.id}

    calls = []

    def finish(kind):
        def complete(_engine, _settings, job_id, token):
            with factory() as db:
                job = db.get(Job, job_id)
                assert job and job.execution_token == token
                job.state = "succeeded"
                job.execution_token = None
                db.commit()
            calls.append((kind, job_id))

        return complete

    monkeypatch.setattr(worker, "execute_answer", finish("answer"))
    monkeypatch.setattr(worker, "execute_memory", finish("memory"))

    def process_item(_db, _settings, processing_id, execution, parser_policy=None):
        assert processing_id == "fixture"
        assert parser_policy is None
        calls.append(("process", execution[0]))

    monkeypatch.setattr(worker, "execute_processing", process_item)

    assert worker.run_once(engine, settings, queue="interactive")
    assert calls == [("answer", identities["answer"])]
    assert worker.run_once(engine, settings, queue="background")
    assert calls[-1] == ("memory", identities["memory"])
    assert worker.run_once(engine, settings, queue="background")
    assert calls[-1] == ("process", identities["process"])
    assert worker.run_once(engine, settings, queue="interactive") is False
    assert worker.run_once(engine, settings, queue="background") is False
    with factory() as db:
        assert {db.get(Job, job_id).state for job_id in identities.values()} == {"succeeded"}
    engine.dispose()
