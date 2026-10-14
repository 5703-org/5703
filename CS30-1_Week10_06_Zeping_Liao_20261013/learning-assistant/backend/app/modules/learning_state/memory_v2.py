"""Transactional typed memory; all long-term state remains owner scoped."""

import math
from sqlalchemy import select, update
from app.db.base import utcnow
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.answering.models import AnswerRequest, Job, Message
from app.modules.learning.models import ChatSession
from personalisation import memory_v2 as engine
from .models import (
    MemoryEntry,
    MemoryRevision,
    MemorySettings,
    MemorySnapshot,
    MemorySuppression,
    MemoryWriteEvent,
    PrivateAnswerDraft,
)


def owned_source(db, owner_id, message_id, *, role="user"):
    actor = db.get(User, owner_id)
    message = db.get(Message, message_id)
    session = db.get(ChatSession, message.session_id) if message else None
    if (
        not actor
        or actor.status != "active"
        or not message
        or not session
        or session.user_id != owner_id
        or session.workspace_id != actor.workspace_id
        or session.deleted_at
        or (role and message.role != role)
    ):
        raise AppError("NOT_FOUND", "The owned source message is unavailable.")
    return actor, message


def source_event(db, owner_id, message_id=None):
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    actor = db.get(User, owner_id)
    if message_id:
        actor, message = owned_source(db, owner_id, message_id)
        old = db.scalar(
            select(MemoryWriteEvent).where(
                MemoryWriteEvent.owner_id == owner_id,
                MemoryWriteEvent.source_message_id == message_id,
            )
        )
        if old:
            if (
                old.source_hash != engine.digest(message.content)
                or old.workspace_id != actor.workspace_id
            ):
                raise AppError("CONFLICT", "The memory source identity changed.")
            return old
    settings.event_sequence += 1
    event = MemoryWriteEvent(
        owner_id=owner_id,
        workspace_id=actor.workspace_id,
        source_message_id=message_id,
        source_hash=engine.digest(message.content) if message_id else None,
        sequence=settings.event_sequence,
        epoch=settings.revocation_epoch,
        status="pending",
        operations=[],
    )
    db.add(event)
    db.flush()
    return event


def invalidate_entries(db, owner_id, entry_ids):
    """Invalidate affected derivatives without cancelling unrelated extraction jobs."""
    from app.modules.answering.service import cancel_job, lock_request_session

    affected = []
    for snap in db.scalars(
        select(MemorySnapshot).where(
            MemorySnapshot.owner_id == owner_id, MemorySnapshot.invalidated.is_(False)
        )
    ):
        ids = [x["id"] for x in snap.payload.get("entries", [])]
        if set(ids) & set(entry_ids):
            snap.payload = {"entries": [], "entry_ids": ids, "revoked": True}
            snap.invalidated = True
            affected.append(snap.id)
    if not affected:
        return
    db.execute(
        update(PrivateAnswerDraft)
        .where(PrivateAnswerDraft.memory_snapshot_id.in_(affected))
        .values(payload={"redacted": "memory_changed"})
    )
    for req in db.scalars(select(AnswerRequest).where(AnswerRequest.owner_id == owner_id)):
        if req.command.get("memory_snapshot_id") not in affected:
            continue
        lock_request_session(db, req)
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


def expire_entries(db, owner_id):
    from .memory import aware

    expired = []
    for row in db.scalars(
        select(MemoryEntry).where(MemoryEntry.owner_id == owner_id, MemoryEntry.status == "active")
    ):
        if row.expires_at and aware(row.expires_at) <= utcnow():
            expired.append(row.id)
    # Expiration excludes content from every new projection and erases frozen derivatives.
    # The editable item is retained as an expired record; explicit erasure removes its body.
    invalidate_entries(db, owner_id, expired)
    return expired


