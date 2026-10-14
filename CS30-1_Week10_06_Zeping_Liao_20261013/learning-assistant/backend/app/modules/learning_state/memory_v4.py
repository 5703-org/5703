"""Owned snapshots for exact, versioned preference conditions."""

from sqlalchemy import select

from app.db.base import utcnow
from app.modules.identity.models import User
from personalisation import memory_v2 as rules, memory_v4 as engine
from . import memory_v2, memory_writer_v4
from .models import MemoryEntry, MemoryRevision, MemorySnapshot, MemoryWriteEvent
from .memory_v3 import source_reader as chat_source_reader


def source_reader(db, owner_id):
    original_reader = chat_source_reader(db, owner_id)

    def read(entry):
        from . import memory

        row = memory.entry_owned(db, owner_id, entry["id"])
        if (
            row.version != entry["version"]
            or row.status != "active"
            or (row.expires_at and memory.aware(row.expires_at) <= utcnow())
            or row.source_message_id != entry.get("source_message_id")
            or row.content != entry.get("content")
            or row.scope != entry.get("scope")
            or row.field_key != entry.get("field_key")
            or row.verification != entry.get("verification")
            or (row.source_details or {}) != (entry.get("provenance") or {})
        ):
            return None
        provenance = row.source_details or {}
        if provenance.get("kind") != "user_correction":
            source = original_reader(entry)
            if (
                source
                and provenance.get("kind") == "user_confirmed_statement"
                and provenance.get("recorded_by") == owner_id
                and row.verification == "explicit_user_statement"
            ):
                source.update(source_kind="user_confirmed_statement", recorded_by=owner_id)
            return source
        if provenance.get("recorded_by") != owner_id or row.verification != "user_corrected":
            return None
        revisions, events = [], {}
        for revision in db.scalars(
            select(MemoryRevision)
            .join(MemoryEntry, MemoryEntry.id == MemoryRevision.entry_id)
            .where(
                MemoryEntry.owner_id == owner_id,
                MemoryEntry.id == row.id,
                MemoryEntry.version == row.version,
                MemoryRevision.entry_version <= row.version,
            )
            .order_by(MemoryRevision.entry_version.desc())
            .limit(engine.MAX_CORRECTION_REVISIONS + 1)
        ):
            if len(revisions) == engine.MAX_CORRECTION_REVISIONS:
                return None
            details = revision.details or {}
            sequence = details.get("source_event_sequence")
            event = db.scalar(
                select(MemoryWriteEvent).where(
                    MemoryWriteEvent.owner_id == owner_id,
                    MemoryWriteEvent.sequence == sequence,
                )
            )
            revisions.append(
                {
                    "id": revision.id,
                    "entry_id": revision.entry_id,
                    "entry_version": revision.entry_version,
                    "content": revision.content,
                    "source_message_id": revision.source_message_id,
                    "action": revision.action,
                    "details": details,
                }
            )
            if event:
                events[sequence] = {
                    "id": event.id,
                    "owner_id": event.owner_id,
                    "sequence": event.sequence,
                    "status": event.status,
                    "operations": event.operations,
                }
            if revision.action == "user_correction":
                break
        return engine.correction_source(entry, owner_id, revisions, events, row.canonical_key)

    return read


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
    semantic_policy=None,
):
    from . import memory

    if policy_version != engine.SELECTOR_VERSION:
        raise ValueError("Unknown semantic memory selector")
    policy = engine.validate_policy(semantic_policy)
    settings = memory.settings_for(db, owner_id, lock=True)
    if not use_profile or not settings.enabled:
        return None
    memory_v2.expire_entries(db, owner_id)
    if current_message_id and rules.eligible(question):
        event = memory_v2.source_event(db, owner_id, current_message_id)
        if event.status == "pending":
            memory_writer_v4.apply_source(db, owner_id, event, question)
    entries = [
        memory.entry_out(row)
        for row in db.scalars(
            select(MemoryEntry)
            .where(MemoryEntry.owner_id == owner_id, MemoryEntry.status == "active")
            .order_by(MemoryEntry.updated_at.desc())
        )
        if not row.expires_at or memory.aware(row.expires_at) > utcnow()
    ]
    selection = engine.select(
        entries,
        question,
        profile,
        context,
        policy=policy,
        source_reader=source_reader(db, owner_id),
        current_message_id=current_message_id,
        counter=counter,
    )
    payload = selection.state
    payload["workspace_id"] = db.get(User, owner_id).workspace_id
    # Diagnostics remain in the revocable private snapshot, outside the prompt budget.
    payload["selection_trace"] = selection.trace
    payload["selection_policy"] = policy
    snap = MemorySnapshot(
        owner_id=owner_id,
        revocation_epoch=settings.revocation_epoch,
        payload=payload,
        content_hash=rules.digest(payload),
    )
    db.add(snap)
    db.flush()
    return snap
