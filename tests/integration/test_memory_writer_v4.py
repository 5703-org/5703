"""Proposed owned PostgreSQL write, replay, suppression and async identity checks."""

from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app.modules.answering.models import AnswerRequest, Job
from app.modules.answering.service import ExecutionCancelled
from app.modules.learning_state import memory, memory_v2 as old, memory_writer_v4 as writer
from app.modules.learning_state.models import MemoryEntry, MemoryRevision, MemoryWriteEvent
from contracts.learning import MemoryControlsUpdate
from generation.types import ModelConfig
from personalisation import memory_v2, memory_writer_v4
from .test_memory_preview_v3 import authored, preview
from .test_memory_v2 import message, setup


@pytest.fixture(autouse=True)
def no_cloud(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("V4 scope acceptance fixtures forbid provider calls")

    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)


@pytest.mark.parametrize(
    "text",
    [
        "I prefer examples for botany.",
        "I prefer examples for biology or chemistry.",
        "I prefer examples for biology but not genetics.",
        "I prefer examples, for example in biology.",
    ],
)
def test_normal_http_uncertain_scope_withholds_without_global_or_async_fallback(runtime, text):
    email, owner, _ = authored(runtime, [])
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Conditional write"}
    ).json()["data"]
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
            event = db.scalar(
                select(MemoryWriteEvent).where(
                    MemoryWriteEvent.owner_id == owner,
                    MemoryWriteEvent.source_message_id == request.user_message_id,
                )
            )
            assert event.status == "no_op" and event.operations[0]["operation"] == "NO_OP"
            assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
            assert not list(
                db.scalars(select(Job).where(Job.owner_id == owner, Job.kind == "memory"))
            )
        assert preview(runtime, email, "Explain ATP.")["entries"] == []
    finally:
        result = runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers)
        assert result.status_code == 200 and result.json()["data"]["state"] == "cancelled"


def source_write(db, actor, session, text, index):
    source = message(db, session, text, index)
    event = old.source_event(db, actor.id, source.id)
    outcomes = writer.apply_source(db, actor.id, event, text)
    db.commit()
    return source, event, outcomes


def test_new_scopes_do_not_collide_and_event_replay_is_exactly_once(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source, event, first = source_write(
            db, actor, session, "I prefer examples for photosynthesis.", 1
        )
        repeated = writer.apply_source(db, actor.id, event, source.content)
        assert repeated == first
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRevision)
                .where(MemoryRevision.entry_id == first[0]["memory_id"])
            )
            == 1
        )
        _, _, second = source_write(
            db, actor, session, "I prefer examples for cellular respiration.", 2
        )
        assert first[0]["memory_id"] != second[0]["memory_id"]
        rows = list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id)))
        assert {row.scope for row in rows} == {"photosynthesis", "cellular respiration"}
        assert all(row.writer_version == "typed_memory_v4" for row in rows)


def test_one_event_applies_multiple_explicit_fields_once_and_retains_withheld_conditions(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        text = "I prefer examples for photosynthesis. I prefer bullet points for chemistry. I prefer analogies for botany."
        source, event, outcomes = source_write(db, actor, session, text, 1)
        assert [receipt["operation"] for receipt in outcomes].count("ADD") == 2
        assert [receipt["operation"] for receipt in outcomes].count("NO_OP") == 1
        assert event.status == "applied"
        first = list(event.operations)
        assert writer.apply_source(db, actor.id, event, source.content) == first
        rows = list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id)))
        assert {(row.field_key, row.scope) for row in rows} == {
            ("examples", "photosynthesis"),
            ("format", "chemistry"),
        }
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryRevision)
                .where(MemoryRevision.entry_id.in_([row.id for row in rows]))
            )
            == 2
        )