def erase_content(db, row, sequence):
    sources = {
        r.source_message_id
        for r in db.scalars(select(MemoryRevision).where(MemoryRevision.entry_id == row.id))
        if r.source_message_id
    }
    if row.source_message_id:
        sources.add(row.source_message_id)
    for source_id in sources:
        if not db.scalar(
            select(MemorySuppression).where(
                MemorySuppression.owner_id == row.owner_id,
                MemorySuppression.source_message_id == source_id,
                MemorySuppression.canonical_key == row.canonical_key,
            )
        ):
            db.add(
                MemorySuppression(
                    owner_id=row.owner_id,
                    source_message_id=source_id,
                    canonical_key=row.canonical_key,
                )
            )
    invalidate_entries(db, row.owner_id, [row.id])
    db.execute(
        update(MemoryRevision)
        .where(MemoryRevision.entry_id == row.id)
        .values(content=None, details={})
    )
    row.content = None
    row.source_message_id = None
    row.source_details = {}
    row.scope_topics = []
    row.scope = "deleted"
    row.expires_at = None
    row.status = "deleted"
    row.match_policy = "rules_only"
    row.version += 1
    row.source_event_sequence = sequence
    row.updated_at = utcnow()
    db.add(
        MemoryRevision(
            entry_id=row.id, entry_version=row.version, content=None, action="deleted", details={}
        )
    )


def apply_operations(db, owner_id, event, operations, *, provenance=None):
    """M3/M4 share this writer. A later event always fences an earlier event."""
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    actor = db.get(User, owner_id)
    if (
        not settings.enabled
        or event.epoch != settings.revocation_epoch
        or event.workspace_id != actor.workspace_id
    ):
        event.status = "revoked"
        return []
    text = None
    if event.source_message_id:
        _, message = owned_source(db, owner_id, event.source_message_id)
        text = message.content
        if event.source_hash != engine.digest(text):
            raise AppError("CONFLICT", "Memory source content changed.")
    receipts = []
    for candidate in operations:
        item = engine.validate_operation(candidate, text) if provenance is None else candidate
        key = engine.canonical(item["category"], item["field_key"], item["scope"])
        row = db.scalar(
            select(MemoryEntry).where(
                MemoryEntry.owner_id == owner_id, MemoryEntry.canonical_key == key
            )
        )
        receipt = {"operation": "NO_OP", "field_key": item["field_key"], "reason": "unchanged"}
        if item["operation"] == "NO_OP":
            receipts.append(receipt)
            continue
        suppressed = event.source_message_id and db.scalar(
            select(MemorySuppression).where(
                MemorySuppression.owner_id == owner_id,
                MemorySuppression.source_message_id == event.source_message_id,
                MemorySuppression.canonical_key == key,
            )
        )
        if suppressed or row and row.source_event_sequence > event.sequence:
            receipt["reason"] = "source_suppressed" if suppressed else "stale_source_event"
            receipts.append(receipt)
            continue
        if item["operation"] == "DELETE":
            if row is None:
                row = MemoryEntry(
                    owner_id=owner_id,
                    category=item["category"],
                    canonical_key=key,
                    content=None,
                    scope="deleted",
                    field_key=item["field_key"],
                    scope_topics=[],
                    source_details={},
                    status="deleted",
                    writer_version=engine.WRITER_VERSION,
                    verification="erased",
                    source_event_sequence=event.sequence,
                )
                db.add(row)
                db.flush()
                db.add(
                    MemoryRevision(
                        entry_id=row.id,
                        entry_version=row.version,
                        content=None,
                        action="deleted",
                        details={},
                    )
                )
                receipt.update(
                    operation="DELETE",
                    memory_id=row.id,
                    version=row.version,
                    reason="field_erasure_fence",
                )
            elif row.status != "deleted":
                erase_content(db, row, event.sequence)
                receipt.update(
                    operation="DELETE",
                    memory_id=row.id,
                    version=row.version,
                    reason="explicit_erasure",
                )
            else:
                row.source_event_sequence = event.sequence
                receipt["reason"] = "absent"
            receipts.append(receipt)
            continue
        expiry = memory.parse_expiry(item["expires_at"])
        details = provenance or {
            "kind": "user_statement",
            "source_message_id": event.source_message_id,
            "source_quote": item["source_quote"],
            "source_hash": event.source_hash,
            "event_id": event.id,
            "verification_scope": "exact owned statement; no independent scientific assessment",
        }
        verification = details.get(
            "verification",
            "self_reported"
            if item["category"] == "self_reported_observation"
            else "explicit_user_statement",
        )
        if (
            row
            and row.status == "active"
            and row.content == item["content"]
            and memory.aware(row.expires_at) == expiry
            and row.source_event_sequence == event.sequence
        ):
            receipt.update(memory_id=row.id, version=row.version)
            receipts.append(receipt)
            continue
        operation = "UPDATE" if row else "ADD"
        if row:
            invalidate_entries(db, owner_id, [row.id])
            row.version += 1
        else:
            row = MemoryEntry(
                owner_id=owner_id,
                category=item["category"],
                canonical_key=key,
                status="active",
                source_event_sequence=0,
            )
            db.add(row)
        row.field_key = item["field_key"]
        row.content = item["content"]
        row.scope = engine.scope_name(item["scope"])
        row.scope_topics = engine.topics(row.scope)
        row.source_message_id = event.source_message_id
        row.status = "paused" if row.status == "paused" else "active"
        row.expires_at = expiry
        row.writer_version = engine.WRITER_VERSION
        row.verification = verification
        row.source_details = details
        row.effective_at = utcnow()
        row.source_event_sequence = event.sequence
        row.updated_at = utcnow()
        db.flush()
        db.add(
            MemoryRevision(
                entry_id=row.id,
                entry_version=row.version,
                content=row.content,
                source_message_id=row.source_message_id,
                action=operation.lower(),
                details={
                    "field_key": row.field_key,
                    "scope": row.scope,
                    "verification": verification,
                    "source_event_sequence": event.sequence,
                    "provenance": details,
                },
            )
        )
        receipt.update(
            operation=operation, memory_id=row.id, version=row.version, reason="explicit_source"
        )
        receipts.append(receipt)
    event.operations = receipts
    event.status = "applied" if any(r["operation"] != "NO_OP" for r in receipts) else "no_op"
    db.flush()
    return receipts


