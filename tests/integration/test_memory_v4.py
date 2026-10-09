"""Proposed real PostgreSQL/HTTP checks; authored fixtures and no answer worker."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest, Message
from app.modules.learning_state import memory
from app.modules.learning_state.models import MemoryEntry
from contracts.learning import MemoryControlsUpdate, MemoryEdit
from personalisation import memory_v3, memory_v4, memory_v5
from .test_memory_preview_v3 import authored, preview
from .test_memory_v2 import Counter


@pytest.fixture(autouse=True)
def no_cloud(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Preparation and preview must make zero provider calls")

    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)


def test_normal_source_submission_freezes_narrowed_scope_and_cancels_its_owned_answer(
    runtime,
):
    email, owner, _ = authored(runtime, [])
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Owned conditional source"}
    ).json()["data"]
    text = "I prefer examples for photosynthesis."
    response = runtime.client.post(
        f"/api/v1/sessions/{session['id']}/messages",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"content": text},
    )
    assert response.status_code == 202, response.text
    receipt = response.json()["data"]
    try:
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            assert request.command["memory_policy_version"] == memory_v5.SELECTOR_VERSION
            assert request.command["memory_selection_policy"] == memory_v5.freeze_policy()
            original = db.get(Message, request.user_message_id)
            row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == owner))
            assert original.content == text and row.content == text
            assert row.scope == "photosynthesis" and row.writer_version == "typed_memory_v5"
        assert not preview(runtime, email, "Explain cellular respiration.")["entries"]
        current = preview(runtime, email, "Explain photosynthesis.")
        assert current["policy_version"] == memory_v5.SELECTOR_VERSION
        assert current["entries"][0]["scope"] == "photosynthesis"
    finally:
        cancelled = runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers)
        assert cancelled.status_code == 200 and cancelled.json()["data"]["state"] == "cancelled"


def test_old_snapshot_and_configured_v3_keep_the_recorded_version(runtime, tmp_path):
    text = "I prefer examples for photosynthesis."
    email, owner, ids = authored(runtime, [text])
    with runtime.db() as db:
        old = memory.freeze_memory(
            db,
            owner,
            "Explain cellular respiration.",
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            semantic_policy=memory_v3.freeze_policy(),
            counter=Counter(),
        )
        db.commit()
        snapshot_id = old.id
    assert not preview(runtime, email, "Explain cellular respiration.")["entries"]
    with runtime.db() as db:
        saved = memory.read_snapshot(db, owner, snapshot_id)
        assert saved["version"] == memory_v3.SELECTOR_VERSION
        assert [entry["id"] for entry in saved["entries"]] == ids
    path = tmp_path / "explicit-historical-policy.json"
    path.write_text(json.dumps(memory_v3.freeze_policy()), encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(path)
    historical = preview(runtime, email, "Explain cellular respiration.")
    assert historical["policy_version"] == memory_v3.SELECTOR_VERSION
    assert [entry["id"] for entry in historical["entries"]] == ids


def test_owned_pause_delete_and_foreign_source_keep_the_guard_closed(runtime):
    text = "I prefer examples for photosynthesis."
    email, owner, ids = authored(runtime, [text])
    assert preview(runtime, email, "Explain photosynthesis.")["entries"]
    assert not preview(runtime, "student2@example.com", "Explain photosynthesis.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
    assert not preview(runtime, email, "Explain photosynthesis.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
    other, foreign, foreign_ids = authored(runtime, [text])
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        source = db.get(MemoryEntry, foreign_ids[0])
        row.source_message_id = source.source_message_id
        db.commit()
    assert not preview(runtime, email, "Explain photosynthesis.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.delete_entry(db, owner, row.id, row.version)
    assert not preview(runtime, email, "Explain photosynthesis.")["entries"]
    assert preview(runtime, other, "Explain photosynthesis.")["entries"]


def test_exact_user_edit_and_controls_preserve_original_chat_and_snapshot_revoke(runtime):
    text = "I prefer examples for photosynthesis."
    email, owner, ids = authored(runtime, [text])
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        source_id = row.source_message_id
        old = memory.freeze_memory(
            db,
            owner,
            "Explain photosynthesis.",
            True,
            policy_version=memory_v4.SELECTOR_VERSION,
            semantic_policy=memory_v4.freeze_policy(),
            counter=Counter(),
        )
        db.commit()
        snapshot_id = old.id
        memory.edit_entry(
            db,
            owner,
            row.id,
            MemoryEdit(
                version=row.version,
                content="Use bullet points.",
                scope="biology",
                field_key="format",
            ),
        )
        assert db.get(Message, source_id).content == text
        with pytest.raises(AppError) as caught:
            memory.read_snapshot(db, owner, snapshot_id)
        assert caught.value.code == "CONFLICT"
        row = db.get(MemoryEntry, row.id)
        revision_version = row.version
        assert row.content == "Use bullet points." and row.source_message_id == source_id
    updated = preview(runtime, email, "Explain ATP.")
    assert updated["entries"][0]["version"] == revision_version
    assert updated["entries"][0]["scope"] == "biology"
    assert not preview(runtime, email, "Explain chemical orbitals.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
    assert not preview(runtime, email, "Explain ATP.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
    assert preview(runtime, email, "Explain ATP.")["entries"][0]["content"] == "Use bullet points."


def test_literal_botany_scope_requires_owned_ui_confirmation_and_preserves_edit_resume(runtime):
    text = "I prefer examples for botany."
    email, owner, ids = authored(runtime, [text], scopes=["botany"])
    assert preview(runtime, email, "Explain plant structure in botany.")["entries"]
    assert not preview(runtime, email, "Explain ATP in biology.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.edit_entry(
            db,
            owner,
            row.id,
            MemoryEdit(
                version=row.version, content="Use examples.", scope="botany", field_key="examples"
            ),
        )
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
    assert not preview(runtime, email, "Explain plant structure in botany.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
    assert preview(runtime, email, "Explain plant structure in botany.")["entries"]
    assert not preview(runtime, email, "Explain ATP.")["entries"]