def test_paused_update_keeps_pause_and_deleted_field_never_resurrects_automatically(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source, event, saved = source_write(
            db, actor, session, "I prefer examples for photosynthesis.", 1
        )
        row = db.get(MemoryEntry, saved[0]["memory_id"])
        memory.update_controls(
            db, actor.id, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
        _, _, updated = source_write(
            db, actor, session, "Actually, I prefer simple examples for photosynthesis.", 2
        )
        row = db.get(MemoryEntry, updated[0]["memory_id"])
        assert row.status == "paused" and row.scope == "photosynthesis"
        memory.delete_entry(db, actor.id, row.id, row.version)
        deleted_version = row.version
        source2, event2, after = source_write(
            db, actor, session, "Remember to use examples for photosynthesis.", 3
        )
        assert (
            after[0]["operation"] == "NO_OP"
            and after[0]["reason"] == "deleted_field_requires_confirmation"
        )
        assert row.status == "deleted" and row.version == deleted_version and row.content is None
        # Replaying the deleted source cannot bypass its suppression with a new key.
        event.status = "pending"
        attempted = writer.apply_source(db, actor.id, event, source.content)
        assert attempted == [] and event.status == "revoked"
        assert row.status == "deleted" and row.version == deleted_version and row.content is None
        # Author-created fault injection in this disposable database exercises
        # source suppression even if a stale event's epoch is made current.
        event.epoch = memory.settings_for(db, actor.id).revocation_epoch
        event.status = "pending"
        attempted = writer.apply_source(db, actor.id, event, source.content)
        assert (
            attempted[0]["operation"] == "NO_OP" and attempted[0]["reason"] == "source_suppressed"
        )
        # A retained V2 fixture used a global key for this exact topic statement.
        # V4 must also block replay under the newly narrowed photosynthesis key.
        legacy_text = "I prefer bullet points for photosynthesis."
        legacy_source = message(db, session, legacy_text, 4)
        legacy_event = old.source_event(db, actor.id, legacy_source.id)
        legacy_outcomes = old.apply_operations(
            db, actor.id, legacy_event, memory_v2.deterministic_operations(legacy_text)
        )
        db.commit()
        legacy_row = db.get(MemoryEntry, legacy_outcomes[0]["memory_id"])
        assert legacy_row.scope == "global" and legacy_row.writer_version == "typed_memory_v2"
        memory.delete_entry(db, actor.id, legacy_row.id, legacy_row.version)
        legacy_deleted_version = legacy_row.version
        legacy_event.epoch = memory.settings_for(db, actor.id).revocation_epoch
        legacy_event.status = "pending"
        narrowed = writer.apply_source(db, actor.id, legacy_event, legacy_source.content)
        assert narrowed[0]["operation"] == "NO_OP" and narrowed[0]["reason"] == "source_suppressed"
        assert legacy_row.status == "deleted" and legacy_row.version == legacy_deleted_version
        assert legacy_source.content == legacy_text
        new_key = memory_v2.canonical("preference", "format", "photosynthesis")
        assert not db.scalar(
            select(MemoryEntry).where(
                MemoryEntry.owner_id == actor.id, MemoryEntry.canonical_key == new_key
            )
        )


def test_async_v4_payload_binds_owner_source_sequence_policy_and_same_event(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        text = "I prefer step-by-step explanations for photosynthesis."
        source = message(db, session, text, 1)
        event = old.source_event(db, actor.id, source.id)
        assert writer.apply_source(db, actor.id, event, text) == [] and event.status == "pending"
        config = ModelConfig().to_dict()
        writer.enqueue(db, actor.id, source, config, True, policy_version="typed_memory_v4")
        db.flush()
        job = db.scalar(select(Job).where(Job.owner_id == actor.id, Job.kind == "memory"))
        assert job.payload["memory_policy_version"] == "typed_memory_v4"
        assert (
            job.payload["event_id"] == event.id and job.payload["event_sequence"] == event.sequence
        )
        assert job.payload["source_hash"] == memory_v2.digest(text)
        assert job.payload["condition_policy"]["writer_version"] == memory_writer_v4.WRITER_VERSION
        writer.enqueue(db, actor.id, source, config, True, policy_version="typed_memory_v4")
        db.flush()
        assert (
            db.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.owner_id == actor.id, Job.kind == "memory")
            )
            == 1
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_message_id", "missing"),
        ("source_hash", "0" * 64),
        ("event_sequence", 999),
        ("memory_policy_version", "typed_memory_v2"),
        ("condition_policy", None),
        ("epoch", 999),
        ("event_id", "missing"),
    ],
)
def test_async_frozen_identity_failure_rejects_before_any_provider(runtime, field, value):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "I prefer step-by-step explanations for photosynthesis.", 1)
        writer.enqueue(
            db, actor.id, source, ModelConfig().to_dict(), True, policy_version="typed_memory_v4"
        )
        db.flush()
        job = db.scalar(select(Job).where(Job.owner_id == actor.id, Job.kind == "memory"))
        token = str(uuid4())
        job.state, job.execution_token = "running", token
        job.payload = {**job.payload, field: value}
        job_id, engine = job.id, db.get_bind()
        db.commit()
    with pytest.raises(ExecutionCancelled):
        writer.execute(engine, runtime.settings, job_id, token)


def test_bad_configured_policy_cannot_schedule_memory_cloud_work(runtime, tmp_path):
    email, owner, _ = authored(runtime, [])
    path = tmp_path / "private-malformed-policy.json"
    path.write_text("null", encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(path)
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Unavailable policy"}
    ).json()["data"]
    response = runtime.client.post(
        f"/api/v1/sessions/{session['id']}/messages",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"content": "I prefer examples for photosynthesis."},
    )
    assert response.status_code == 202
    receipt = response.json()["data"]
    try:
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            assert request.command["memory_stage"]["code"] == "MEMORY_POLICY_UNAVAILABLE"
            assert not list(
                db.scalars(select(Job).where(Job.owner_id == owner, Job.kind == "memory"))
            )
            assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
    finally:
        cancelled = runtime.client.post(f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers)
        assert cancelled.status_code == 200 and cancelled.json()["data"]["state"] == "cancelled"