def freeze(
    db,
    owner_id,
    question,
    use_profile,
    *,
    policy_version,
    current_message_id=None,
    profile=None,
    context=None,
    counter=None,
):
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    if not use_profile or not settings.enabled:
        return None
    if policy_version not in {engine.WRITER_VERSION, engine.SELECTOR_VERSION}:
        raise ValueError("Unknown learner-state policy")
    expire_entries(db, owner_id)
    if current_message_id and engine.eligible(question):
        event = source_event(db, owner_id, current_message_id)
        # Clear explicit corrections immediately under the same transaction as submission.
        operations = engine.deterministic_operations(question)
        if operations and event.status == "pending":
            apply_operations(db, owner_id, event, operations)
    entries = [
        memory.entry_out(row)
        for row in db.scalars(
            select(MemoryEntry)
            .where(MemoryEntry.owner_id == owner_id, MemoryEntry.status == "active")
            .order_by(MemoryEntry.updated_at.desc())
        )
        if not row.expires_at or memory.aware(row.expires_at) > utcnow()
    ]
    payload = engine.learner_state(
        entries,
        question,
        profile,
        context,
        conditioned=policy_version == engine.SELECTOR_VERSION,
        current_message_id=current_message_id,
        counter=counter,
    )
    payload["workspace_id"] = db.get(User, owner_id).workspace_id
    snap = MemorySnapshot(
        owner_id=owner_id,
        revocation_epoch=settings.revocation_epoch,
        payload=payload,
        content_hash=engine.digest(payload),
    )
    db.add(snap)
    db.flush()
    return snap


def summary(db, owner_id):
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    expire_entries(db, owner_id)
    items = [
        memory.entry_out(row)
        for row in db.scalars(
            select(MemoryEntry)
            .where(MemoryEntry.owner_id == owner_id, MemoryEntry.status == "active")
            .order_by(MemoryEntry.updated_at.desc())
        )
        if not row.expires_at or memory.aware(row.expires_at) > utcnow()
    ]
    rendered = "\n".join(
        f"{row['category'].replace('_', ' ').capitalize()} ({row['scope']}): {row['content']}"
        for row in items
    )
    data = {
        "enabled": settings.enabled,
        "active_count": len(items),
        "summary": rendered
        if settings.enabled
        else "Memory is disabled. Saved entries remain available to inspect and erase.",
        "items": items if settings.enabled else [],
        "limitations": [
            "Generated from active items; assessment performance applies only to its recorded question.",
            "Conversation summaries use a separate lifecycle.",
        ],
    }
    data["version"] = engine.digest(
        {
            "epoch": settings.revocation_epoch,
            "enabled": settings.enabled,
            "items": [(e["id"], e["version"]) for e in items],
        }
    )
    db.commit()
    return data


