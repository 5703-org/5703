"""Real disposable PostgreSQL ownership, expiry and revocation checks for v3."""

import datetime as dt
import pytest
from sqlalchemy import select

from app.db.base import utcnow
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.learning_state import memory
from app.modules.learning_state.models import MemoryEntry
from personalisation import memory_v3
from contracts.learning import MemoryControlsUpdate
from tests.integration.test_memory_v2 import setup, message, save, Counter


def freeze(db, actor, **kwargs):
    return memory.freeze_memory(
        db,
        actor.id,
        "How do stomata respond?",
        True,
        policy_version=memory_v3.SELECTOR_VERSION,
        counter=Counter(),
        **kwargs,
    )


def semantic():
    return memory_v3.freeze_policy(enabled=True, threshold=0.85, calibration_id="a" * 64)


def test_frozen_chemistry_preference_and_explicit_length_have_distinct_precedence(runtime):
    from personalisation.compiler import compile_profile

    with runtime.db() as db:
        actor, session = setup(db)
        general = message(db, session, "I prefer detailed explanations.", 1)
        scoped = message(db, session, "I prefer detailed explanations for chemistry.", 2)
        save(db, actor, general)
        save(db, actor, scoped)
        query = "Why are eg orbitals higher in an octahedral complex?"
        scoped_snapshot = memory.freeze_memory(
            db,
            actor.id,
            query,
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            counter=Counter(),
        )
        assert [e["scope"] for e in scoped_snapshot.payload["entries"]] == ["chemistry"]
        old_hash = scoped_snapshot.content_hash
        current = message(
            db,
            session,
            "Please answer briefly: why are eg orbitals higher in an octahedral complex?",
            3,
        )
        profile = compile_profile({"style": "detailed"}, turn_message=current.content)
        snap = memory.freeze_memory(
            db,
            actor.id,
            current.content,
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            current_message_id=current.id,
            profile=profile,
            counter=Counter(),
        )
        assert snap.payload["query_topics"] == ["chemistry"]
        assert snap.payload["entries"] == []
        field = snap.payload["fields"][0]
        assert field["field_key"] == "detail_level"
        assert field["verification"] == "current_user_instruction"
        assert field["source"] == {"message_id": current.id}
        assert profile["turn_override"]["style"] == "concise"
        prompt = memory.read_snapshot(db, actor.id, snap.id)
        assert prompt["fields"][0] == field
        assert scoped_snapshot.content_hash == old_hash
        assert [e["scope"] for e in scoped_snapshot.payload["entries"]] == ["chemistry"]


def test_v3_owned_source_reread_revocation_and_prompt_projection(runtime, monkeypatch):
    monkeypatch.setattr(memory_v3, "scope_scores", lambda q, s: [0.93] * len(s))
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "For botany, I prefer detailed explanations.", 1)
        save(db, actor, source)
        row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id))
        memory.update_controls(
            db,
            actor.id,
            row.id,
            MemoryControlsUpdate(
                version=row.version, paused=False, match_policy="calibrated_semantic"
            ),
        )
        snap = freeze(db, actor, semantic_policy=semantic())
        assert snap.payload["entries"][0]["scope"] == "botany"
        assert (
            snap.payload["selection_trace"]["source_rereads"][0]["reason"] == "owned_source_reread"
        )
        prompt = memory.read_snapshot(db, actor.id, snap.id)
        assert "selection_trace" not in prompt and "selection_policy" not in prompt
        outsider = db.scalar(select(User).where(User.email == "student2@example.com"))
        with pytest.raises(AppError):
            memory.read_snapshot(db, outsider.id, snap.id)
        row = db.get(MemoryEntry, snap.payload["entries"][0]["id"])
        memory.delete_entry(db, actor.id, row.id, row.version)
        with pytest.raises(AppError):
            memory.read_snapshot(db, actor.id, snap.id)
        assert snap.payload.get("revoked") is True and "selection_trace" not in snap.payload


def test_v3_rejects_foreign_source_and_expired_entry(runtime, monkeypatch):
    monkeypatch.setattr(memory_v3, "scope_scores", lambda q, s: [0.93] * len(s))
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "For botany, I prefer detailed explanations.", 1)
        save(db, actor, source)
        row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id))
        memory.update_controls(
            db,
            actor.id,
            row.id,
            MemoryControlsUpdate(
                version=row.version, paused=False, match_policy="calibrated_semantic"
            ),
        )
        other, other_session = setup(db)
        foreign = message(db, other_session, source.content, 1)
        row.source_message_id = foreign.id
        db.flush()
        snap = freeze(db, actor, semantic_policy=semantic())
        assert snap.payload["entries"] == []
        assert (
            snap.payload["selection_trace"]["source_rereads"][0]["reason"]
            == "conditional_source_unavailable"
        )
        row.source_message_id = source.id
        row.expires_at = utcnow() - dt.timedelta(seconds=1)
        db.flush()
        expired = freeze(db, actor, semantic_policy=semantic())
        assert expired.payload["entries"] == []
        assert expired.payload["selection_trace"]["source_rereads"] == []


def test_disabled_v3_matches_stored_v2_snapshot_and_enabled_switch_is_explicit(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "I prefer detailed explanations for biology.", 1)
        save(db, actor, source)
        old = memory.freeze_memory(
            db,
            actor.id,
            "What is photosynthesis?",
            True,
            policy_version="query_conditioned_memory_v2",
            counter=Counter(),
        )
        new = memory.freeze_memory(
            db,
            actor.id,
            "What is photosynthesis?",
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            counter=Counter(),
        )
        projected = {
            k: v for k, v in new.payload.items() if k not in {"selection_trace", "selection_policy"}
        }
        projected["version"] = "query_conditioned_memory_v2"
        assert projected == old.payload
        assert new.payload["selection_trace"]["status"] == "disabled_rules_only"
