"""Versioned conditional memory writes and fenced asynchronous extraction."""

from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering.models import Job
from app.modules.identity.models import User
from personalisation import memory_v2 as rules, memory_v4 as conditions, memory_writer_v4 as writer
from . import memory_v2 as legacy
from .models import MemoryEntry, MemorySuppression, MemoryWriteEvent


def apply_operations(db, owner_id, event, operations, *, withheld=None):
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    actor, source = legacy.owned_source(db, owner_id, event.source_message_id)
    if (
        event.owner_id != owner_id
        or event.workspace_id != actor.workspace_id
        or event.source_hash != rules.digest(source.content)
    ):
        raise AppError("CONFLICT", "The memory source identity changed.")
    if not settings.enabled or event.epoch != settings.revocation_epoch:
        event.status = "revoked"
        return []
    if event.status != "pending":
        return event.operations or []
    plan = writer.prepare_operations(source.content, operations)
    receipts = list(withheld or []) + plan["withheld"]
    for item in plan["operations"]:
        key = rules.canonical(item["category"], item["field_key"], item["scope"])
        suppressed = db.scalar(
            select(MemorySuppression.id).where(
                MemorySuppression.owner_id == owner_id,
                MemorySuppression.source_message_id == source.id,
            )
        )
        row = db.scalar(
            select(MemoryEntry).where(
                MemoryEntry.owner_id == owner_id,
                MemoryEntry.canonical_key == key,
            )
        )
        reason = (
            "source_suppressed"
            if suppressed
            else "deleted_field_requires_confirmation"
            if row and row.status == "deleted"
            else "stale_source_event"
            if row and row.source_event_sequence > event.sequence
            else None
        )
        if reason:
            receipts.append(
                {"operation": "NO_OP", "field_key": item["field_key"], "reason": reason}
            )
            continue
        provenance = {
            "kind": "user_statement",
            "source_message_id": source.id,
            "source_quote": item["source_quote"],
            "source_hash": event.source_hash,
            "event_id": event.id,
            "writer_version": writer.WRITER_VERSION,
            "condition_policy_hash": rules.digest(conditions.freeze_policy()),
            "verification_scope": "exact owned statement; no independent scientific assessment",
        }
        outcomes = legacy.apply_operations(db, owner_id, event, [item], provenance=provenance)
        for receipt in outcomes:
            if receipt["operation"] in {"ADD", "UPDATE"}:
                db.get(MemoryEntry, receipt["memory_id"]).writer_version = writer.WRITER_VERSION
        receipts.extend(outcomes)
    event.operations = receipts
    event.status = "applied" if any(item["operation"] != "NO_OP" for item in receipts) else "no_op"
    db.flush()
    return receipts


def apply_source(db, owner_id, event, text):
    plan = writer.prepare_operations(text)
    if plan["operations"] or plan["withheld"]:
        return apply_operations(db, owner_id, event, plan["operations"], withheld=plan["withheld"])
    return []


def enqueue(db, owner_id, message, config, use_profile, *, policy_version):
    from . import memory

    if policy_version != writer.WRITER_VERSION:
        raise ValueError("Unknown V4 memory writer")
    settings = memory.settings_for(db, owner_id, lock=True)
    if not use_profile or not settings.enabled or not rules.eligible(message.content):
        return
    event = legacy.source_event(db, owner_id, message.id)
    if event.status in {"applied", "no_op", "revoked"}:
        return
    if db.scalar(
        select(Job.id).where(
            Job.owner_id == owner_id,
            Job.kind == "memory",
            Job.payload["event_id"].as_string() == event.id,
        )
    ):
        return
    db.add(
        Job(
            owner_id=owner_id,
            kind="memory",
            payload={
                "source_message_id": message.id,
                "source_hash": event.source_hash,
                "event_id": event.id,
                "event_sequence": event.sequence,
                "epoch": settings.revocation_epoch,
                "memory_policy_version": writer.WRITER_VERSION,
                "condition_policy": conditions.freeze_policy(),
                "model_config": config,
                "budget": {"max_calls": 2, "max_active_seconds": 90},
            },
        )
    )


def execute(db_engine, settings, job_id, token):
    from sqlalchemy.orm import sessionmaker
    from generation.types import ModelConfig, RequestBudget
    from personalisation.memory_writer_v4 import extract_operations
    from app.modules.model_settings.service import resolve_secret
    from app.modules.answering.service import ExecutionCancelled
    from app.modules.answering.models import Attempt
    from . import memory

    factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def validate(db, job):
        state = memory.settings_for(db, job.owner_id, lock=True)
        event = db.get(MemoryWriteEvent, job.payload["event_id"])
        if (
            job.state != "running"
            or job.execution_token != token
            or not state.enabled
            or job.payload.get("epoch") != state.revocation_epoch
            or not event
            or event.status in {"applied", "no_op", "revoked"}
            or event.owner_id != job.owner_id
            or event.source_message_id != job.payload.get("source_message_id")
            or event.sequence != job.payload.get("event_sequence")
            or event.source_hash != job.payload.get("source_hash")
            or job.payload.get("memory_policy_version") != writer.WRITER_VERSION
            or job.payload.get("condition_policy") != conditions.freeze_policy()
            or event.epoch != state.revocation_epoch
        ):
            raise ExecutionCancelled()
        actor, message = legacy.owned_source(db, job.owner_id, job.payload["source_message_id"])
        if event.workspace_id != actor.workspace_id or event.source_hash != rules.digest(
            message.content
        ):
            raise ExecutionCancelled()
        if event.status == "failed":
            event.status, event.error = "pending", None
        return event, message

    with factory() as db:
        job = db.get(Job, job_id)
        event, message = validate(db, job)
        owner_id, text = job.owner_id, message.content
        config = ModelConfig.from_dict(job.payload["model_config"])
        budget = RequestBudget.from_dict(job.payload["budget"])
        key = resolve_secret(db, settings, config.configuration_id)
        db.commit()

    def attempt(payload):
        with factory() as db:
            memory.settings_for(db, owner_id, lock=True)
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            validate(db, job)
            job.payload = {**job.payload, "budget": payload["budget"]}
            job.stage = "memory_extraction_v4"
            count = len(list(db.scalars(select(Attempt.id).where(Attempt.job_id == job_id))))
            db.add(Attempt(job_id=job_id, sequence=count + 1, payload=payload))
            db.commit()

    try:
        result = extract_operations(text, config, budget, attempt, api_key=key)
    finally:
        key = None
    with factory() as db:
        memory.settings_for(db, owner_id, lock=True)
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        event, _ = validate(db, job)
        if result["error"]:
            event.status, event.error = "failed", result["error"]
            job.state, job.stage, job.error = "failed", "failed", result["error"]
            receipts = []
        else:
            receipts = apply_operations(
                db, owner_id, event, result["operations"], withheld=result.get("withheld")
            )
            job.state, job.stage = "succeeded", "complete"
        saved = [
            {
                "memory_id": r["memory_id"],
                "version": r["version"],
                "message": "Learning memory saved.",
                "action": "undo_save",
            }
            for r in receipts
            if r["operation"] in {"ADD", "UPDATE"}
        ]
        job.payload = {
            **job.payload,
            "saved": saved,
            "condition_withheld": result.get("withheld", []),
            "extraction_schema_version": result.get("extraction_schema_version"),
            "budget": result["budget"],
            "usage": result["usage"],
        }
        job.execution_token = None
        db.commit()