def processing(db, owner_id):
    output = []
    for row in db.scalars(
        select(MemoryWriteEvent)
        .where(MemoryWriteEvent.owner_id == owner_id)
        .order_by(MemoryWriteEvent.sequence.desc())
        .limit(20)
    ):
        jobs = list(db.scalars(select(Job).where(Job.owner_id == owner_id, Job.kind == "memory")))
        job = next((j for j in jobs if j.payload.get("event_id") == row.id), None)
        state = (
            job.state
            if job and job.state in {"queued", "running", "retry_wait", "failed", "cancelled"}
            else row.status
        )
        error = row.error or (job.error if job else None)
        output.append(
            {
                "event_id": row.id,
                "source_message_id": row.source_message_id,
                "sequence": row.sequence,
                "status": state,
                "operations": row.operations,
                "error": {
                    "code": error.get("code", "MEMORY_STAGE_FAILED"),
                    "message": "Memory processing failed. Current instructions still apply; submit a new request without memory if needed.",
                }
                if error
                else None,
                "created_at": row.created_at.isoformat(),
            }
        )
    return output


def create_record(db, owner_id, body):
    from . import memory

    settings = memory.settings_for(db, owner_id, lock=True)
    if not settings.enabled:
        raise AppError("CONFLICT", "Enable learning memory before saving a new record.")
    _, source = owned_source(db, owner_id, body.source_message_id)
    event = source_event(db, owner_id)
    candidate = {
        "operation": "ADD",
        "category": body.category,
        "field_key": body.field_key,
        "content": body.content,
        "scope": body.scope,
        "source_quote": body.source_quote,
        "expires_at": body.expires_at,
    }
    try:
        item = engine.validate_operation(candidate, source.content)
    except ValueError as exc:
        raise AppError("VALIDATION_FAILED", str(exc)) from exc
    provenance = {
        "kind": "user_confirmed_statement",
        "source_message_id": source.id,
        "source_quote": body.source_quote,
        "source_hash": engine.digest(source.content),
        "recorded_by": owner_id,
        "event_id": event.id,
    }
    result = apply_operations(db, owner_id, event, [item], provenance=provenance)
    row = db.get(MemoryEntry, result[0]["memory_id"])
    row.source_message_id = source.id
    db.commit()
    return memory.entry_out(row)


