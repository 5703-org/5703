"""Owner-scoped memory updates, erasure and durable extraction fencing."""

import datetime as dt
import hashlib
import json
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker
from app.db.base import utcnow
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.answering.models import AnswerRequest, Attempt, Job, Message, SessionSummary
from app.modules.learning.models import ChatSession
from .models import (
    MemorySettings,
    MemoryEntry,
    MemoryRevision,
    MemorySuppression,
    MemorySnapshot,
    PrivateAnswerDraft,
    MemoryWriteEvent,
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def settings_for(db, owner_id, *, lock=False):
    # Lock a durable parent even on first creation; an absent-row lock is insufficient.
    if lock:
        db.scalar(select(User.id).where(User.id == owner_id).with_for_update())
    row = db.scalar(select(MemorySettings).where(MemorySettings.owner_id == owner_id))
    if row is None:
        if not lock:
            return settings_for(db, owner_id, lock=True)
        row = MemorySettings(owner_id=owner_id, enabled=False, revocation_epoch=0)
        db.add(row)
        db.flush()
    if lock:
        # HTTP sessions disable autoflush; preserve a caller's pending settings
        # change before refreshing under the already-owned parent lock.
        db.flush()
        db.refresh(row, with_for_update=True)
    return row


def settings_out(row):
    return {
        "enabled": row.enabled,
        "version": row.version,
        "revocation_epoch": row.revocation_epoch,
    }


def entry_owned(db, owner_id, entry_id):
    row = db.get(MemoryEntry, entry_id)
    if row is None or row.owner_id != owner_id:
        raise AppError("NOT_FOUND")
    return row


def aware(value):
    return value.replace(tzinfo=dt.timezone.utc) if value and value.tzinfo is None else value


def entry_out(row):
    expired = row.expires_at and aware(row.expires_at) <= utcnow()
    return {
        "id": row.id,
        "category": row.category,
        "content": row.content,
        "scope": row.scope,
        "source_message_id": row.source_message_id,
        "status": "expired" if row.status == "active" and expired else row.status,
        "match_policy": row.match_policy,
        "version": row.version,
        "updated_at": row.updated_at.isoformat(),
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "field_key": row.field_key,
        "scope_topics": row.scope_topics or [],
        "verification": row.verification,
        "writer_version": row.writer_version,
        "effective_at": row.effective_at.isoformat() if row.effective_at else None,
        "source_event_sequence": row.source_event_sequence,
        "provenance": row.source_details or {},
    }


def parse_expiry(value):
    if value is None:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timezone required")
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise AppError(
            "VALIDATION_FAILED", "Expiry must be an ISO timestamp with a timezone."
        ) from exc


def revoke_snapshots(db, owner_id, entry_id=None):
    """Erase memory derivatives and cancel stale work without deleting chat history."""
    settings = settings_for(db, owner_id, lock=True)
    settings.revocation_epoch += 1
    affected = []
    for snap in db.scalars(select(MemorySnapshot).where(MemorySnapshot.owner_id == owner_id)):
        entries = snap.payload.get("entries", [])
        if entry_id is None or any(e.get("id") == entry_id for e in entries):
            # Erase entire combined snapshot, never retain deleted text in an undo payload.
            snap.payload = {"entries": [], "revoked": True, "entry_ids": [e["id"] for e in entries]}
            snap.invalidated = True
            affected.append(snap.id)
    if affected:
        db.execute(
            update(PrivateAnswerDraft)
            .where(PrivateAnswerDraft.memory_snapshot_id.in_(affected))
            .values(payload={"redacted": "memory_revoked"})
        )
    from app.modules.answering.service import cancel_job, lock_request_session

    for req in db.scalars(select(AnswerRequest).where(AnswerRequest.owner_id == owner_id)):
        if req.command.get("memory_snapshot_id") in affected:
            lock_request_session(db, req)
            # New memory-enabled traces are already content-free; defensive purge covers imported derivatives.
            trace = dict(req.trace or {})
            trace.pop("model_messages", None)
            trace["memory_revoked"] = True
            req.trace = trace
            for job in db.scalars(
                select(Job)
                .where(Job.request_id == req.id, Job.state.in_(["queued", "running", "retry_wait"]))
                .with_for_update()
            ):
                cancel_job(db, job)
    for job in db.scalars(
        select(Job)
        .where(
            Job.owner_id == owner_id,
            Job.kind == "memory",
            Job.state.in_(["queued", "running", "retry_wait"]),
        )
        .with_for_update()
    ):
        cancel_job(db, job)
        job.payload = {
            k: v
            for k, v in job.payload.items()
            if k
            in {
                "source_message_id",
                "epoch",
                "budget",
                "model_config",
                "event_id",
                "event_sequence",
                "memory_policy_version",
            }
        }
    # Session summaries contain independent user chat, not injected memory. Only memory-kind
    # snapshots are erased; chat history uses its separate lifecycle and is not silently removed.


def update_settings(db, owner_id, body):
    row = settings_for(db, owner_id, lock=True)
    if body.version != row.version:
        raise AppError("CONFLICT", "Memory settings changed. Refresh before saving.")
    if row.enabled != body.enabled:
        row.enabled = body.enabled
        row.version += 1
        if not row.enabled:
            revoke_snapshots(db, owner_id)
    db.commit()
    return settings_out(row)


def update_controls(db, owner_id, entry_id, body):
    """Pause applicability without erasing the saved source or enabling a selector."""
    settings_for(db, owner_id, lock=True)
    row = entry_owned(db, owner_id, entry_id)
    if row.version != body.version or row.status == "deleted":
        raise AppError("CONFLICT", "Memory changed or was deleted. Refresh before saving.")
    status = "paused" if body.paused else "active"
    if row.status == status and row.match_policy == body.match_policy:
        db.commit()
        return entry_out(row)
    from .memory_v2 import invalidate_entries, source_event

    event = source_event(db, owner_id)
    invalidate_entries(db, owner_id, [row.id])
    row.status = status
    row.match_policy = body.match_policy
    row.source_event_sequence = event.sequence
    row.version += 1
    row.updated_at = utcnow()
    db.add(
        MemoryRevision(
            entry_id=row.id,
            entry_version=row.version,
            content=row.content,
            source_message_id=row.source_message_id,
            action="applicability_controls",
            details={
                "status": status,
                "match_policy": row.match_policy,
                "source_event_sequence": event.sequence,
            },
        )
    )
    event.status = "applied"
    event.operations = [{"operation": "CONTROLS", "memory_id": row.id, "version": row.version}]
    db.commit()
    return entry_out(row)


def edit_entry(db, owner_id, entry_id, body):
    settings_for(db, owner_id, lock=True)
    row = entry_owned(db, owner_id, entry_id)
    if row.version != body.version or row.status == "deleted":
        raise AppError("CONFLICT", "Memory changed or was deleted. Refresh before saving.")
    content = body.content.strip()
    if not content:
        raise AppError("VALIDATION_FAILED")
    from personalisation import memory_v2 as engine
    from .memory_v2 import source_event

    event = source_event(db, owner_id)
    chosen_field = body.field_key or row.field_key
    if chosen_field is None:
        inferred = engine.infer_field(content)
        chosen_field = (
            inferred
            if inferred and engine.FIELDS[inferred] == row.category
            else "learning_goal"
            if row.category == "goal"
            else None
        )
    if chosen_field is not None:
        try:
            chosen_field = engine.field_key(chosen_field)
            if engine.FIELDS[chosen_field] != row.category:
                raise ValueError("Field does not match this memory category")
        except ValueError as exc:
            raise AppError("VALIDATION_FAILED", str(exc)) from exc
        row.field_key = chosen_field
        row.writer_version = engine.WRITER_VERSION
    if row.field_key:
        new_scope = engine.scope_name(body.scope)
        new_key = engine.canonical(row.category, row.field_key, new_scope)
        collision = db.scalar(
            select(MemoryEntry).where(
                MemoryEntry.owner_id == owner_id,
                MemoryEntry.canonical_key == new_key,
                MemoryEntry.id != row.id,
            )
        )
        if collision:
            raise AppError(
                "CONFLICT",
                "Another memory already uses this field and scope. Edit that entry instead.",
            )
        row.canonical_key = new_key
        row.scope_topics = engine.topics(new_scope)
        row.source_details = {
            "kind": "user_correction",
            "recorded_by": owner_id,
            "event_id": event.id,
            "previous_source_message_id": row.source_message_id,
        }
        row.verification = (
            "user_corrected" if row.category != "assessment_performance" else "recorded_unconfirmed"
        )
        row.effective_at = utcnow()
    row.source_event_sequence = event.sequence
    revoke_snapshots(db, owner_id, row.id)
    row.content, row.scope, row.expires_at = (
        content,
        engine.scope_name(body.scope) if row.field_key else body.scope.strip(),
        parse_expiry(body.expires_at),
    )
    row.version += 1
    row.updated_at = utcnow()
    db.add(
        MemoryRevision(
            entry_id=row.id,
            entry_version=row.version,
            content=content,
            action="user_correction",
            source_message_id=row.source_message_id,
            details={
                "source_event_sequence": event.sequence,
                "scope": row.scope,
                "verification": row.verification,
            },
        )
    )
    event.status = "applied"
    event.operations = [
        {
            "operation": "UPDATE",
            "memory_id": row.id,
            "version": row.version,
            "reason": "user_correction",
        }
    ]
    db.commit()
    return entry_out(row)


def delete_entry(db, owner_id, entry_id, version):
    settings_for(db, owner_id, lock=True)
    row = entry_owned(db, owner_id, entry_id)
    if row.version != version:
        raise AppError("CONFLICT", "Memory changed. Refresh before deleting.")
    if row.status != "deleted":
        from .memory_v2 import source_event

        event = source_event(db, owner_id)
        source_ids = {
            r.source_message_id
            for r in db.scalars(select(MemoryRevision).where(MemoryRevision.entry_id == row.id))
            if r.source_message_id
        }
        if row.source_message_id:
            source_ids.add(row.source_message_id)
        for mid in source_ids:
            if not db.scalar(
                select(MemorySuppression).where(
                    MemorySuppression.owner_id == owner_id,
                    MemorySuppression.source_message_id == mid,
                    MemorySuppression.canonical_key == row.canonical_key,
                )
            ):
                db.add(
                    MemorySuppression(
                        owner_id=owner_id, source_message_id=mid, canonical_key=row.canonical_key
                    )
                )
        revoke_snapshots(db, owner_id, row.id)
        db.execute(
            update(MemoryRevision)
            .where(MemoryRevision.entry_id == row.id)
            .values(content=None, details={})
        )
        row.content = None
        row.source_details = {}
        row.scope_topics = []
        row.source_event_sequence = event.sequence
        row.source_message_id = None
        row.scope = "deleted"
        row.expires_at = None
        row.status = "deleted"
        row.match_policy = "rules_only"
        row.version += 1
        row.updated_at = utcnow()
        db.add(
            MemoryRevision(
                entry_id=row.id, entry_version=row.version, content=None, action="deleted"
            )
        )
        event.status = "applied"
        event.operations = [
            {
                "operation": "DELETE",
                "memory_id": row.id,
                "version": row.version,
                "reason": "user_erasure",
            }
        ]
    db.commit()
    return {"deleted": True, "id": row.id, "version": row.version}


def freeze_memory(
    db,
    owner_id,
    question,
    use_profile,
    *,
    policy_version="explicit_learning_memory_v1",
    current_message_id=None,
    profile=None,
    context=None,
    counter=None,
    semantic_policy=None,
):
    if policy_version == "query_conditioned_memory_v5":
        from .memory_v5 import freeze

        return freeze(
            db,
            owner_id,
            question,
            use_profile,
            policy_version=policy_version,
            current_message_id=current_message_id,
            profile=profile,
            context=context,
            counter=counter,
            semantic_policy=semantic_policy,
        )
    if policy_version == "query_conditioned_memory_v4":
        from .memory_v4 import freeze

        return freeze(
            db,
            owner_id,
            question,
            use_profile,
            policy_version=policy_version,
            current_message_id=current_message_id,
            profile=profile,
            context=context,
            counter=counter,
            semantic_policy=semantic_policy,
        )
    if policy_version == "query_conditioned_memory_v3":
        from .memory_v3 import freeze

        return freeze(
            db,
            owner_id,
            question,
            use_profile,
            policy_version=policy_version,
            current_message_id=current_message_id,
            profile=profile,
            context=context,
            counter=counter,
            semantic_policy=semantic_policy,
        )
    if policy_version != "explicit_learning_memory_v1":
        from .memory_v2 import freeze

        return freeze(
            db,
            owner_id,
            question,
            use_profile,
            policy_version=policy_version,
            current_message_id=current_message_id,
            profile=profile,
            context=context,
            counter=counter,
        )
    state = settings_for(db, owner_id, lock=True)
    if not use_profile or not state.enabled:
        return None
    words = set(question.casefold().split())
    entries = []
    for row in db.scalars(
        select(MemoryEntry)
        .where(MemoryEntry.owner_id == owner_id, MemoryEntry.status == "active")
        .order_by(MemoryEntry.updated_at.desc())
    ):
        if row.expires_at and aware(row.expires_at) <= utcnow():
            continue
        if row.scope != "global" and not (set(row.scope.casefold().split()) & words):
            continue
        entries.append(
            {
                "id": row.id,
                "version": row.version,
                "category": row.category,
                "content": row.content,
                "scope": row.scope,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
        )
        if len(entries) == 10:
            break
    payload = {
        "entries": entries,
        "precedence": [
            "current_instruction",
            "saved_settings",
            "active_memory",
            "confirmed_observation",
        ],
        "version": "explicit_learning_memory_v1",
    }
    snap = MemorySnapshot(
        owner_id=owner_id,
        revocation_epoch=state.revocation_epoch,
        payload=payload,
        content_hash=digest(payload),
    )
    db.add(snap)
    db.flush()
    return snap


def read_snapshot(db, owner_id, snapshot_id):
    if snapshot_id is None:
        return None
    snap = db.get(MemorySnapshot, snapshot_id)
    state = settings_for(db, owner_id)
    if (
        not snap
        or snap.owner_id != owner_id
        or snap.invalidated
        or not state.enabled
        or snap.revocation_epoch != state.revocation_epoch
    ):
        raise AppError("CONFLICT", "The memory context was revoked. Submit a new request.")
    if (
        snap.payload.get("workspace_id")
        and snap.payload["workspace_id"] != db.get(User, owner_id).workspace_id
    ):
        raise AppError("CONFLICT", "The memory workspace changed. Submit a new request.")
    for entry in snap.payload.get("entries", []):
        current = db.get(MemoryEntry, entry["id"])
        if (
            not current
            or current.status != "active"
            or current.version != entry["version"]
            or (current.expires_at and aware(current.expires_at) <= utcnow())
        ):
            raise AppError(
                "CONFLICT", "The memory context changed or expired. Submit a new request."
            )
    payload = snap.payload
    if payload.get("version") in {
        "query_conditioned_memory_v3",
        "query_conditioned_memory_v4",
        "query_conditioned_memory_v5",
    }:
        payload = {
            k: v for k, v in payload.items() if k not in {"selection_trace", "selection_policy"}
        }
    return {**payload, "snapshot_id": snap.id, "revision": snap.revocation_epoch}


def enqueue_extraction(
    db, owner_id, message, config, use_profile, *, policy_version="explicit_learning_memory_v1"
):
    if policy_version == "typed_memory_v5":
        from .memory_writer_v5 import enqueue

        return enqueue(db, owner_id, message, config, use_profile, policy_version=policy_version)
    if policy_version == "typed_memory_v4":
        from .memory_writer_v4 import enqueue

        return enqueue(db, owner_id, message, config, use_profile, policy_version=policy_version)
    if policy_version != "explicit_learning_memory_v1":
        from .memory_v2 import enqueue

        return enqueue(db, owner_id, message, config, use_profile, policy_version=policy_version)
    from personalisation.memory import eligible

    state = settings_for(db, owner_id)
    if not state.enabled or not use_profile or not eligible(message.content):
        return
    if db.scalar(
        select(MemorySuppression).where(
            MemorySuppression.owner_id == owner_id,
            MemorySuppression.source_message_id == message.id,
        )
    ):
        return
    db.add(
        Job(
            owner_id=owner_id,
            kind="memory",
            payload={
                "source_message_id": message.id,
                "epoch": state.revocation_epoch,
                "model_config": config,
                "budget": {"max_calls": 2, "max_active_seconds": 90},
            },
        )
    )


def execute_memory(engine, settings, job_id, token):
    with sessionmaker(bind=engine)() as dispatch_db:
        dispatch_job = dispatch_db.get(Job, job_id)
        if dispatch_job.payload.get("memory_policy_version") == "typed_memory_v5":
            from .memory_writer_v5 import execute

            return execute(engine, settings, job_id, token)
        if dispatch_job.payload.get("memory_policy_version") == "typed_memory_v4":
            from .memory_writer_v4 import execute

            return execute(engine, settings, job_id, token)
        if dispatch_job.payload.get("memory_policy_version") == "typed_memory_v2":
            from .memory_v2 import execute

            return execute(engine, settings, job_id, token)
        if dispatch_job.payload.get("memory_policy_version") is not None:
            raise ValueError("Unknown memory writer policy")
    from personalisation.memory import extract_memories
    from generation.types import ModelConfig, RequestBudget
    from app.modules.model_settings.service import resolve_secret
    from app.modules.answering.service import ExecutionCancelled

    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def validate(db, job):
        state = settings_for(db, job.owner_id, lock=True)
        if (
            job.state != "running"
            or job.execution_token != token
            or not state.enabled
            or job.payload.get("epoch") != state.revocation_epoch
        ):
            raise ExecutionCancelled()
        message = db.get(Message, job.payload["source_message_id"])
        session = db.get(ChatSession, message.session_id) if message else None
        if not message or not session or session.user_id != job.owner_id or session.deleted_at:
            raise AppError(
                "CONFLICT", "The source conversation is no longer available for memory extraction."
            )
        return message

    with factory() as db:
        job = db.get(Job, job_id)
        message = validate(db, job)
        text, source_id, owner_id = message.content, message.id, job.owner_id
        config = ModelConfig.from_dict(job.payload["model_config"])
        budget = RequestBudget.from_dict(job.payload["budget"])
        key = resolve_secret(db, settings, config.configuration_id)
        db.commit()

    def on_attempt(event):
        with factory() as db:
            settings_for(db, owner_id, lock=True)
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            validate(db, job)
            job.payload = {**job.payload, "budget": event["budget"]}
            job.stage = "memory_extraction"
            job.updated_at = utcnow()
            count = len(list(db.scalars(select(Attempt).where(Attempt.job_id == job_id))))
            db.add(Attempt(job_id=job_id, sequence=count + 1, payload=event))
            db.commit()

    try:
        result = extract_memories(text, config, budget, on_attempt, api_key=key)
    finally:
        key = None
    with factory() as db:
        settings_for(db, owner_id, lock=True)
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        validate(db, job)
        if result["error"]:
            job.state, job.stage, job.error = "failed", "failed", result["error"]
        else:
            saved = []
            for item in result["entries"]:
                canonical = digest(
                    [
                        item["category"],
                        item["attribute"].strip().casefold(),
                        item["scope"].strip().casefold(),
                    ]
                )
                if db.scalar(
                    select(MemorySuppression).where(
                        MemorySuppression.owner_id == owner_id,
                        MemorySuppression.source_message_id == source_id,
                    )
                ):
                    continue
                row = db.scalar(
                    select(MemoryEntry).where(
                        MemoryEntry.owner_id == owner_id,
                        MemoryEntry.category == item["category"],
                        MemoryEntry.canonical_key == canonical,
                    )
                )
                if row and row.content == item["content"] and row.status == "active":
                    continue
                if row is None:
                    row = MemoryEntry(
                        owner_id=owner_id,
                        category=item["category"],
                        canonical_key=canonical,
                        content=item["content"],
                        scope=item["scope"],
                        source_message_id=source_id,
                        status="active",
                        expires_at=parse_expiry(item["expires_at"]),
                    )
                    db.add(row)
                    db.flush()
                else:
                    row.version += 1
                    row.content, row.scope, row.source_message_id, row.status = (
                        item["content"],
                        item["scope"],
                        source_id,
                        "paused" if row.status == "paused" else "active",
                    )
                    row.expires_at = parse_expiry(item["expires_at"])
                db.add(
                    MemoryRevision(
                        entry_id=row.id,
                        entry_version=row.version,
                        content=row.content,
                        source_message_id=source_id,
                        action="explicit_auto_save",
                    )
                )
                saved.append(
                    {
                        "memory_id": row.id,
                        "version": row.version,
                        "message": "Learning memory saved.",
                        "action": "undo_save",
                    }
                )
            job.payload = {**job.payload, "saved": saved}
            job.state, job.stage = "succeeded", "complete"
        job.payload = {**job.payload, "budget": result["budget"], "usage": result["usage"]}
        job.execution_token = None
        db.commit()
