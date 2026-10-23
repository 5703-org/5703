"""Real migrated PostgreSQL controls and cross-session memory lifecycle."""

from sqlalchemy import select
from app.modules.learning.models import ChatSession
from app.modules.learning_state import memory, memory_v2
from app.modules.learning_state.models import MemoryEntry, MemoryRevision
from contracts.learning import MemoryControlsUpdate, MemoryEdit
from personalisation.memory_v2 import deterministic_operations
from .test_memory_v2 import setup, message, save, Counter


def preview(db, actor, question="Explain ATP."):
    return memory.freeze_memory(
        db,
        actor.id,
        question,
        True,
        policy_version="query_conditioned_memory_v3",
        counter=Counter(),
    )


def test_owned_pause_invalidates_snapshot_keeps_content_and_fences_old_writer(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "I prefer detailed explanations for biology.", 1)
        _, receipts = save(db, actor, source)
        row = db.get(MemoryEntry, receipts[0]["memory_id"])
        snap = preview(db, actor)
        assert snap.payload["entries"][0]["id"] == row.id
        original = row.content
        saved = memory.update_controls(
            db, actor.id, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
        assert saved["status"] == "paused" and saved["content"] == original
        assert snap.invalidated and snap.payload["entries"] == []
        assert preview(db, actor).payload["entries"] == []
        late = memory_v2.source_event(db, actor.id, source.id)
        result = memory_v2.apply_operations(
            db, actor.id, late, deterministic_operations(source.content)
        )
        assert result[0]["reason"] == "stale_source_event" and row.status == "paused"
        later = message(db, session, "I prefer concise explanations for biology.", 2)
        _, later_receipts = save(db, actor, later)
        assert later_receipts[0]["memory_id"] == row.id and row.status == "paused"
        assert row.match_policy == "rules_only" and preview(db, actor).payload["entries"] == []
        updated = memory.edit_entry(
            db,
            actor.id,
            row.id,
            MemoryEdit(
                version=row.version,
                content="Use detailed explanations with examples for biology.",
                scope="biology",
            ),
        )
        assert updated["status"] == "paused"
        resumed = memory.update_controls(
            db, actor.id, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
        assert resumed["status"] == "active" and resumed["match_policy"] == "rules_only"
        assert preview(db, actor).payload["entries"][0]["content"] == updated["content"]


def test_cross_session_latest_scoped_preference_current_override_and_deletion(runtime):
    with runtime.db() as db:
        actor, first = setup(db)
        initial = message(db, first, "I prefer detailed explanations for biology.", 1)
        _, receipts = save(db, actor, initial)
        row_id = receipts[0]["memory_id"]
        second = ChatSession(
            user_id=actor.id, workspace_id=actor.workspace_id, title="Later conversation"
        )
        db.add(second)
        db.flush()
        changed = message(db, second, "I prefer concise explanations for biology.", 1)
        _, changed_receipts = save(db, actor, changed)
        assert changed_receipts[0]["memory_id"] == row_id
        selected = preview(db, actor).payload
        assert selected["entries"][0]["content"] == changed.content
        override = preview(db, actor, "For this answer, explain ATP in detail.").payload
        assert not override["entries"]
        assert override["fields"][0]["verification"] == "current_user_instruction"
        memory.delete_entry(db, actor.id, row_id, changed_receipts[0]["version"])
        assert preview(db, actor).payload["entries"] == []
        row = db.get(MemoryEntry, row_id)
        assert row.content is None
        assert all(
            revision.content is None
            for revision in db.scalars(
                select(MemoryRevision).where(MemoryRevision.entry_id == row_id)
            )
        )
        assert db.get(type(initial), initial.id).content == initial.content


def test_http_controls_are_owner_version_bound_and_do_not_enable_global_memory(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "I prefer detailed explanations for biology.", 1)
        _, receipts = save(db, actor, source)
        identifier, version, email = receipts[0]["memory_id"], receipts[0]["version"], actor.email
        db.commit()
    headers = runtime.headers(email)
    path = "/api/v1/me/memories/" + identifier + "/controls"
    body = {"version": version, "paused": True, "match_policy": "rules_only"}
    outsider = runtime.client.patch(
        path, headers=runtime.headers("student2@example.com"), json=body
    )
    assert outsider.status_code == 404
    result = runtime.client.patch(path, headers=headers, json=body)
    assert result.status_code == 200, result.text
    saved = result.json()["data"]
    assert saved["status"] == "paused" and saved["version"] == version + 1
    stale = runtime.client.patch(path, headers=headers, json={**body, "paused": False})
    assert stale.status_code == 409
    repeated = runtime.client.patch(
        path, headers=headers, json={**body, "version": saved["version"]}
    )
    assert repeated.status_code == 200 and repeated.json()["data"]["version"] == saved["version"]
    changed = runtime.client.patch(
        path,
        headers=headers,
        json={"version": saved["version"], "paused": True, "match_policy": "calibrated_semantic"},
    )
    assert (
        changed.status_code == 200
        and changed.json()["data"]["match_policy"] == "calibrated_semantic"
    )
    invalid = runtime.client.patch(
        path, headers=headers, json={"version": 1, "paused": False, "match_policy": "unchecked"}
    )
    assert invalid.status_code == 422
