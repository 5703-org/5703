"""Disposable PostgreSQL/API and actual mock worker; authored rules, no quality labels."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest, Job, Message
from app.modules.learning_state import memory, memory_writer_v5
from app.modules.learning_state.models import MemoryEntry, MemorySnapshot, MemoryWriteEvent
from contracts.learning import MemoryControlsUpdate
from generation.types import ModelConfig
from personalisation import memory_v4, memory_v5
from .test_memory_preview_v3 import authored, preview
from .test_memory_v2 import Counter, message, setup


SOURCE = "For biology questions, I prefer detailed explanations."


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("This is authored software verification, not a provider or quality study")

    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)


def submit_source(runtime, email):
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Owned leading preference"}
    ).json()["data"]
    result = runtime.client.post(
        f"/api/v1/sessions/{session['id']}/messages",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"content": SOURCE},
    )
    assert result.status_code == 202, result.text
    return result.json()["data"], headers


def test_actual_submit_writer_snapshot_and_cross_session_precedence_are_coherent(runtime):
    email, owner, _ = authored(runtime, [])
    receipt, headers = submit_source(runtime, email)
    try:
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            assert request.command["memory_policy_version"] == memory_v5.SELECTOR_VERSION
            assert request.command["memory_selection_policy"] == memory_v5.freeze_policy()
            row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == owner))
            assert (
                row.content == SOURCE
                and row.scope == "biology"
                and row.writer_version == "typed_memory_v5"
            )
            original = db.get(Message, row.source_message_id)
            assert original.id == request.user_message_id and original.content == SOURCE
            assert (
                db.scalar(
                    select(MemoryWriteEvent).where(
                        MemoryWriteEvent.source_message_id == original.id
                    )
                ).status
                == "applied"
            )
            identity = row.id
        current = preview(runtime, email, "Explain photosynthesis.")
        assert current["policy_version"] == memory_v5.SELECTOR_VERSION
        assert [row["id"] for row in current["entries"]] == [identity]
        assert not preview(runtime, email, "Explain sodium orbitals in chemistry.")["entries"]
        short = preview(runtime, email, "Explain photosynthesis. Give a short explanation.")
        assert short["fields"][0]["verification"] == "current_user_instruction"
        assert not preview(runtime, "student2@example.com", "Explain photosynthesis.")["entries"]
    finally:
        stopped = runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers)
        assert stopped.status_code == 200


def test_explicit_frozen_v4_request_keeps_old_source_rejection_and_snapshot_version(
    runtime, tmp_path
):
    file = tmp_path / "recorded-v4.json"
    file.write_text(json.dumps(memory_v4.freeze_policy()), encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(file)
    email, owner, _ = authored(runtime, [])
    receipt, headers = submit_source(runtime, email)
    try:
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            assert request.command["memory_policy_version"] == memory_v4.SELECTOR_VERSION
            assert request.command["memory_selection_policy"] == memory_v4.freeze_policy()
            assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
            snapshot = db.get(MemorySnapshot, request.command["memory_snapshot_id"])
            assert snapshot.payload["version"] == memory_v4.SELECTOR_VERSION
        assert not preview(runtime, email, "Explain photosynthesis.")["entries"]
    finally:
        runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers)


def test_pause_resume_delete_and_original_source_revocation_remain_owner_scoped(runtime):
    email, owner, ids = authored(runtime, [SOURCE], scopes=["biology"])
    with runtime.db() as db:
        snap = memory.freeze_memory(
            db,
            owner,
            "Explain photosynthesis.",
            True,
            policy_version=memory_v5.SELECTOR_VERSION,
            semantic_policy=memory_v5.freeze_policy(),
            counter=Counter(),
        )
        db.commit()
        snapshot_id = snap.id
        row = db.get(MemoryEntry, ids[0])
        original_source = row.source_message_id
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
    assert not preview(runtime, email, "Explain photosynthesis.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
    assert [e["id"] for e in preview(runtime, email, "Explain photosynthesis.")["entries"]] == ids
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.delete_entry(db, owner, row.id, row.version)
        assert db.get(Message, original_source).content == SOURCE
        with pytest.raises(AppError):
            memory.read_snapshot(db, owner, snapshot_id)
    assert not preview(runtime, email, "Explain photosynthesis.")["entries"]


def enqueue_owned(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, SOURCE, 1)
        memory_writer_v5.enqueue(
            db, actor.id, source, ModelConfig().to_dict(), True, policy_version="typed_memory_v5"
        )
        job = db.scalar(select(Job).where(Job.owner_id == actor.id, Job.kind == "memory"))
        db.commit()
        return job.id, actor.id, source.id


def test_actual_background_worker_consumes_v5_frozen_policy_without_cloud(runtime):
    identity, owner, source_id = enqueue_owned(runtime)
    runtime.work()
    with runtime.db() as db:
        job = db.get(Job, identity)
        assert job.state == "succeeded", job.error
        assert job.payload["memory_policy_version"] == "typed_memory_v5"
        assert job.payload["condition_policy"] == memory_v5.freeze_policy()
        row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == owner))
        assert (
            row.content == SOURCE and row.scope == "biology" and row.source_message_id == source_id
        )
        assert row.writer_version == "typed_memory_v5"
        assert row.source_details["writer_version"] == "typed_memory_v5"
        assert job.payload["budget"]["consumed_calls"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_hash", "0" * 64),
        ("condition_policy", memory_v4.freeze_policy()),
        ("memory_policy_version", "typed_memory_v999"),
    ],
)
def test_worker_payload_identity_tampering_fails_before_provider_or_memory_write(
    runtime, field, value
):
    identity, owner, _ = enqueue_owned(runtime)
    with runtime.db() as db:
        job = db.get(Job, identity)
        job.payload = {**job.payload, field: value}
        db.commit()
    runtime.work()
    with runtime.db() as db:
        job = db.get(Job, identity)
        assert job.state != "succeeded"
        assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
