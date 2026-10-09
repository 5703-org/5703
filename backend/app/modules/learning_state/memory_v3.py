"""Owned snapshot preparation for opt-in semantic scope supplementation."""

from sqlalchemy import select

from app.db.base import utcnow
from app.modules.identity.models import User
from personalisation import memory_v2 as rules, memory_v3 as engine
from . import memory_v2
from .models import MemoryEntry, MemorySnapshot


def source_reader(db, owner_id):
    def read(entry):
        from . import memory

        row = memory.entry_owned(db, owner_id, entry["id"])
        if (
            row.version != entry["version"]
            or row.status != "active"
            or (row.expires_at and memory.aware(row.expires_at) <= utcnow())
            or row.source_message_id != entry.get("source_message_id")
        ):
            return None
        _, source = memory_v2.owned_source(db, owner_id, row.source_message_id)
        return {
            "owned": True,
            "memory_id": row.id,
            "memory_version": row.version,
            "source_message_id": source.id,
            "source_hash": rules.digest(source.content),
            "content": source.content,
        }

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
        operations = rules.deterministic_operations(question)
        if operations and event.status == "pending":
            memory_v2.apply_operations(db, owner_id, event, operations)
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