def record_assessment(db, actor, body):
    from . import memory

    owner_id = body.owner_id or actor.id
    owner = db.get(User, owner_id)
    admin = actor.role.name == "admin"
    if (
        not owner
        or owner.workspace_id != actor.workspace_id
        or (owner_id != actor.id and not admin)
    ):
        raise AppError("NOT_FOUND")
    memory.settings_for(db, owner_id, lock=True)
    _, question = owned_source(db, owner_id, body.question_message_id, role=None)
    _, response = owned_source(db, owner_id, body.response_message_id)
    if (
        question.session_id != response.session_id
        or response.sequence <= question.sequence
        or body.question_quote not in question.content
        or body.response_quote not in response.content
    ):
        raise AppError(
            "VALIDATION_FAILED",
            "Assessment evidence must be ordered, exact messages in one owned conversation.",
        )
    if not body.question_quote.strip() or not body.response_quote.strip():
        raise AppError("VALIDATION_FAILED")
    verification = "recorded_unconfirmed"
    score = body.score
    evaluator = body.evaluator_id
    version = body.evaluator_version
    if body.rubric_kind in {"exact_text", "numeric"}:
        if not admin or body.confirmation != "automatic" or body.expected_answer is None:
            raise AppError(
                "FORBIDDEN", "Automatic assessment requires an authorized recorded rubric."
            )
        if (
            body.response_quote.strip() != response.content.strip()
            or body.question_quote.strip() != question.content.strip()
        ):
            raise AppError(
                "VALIDATION_FAILED",
                "Automatic scoring requires the complete question and learner response, not selected substrings.",
            )
        if body.rubric_kind == "exact_text":
            score = float(
                " ".join(body.response_quote.casefold().split())
                == " ".join(body.expected_answer.casefold().split())
            )
        else:
            try:
                actual, expected = (
                    float(body.response_quote.strip()),
                    float(body.expected_answer.strip()),
                )
                if not math.isfinite(actual) or not math.isfinite(expected):
                    raise ValueError()
                score = float(abs(actual - expected) <= body.tolerance)
            except ValueError as exc:
                raise AppError(
                    "VALIDATION_FAILED", "The numeric rubric requires finite numeric values."
                ) from exc
        verification, evaluator, version = (
            "automatic_rubric_evaluated",
            "server:" + body.rubric_kind,
            "assessment_rubric_v1",
        )
    elif body.confirmation == "human":
        if (
            not admin
            or not body.reviewer_attestation
            or body.evaluator_id != actor.id
            or not actor.full_name.strip()
        ):
            raise AppError(
                "FORBIDDEN",
                "Human confirmation requires a named signed-in reviewer and explicit attestation.",
            )
        verification = "human_attested"
    if score is None:
        raise AppError("VALIDATION_FAILED", "A recorded score or executable rubric is required.")
    event = source_event(db, owner_id)
    # Assessment instances use their own scope identity; two performances are not one mastery field.
    scope = engine.scope_name(body.scope)[:150].rstrip() + " assessment " + response.id
    item = {
        "operation": "ADD",
        "category": "assessment_performance",
        "field_key": "assessment_result",
        "scope": scope,
        "content": f"Recorded performance on one assessment: {score:g} of 1. This result does not establish general mastery.",
        "source_quote": body.response_quote,
        "expires_at": None,
    }
    rubric = {
        "kind": body.rubric_kind,
        "basis": body.scoring_basis,
        "expected_answer": body.expected_answer,
        "tolerance": body.tolerance,
    }
    provenance = {
        "kind": "assessment",
        "verification": verification,
        "question_message_id": question.id,
        "response_message_id": response.id,
        "question_quote": body.question_quote,
        "response_quote": body.response_quote,
        "question_hash": engine.digest(question.content),
        "response_hash": engine.digest(response.content),
        "score": score,
        "rubric": rubric,
        "rubric_hash": engine.digest(rubric),
        "evaluator_id": evaluator,
        "evaluator_version": version,
        "recorded_by": actor.id,
        "reviewer_attestation": body.reviewer_attestation
        if verification == "human_attested"
        else False,
        "event_id": event.id,
    }
    result = apply_operations(db, owner_id, event, [item], provenance=provenance)
    if not result or not result[0].get("memory_id"):
        raise AppError("CONFLICT", "Enable learning memory before recording assessment evidence.")
    row = db.get(MemoryEntry, result[0]["memory_id"])
    row.source_message_id = response.id
    db.commit()
    return memory.entry_out(row)


def enqueue(db, owner_id, message, config, use_profile, *, policy_version):
    from . import memory

    if policy_version not in {engine.WRITER_VERSION, engine.SELECTOR_VERSION}:
        raise ValueError("Unknown memory extraction policy")
    settings = memory.settings_for(db, owner_id, lock=True)
    if not use_profile or not settings.enabled or not engine.eligible(message.content):
        return
    event = source_event(db, owner_id, message.id)
    if db.scalar(
        select(Job.id).where(
            Job.owner_id == owner_id,
            Job.kind == "memory",
            Job.payload["event_id"].as_string() == event.id,
        )
    ):
        return
    # Fully recognized statements have already used the same typed writer during freeze.
    # An asynchronous job remains necessary for unrecognised durable statement shapes.
    if event.status in {"applied", "no_op", "revoked"}:
        return
    db.add(
        Job(
            owner_id=owner_id,
            kind="memory",
            payload={
                "source_message_id": message.id,
                "event_id": event.id,
                "event_sequence": event.sequence,
                "epoch": settings.revocation_epoch,
                "memory_policy_version": engine.WRITER_VERSION,
                "model_config": config,
                "budget": {"max_calls": 2, "max_active_seconds": 90},
            },
        )
    )


def execute(db_engine, settings, job_id, token):
    from sqlalchemy.orm import sessionmaker
    from generation.types import ModelConfig, RequestBudget
    from personalisation.memory_extraction import extract_operations
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
            or event.epoch != state.revocation_epoch
        ):
            raise ExecutionCancelled()
        actor, message = owned_source(db, job.owner_id, job.payload["source_message_id"])
        if event.workspace_id != actor.workspace_id or event.source_hash != engine.digest(
            message.content
        ):
            raise ExecutionCancelled()
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
            job.stage = "memory_extraction_v2"
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
            receipts = apply_operations(db, owner_id, event, result["operations"])
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
            "budget": result["budget"],
            "usage": result["usage"],
        }
        job.execution_token = None
        db.commit()
