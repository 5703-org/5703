"""Workspace-scoped, redacted operational overview for administrators."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.modules.answering.models import AnswerRequest, Job
from app.modules.experiment.models import ExperimentRun
from app.modules.identity.models import User
from app.modules.knowledge.models import ActiveCorpus, Chunk, Document, CorpusRelease, ReleaseChunk
from app.modules.model_settings.models import ActiveModelConfiguration, ModelConfiguration
from app.platform_core.worker_locks import inspect_worker_locks


def _utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def _model(db: Session, config_id: str | None) -> dict | None:
    if not config_id:
        return None
    row = db.get(ModelConfiguration, config_id)
    if not row:
        return None
    return {
        "configuration_id": row.id,
        "name": row.name,
        "provider_preset": row.preset,
        "model": row.public_config.get("model"),
        "revision": row.revision,
    }


def overview(db: Session, workspace_id: str) -> dict:
    now = utcnow()
    pointer = db.get(ActiveCorpus, 1)
    release_id = pointer.release_id if pointer else None
    release = db.get(CorpusRelease, release_id) if release_id else None
    if release_id:
        documents, chunks = db.execute(
            select(func.count(func.distinct(Document.id)), func.count(ReleaseChunk.chunk_id))
            .select_from(ReleaseChunk)
            .join(Chunk, Chunk.id == ReleaseChunk.chunk_id)
            .join(Document, Document.id == Chunk.document_id)
            .where(ReleaseChunk.release_id == release_id)
        ).one()
    else:
        documents, chunks = 0, 0

    active_model = db.get(ActiveModelConfiguration, workspace_id)
    counts: dict[str, dict[str, int | None]] = {
        queue: {state: 0 for state in ("queued", "running", "retry_wait", "failed")}
        for queue in ("interactive", "background")
    }
    for kind, state, count in db.execute(
        select(Job.kind, Job.state, func.count(Job.id))
        .join(User, User.id == Job.owner_id)
        .where(
            User.workspace_id == workspace_id,
            Job.state.in_(("queued", "running", "retry_wait", "failed")),
        )
        .group_by(Job.kind, Job.state)
    ):
        queue = "interactive" if kind == "answer" else "background"
        counts[queue][state] = int(counts[queue][state] or 0) + count
    for queue, answer in (("interactive", True), ("background", False)):
        oldest = db.scalar(
            select(func.min(Job.created_at))
            .join(User, User.id == Job.owner_id)
            .where(
                User.workspace_id == workspace_id,
                Job.state == "queued",
                Job.kind == "answer" if answer else Job.kind != "answer",
            )
        )
        counts[queue]["oldest_queued_seconds"] = (
            max(0, int((now - _utc(oldest)).total_seconds())) if oldest else None
        )

    recent_failures = []
    for job in db.scalars(
        select(Job)
        .join(User, User.id == Job.owner_id)
        .where(User.workspace_id == workspace_id, Job.state == "failed")
        .order_by(Job.updated_at.desc())
        .limit(10)
    ):
        error = job.error if isinstance(job.error, dict) else {}
        recent_failures.append(
            {
                "job_id": job.id,
                "request_id": job.request_id,
                "kind": job.kind,
                "error_code": error.get("code") if isinstance(error.get("code"), str) else None,
                "updated_at": job.updated_at.isoformat(),
            }
        )

    experiment_states: dict[str, int] = defaultdict(int)
    for state, count in db.execute(
        select(ExperimentRun.state, func.count(ExperimentRun.id))
        .join(User, User.id == ExperimentRun.owner_id)
        .where(User.workspace_id == workspace_id)
        .group_by(ExperimentRun.state)
    ):
        experiment_states[state] = count

    usage = {"sampled_requests": 0, "requests_with_usage": 0, "input_tokens": 0, "output_tokens": 0}
    for request in db.scalars(
        select(AnswerRequest)
        .join(User, User.id == AnswerRequest.owner_id)
        .where(User.workspace_id == workspace_id)
        .order_by(AnswerRequest.created_at.desc())
        .limit(200)
    ):
        usage["sampled_requests"] += 1
        receipt = (request.trace or {}).get("usage", {})
        if not isinstance(receipt, dict):
            continue
        recognized = False
        for key in ("input_tokens", "output_tokens"):
            value = receipt.get(key)
            if type(value) is int and value >= 0:
                usage[key] += value
                recognized = True
        if recognized:
            usage["requests_with_usage"] += 1

    return {
        "observed_at": now.isoformat(),
        "database": "up",
        "corpus": {
            "active_release_id": release_id,
            "release_state": release.state if release else None,
            "document_count": documents,
            "chunk_vector_count": chunks,
        },
        "model": {
            "answer": _model(db, active_model.configuration_id) if active_model else None,
            "checker": _model(db, active_model.checker_configuration_id) if active_model else None,
        },
        "queues": counts,
        "worker_locks": inspect_worker_locks(db),
        "recent_failures": recent_failures,
        "experiment_states": dict(experiment_states),
        "recent_usage": {
            **usage,
            "scope": "up to 200 most recent workspace requests; missing provider counters excluded",
            "cost_estimate": None,
        },
    }
