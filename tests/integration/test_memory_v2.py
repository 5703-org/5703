"""Actual PostgreSQL typing, source, erasure and temporal-order invariants."""

import datetime as dt
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db.base import utcnow
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession
from app.modules.answering.models import Message
from app.modules.learning_state import memory, memory_v2
from app.modules.learning_state.models import (
    MemoryEntry,
    MemoryRevision,
    MemorySnapshot,
    MemoryWriteEvent,
)
from contracts.learning import MemoryEdit, MemorySettingsUpdate, MemoryAssessmentCreate
from personalisation.memory_v2 import deterministic_operations


def test_http_summary_preview_record_and_erasure_are_owned(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        src = message(db, session, "I prefer detailed explanations for biology.", 1)
        actor_id, email, source_id = actor.id, actor.email, src.id
        db.commit()
    headers = runtime.headers(email)
    body = {
        "category": "preference",
        "field_key": "detail_level",
        "content": src.content,
        "scope": "biology",
        "source_message_id": source_id,
        "source_quote": src.content,
    }
    response = runtime.client.post("/api/v1/me/memories", headers=headers, json=body)
    assert response.status_code == 200, response.text
    saved = response.json()["data"]
    summary = runtime.client.get("/api/v1/me/memory/summary", headers=headers).json()["data"]
    assert summary["active_count"] == 1 and src.content in summary["summary"]
    preview = runtime.client.post(
        "/api/v1/me/memory/preview",
        headers=headers,
        json={"question": "How does ATP store energy?", "use_profile": True},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["fields"][0]["field_key"] == "detail_level"
    without = runtime.client.post(
        "/api/v1/me/memory/preview",
        headers=headers,
        json={"question": "How does ATP store energy?", "use_profile": False},
    ).json()["data"]
    assert not without["enabled"] and without["fields"] == []
    outsider = runtime.client.post(
        "/api/v1/me/memories", headers=runtime.headers("student2@example.com"), json=body
    )
    assert outsider.status_code in {404, 409}
    erased = runtime.client.request(
        "DELETE",
        "/api/v1/me/memories/" + saved["id"],
        headers=headers,
        json={"version": saved["version"]},
    )
    assert erased.status_code == 200
    summary2 = runtime.client.get("/api/v1/me/memory/summary", headers=headers).json()["data"]
    assert summary2["version"] != summary["version"] and summary2["active_count"] == 0
    with runtime.db() as db:
        assert (
            db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == actor_id)).content is None
        )


def queued_job(runtime):
    from generation.types import ModelConfig
    from app.modules.answering.models import Job

    token = str(uuid4())
    with runtime.db() as db:
        actor, session = setup(db)
        src = message(db, session, "I prefer analogies for biology.", 1)
        memory.enqueue_extraction(
            db, actor.id, src, ModelConfig().to_dict(), True, policy_version="typed_memory_v2"
        )
        db.flush()
        job = db.scalar(select(Job).where(Job.owner_id == actor.id, Job.kind == "memory"))
        job.state, job.execution_token = "running", token
        db.commit()
        return actor.id, job.id, token


def test_async_typed_extraction_uses_actual_writer_and_visible_receipt(runtime):
    from app.modules.answering.models import Job

    owner, job_id, token = queued_job(runtime)
    memory.execute_memory(runtime.engine, runtime.settings, job_id, token)
    with runtime.db() as db:
        job = db.get(Job, job_id)
        assert job.state == "succeeded" and len(job.payload["saved"]) == 1
        rows = memory_v2.processing(db, owner)
        assert rows[0]["status"] == "applied" and rows[0]["operations"][0]["operation"] == "ADD"
        entry = db.get(MemoryEntry, job.payload["saved"][0]["memory_id"])
        assert entry.field_key == "analogies" and entry.verification == "explicit_user_statement"


def test_disable_during_extraction_fences_publication_and_keeps_cancel_metadata(
    runtime, monkeypatch
):
    from app.modules.answering.service import ExecutionCancelled
    from app.modules.answering.models import Job

    owner, job_id, token = queued_job(runtime)

    def delayed(text, config, budget, on_attempt, **kwargs):
        with runtime.db() as db:
            state = memory.settings_for(db, owner)
            memory.update_settings(
                db, owner, MemorySettingsUpdate(enabled=False, version=state.version)
            )
        return {
            "operations": deterministic_operations(text),
            "budget": budget.to_dict(),
            "usage": {},
            "error": None,
        }

    monkeypatch.setattr("personalisation.memory_extraction.extract_operations", delayed)
    with pytest.raises(ExecutionCancelled):
        memory.execute_memory(runtime.engine, runtime.settings, job_id, token)
    with runtime.db() as db:
        assert db.get(Job, job_id).state == "cancelled"
        assert memory_v2.processing(db, owner)[0]["status"] == "cancelled"
        assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))


def test_assessment_import_never_promotes_automatic_label_or_substring_score(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        question = message(db, session, "What is 2 plus 2?", 1)
        response = message(db, session, "4 or 5", 2)
        body = MemoryAssessmentCreate(
            question_message_id=question.id,
            response_message_id=response.id,
            question_quote=question.content,
            response_quote=response.content,
            scope="chemistry",
            scoring_basis="Imported authored rating",
            evaluator_id="unverified-import",
            evaluator_version="v1",
            confirmation="automatic",
            rubric_kind="recorded",
            score=1.0,
        )
        result = memory_v2.record_assessment(db, actor, body)
        assert result["verification"] == "recorded_unconfirmed"
        assert not memory.freeze_memory(
            db,
            actor.id,
            "Explain chemistry.",
            True,
            policy_version="query_conditioned_memory_v2",
            counter=Counter(),
        ).payload["entries"]
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        with pytest.raises(AppError, match="complete question"):
            memory_v2.record_assessment(
                db,
                admin,
                body.model_copy(
                    update={
                        "owner_id": actor.id,
                        "rubric_kind": "numeric",
                        "response_quote": "4",
                        "expected_answer": "4",
                    }
                ),
            )


def test_study_shared_writer_preserves_m3_m4_identity_and_separates_selection(runtime):
    from evaluation.memory_v2.memory_study import StatePair
    from generation.types import ModelConfig
    from personalisation.compiler import compile_profile
    from personalisation.memory_extraction import extract_operations

    pair = StatePair(
        runtime.engine, runtime.settings, ModelConfig(), "Authored study harness check"
    )
    statement = "I prefer worked examples for biology."
    pair.statement(statement, extract_operations(statement, ModelConfig()))
    states = pair.contexts(
        "How are isotope abundances used?", compile_profile({"style": "concise"}), True
    )
    assert states["M3"]["writer_entries"] == states["M4"]["writer_entries"]
    assert states["M3"]["memory_context"]["entries"]
    assert states["M4"]["memory_context"]["entries"] == []
    assert states["M2"]["memory_context"]["version"] == "explicit_learning_memory_v1"


def test_twelve_real_observation_gate_pairs_keep_ungated_candidate_outside_storage(
    runtime, tmp_path, monkeypatch
):
    from evaluation.memory_v2.memory_gates import execute
    from generation.types import ModelConfig

    kinds = [
        "question_only",
        "self_report",
        "scored_exact",
        "scored_numeric",
        "missing_rubric",
        "wrong_owner",
        "wrong_workspace",
        "reversed_source_order",
        "selected_response_substring",
        "invented_mastery",
        "imported_score",
        "human_without_attestation",
    ]
    fixtures = [
        {
            "id": f"AUTHORED-G{i}",
            "kind": kind,
            "question": "Compute 7 plus 5.",
            "source_text": "I have difficulty with chemistry symbols."
            if kind == "self_report"
            else "I have mastered chemistry."
            if kind == "invented_mastery"
            else "Compute 7 plus 5.",
            "response": "12",
            "expected_answer": "12",
            "ambiguous_response": "12 or 13",
            "selected_response": "12",
            "automatic_expected_admitted": kind
            in {"self_report", "scored_exact", "scored_numeric"},
        }
        for i, kind in enumerate(kinds)
    ]
    monkeypatch.setattr("evaluation.memory_v2.memory_gates.gating_pairs", lambda: fixtures)

    result = execute(runtime.engine, runtime.settings, ModelConfig(), tmp_path / "gates.json")
    assert len(result["records"]) == 12
    assert all(r["expected_match"] for r in result["records"])
    assert all(
        r["candidate"] == r["gate_disabled_projection"]["candidates"][0]
        and r["gate_disabled_projection"]["writes"] == 0
        for r in result["records"]
    )
    assert result["model_calls"] == result["human_ratings"] == 0


class Counter:
    def count(self, value):
        return (len(value.encode()) + 2) // 3


def setup(db):
    actor = db.scalar(select(User).where(User.email == "student@example.com"))
    settings = memory.settings_for(db, actor.id, lock=True)
    if not settings.enabled:
        memory.update_settings(
            db, actor.id, MemorySettingsUpdate(enabled=True, version=settings.version)
        )
    # The fixture shares one disposable DB across tests; distinct users isolate state.
    isolated = User(
        email=uuid4().hex + "@example.com",
        full_name="Authored learner",
        hashed_password=actor.hashed_password,
        role_id=actor.role_id,
        workspace_id=actor.workspace_id,
    )
    db.add(isolated)
    db.flush()
    settings = memory.settings_for(db, isolated.id, lock=True)
    memory.update_settings(
        db, isolated.id, MemorySettingsUpdate(enabled=True, version=settings.version)
    )
    session = ChatSession(
        user_id=isolated.id, workspace_id=isolated.workspace_id, title="Typed memory fixture"
    )
    db.add(session)
    db.flush()
    return isolated, session


def message(db, session, text, sequence):
    row = Message(session_id=session.id, role="user", content=text, sequence=sequence)
    db.add(row)
    db.flush()
    return row


def save(db, actor, msg):
    event = memory_v2.source_event(db, actor.id, msg.id)
    result = memory_v2.apply_operations(db, actor.id, event, deterministic_operations(msg.content))
    db.flush()
    return event, result


def test_current_correction_precedes_freeze_and_old_late_result_cannot_return(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        old = message(db, session, "I prefer analogies.", 1)
        event = memory_v2.source_event(db, actor.id, old.id)
        current = message(db, session, "Actually, I no longer want analogies.", 2)
        snap = memory.freeze_memory(
            db,
            actor.id,
            current.content,
            True,
            policy_version="query_conditioned_memory_v2",
            current_message_id=current.id,
            counter=Counter(),
        )
        assert snap.payload["fields"][0]["source"]["message_id"] == current.id
        late = memory_v2.apply_operations(
            db, actor.id, event, deterministic_operations(old.content)
        )
        assert late[0]["reason"] == "stale_source_event"
        row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id))
        assert row.content == current.content


def test_delete_before_old_add_creates_tombstone_and_prevents_resurrection(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        old = message(db, session, "I prefer analogies.", 1)
        queued = memory_v2.source_event(db, actor.id, old.id)
        erased = message(db, session, "Forget my preference for analogies.", 2)
        save(db, actor, erased)
        result = memory_v2.apply_operations(
            db, actor.id, queued, deterministic_operations(old.content)
        )
        assert result[0]["reason"] == "stale_source_event"
        row = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id))
        assert row.status == "deleted" and row.content is None


def test_repeated_erasure_advances_fence_past_an_intervening_delayed_add(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        erased = message(db, session, "Forget my preference for analogies.", 1)
        save(db, actor, erased)
        late_source = message(db, session, "I prefer analogies.", 2)
        late = memory_v2.source_event(db, actor.id, late_source.id)
        again = message(db, session, "Delete my preference for analogies.", 3)
        save(db, actor, again)
        assert (
            memory_v2.apply_operations(
                db, actor.id, late, deterministic_operations(late_source.content)
            )[0]["reason"]
            == "stale_source_event"
        )


def test_scope_edit_updates_key_and_cas_and_erasure_remove_all_revision_payloads(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        src = message(db, session, "I prefer detailed explanations for biology.", 1)
        _, receipts = save(db, actor, src)
        row = db.get(MemoryEntry, receipts[0]["memory_id"])
        old_key, old_version = row.canonical_key, row.version
        edited = memory.edit_entry(
            db,
            actor.id,
            row.id,
            MemoryEdit(version=row.version, content="Use clear examples.", scope="chemistry"),
        )
        assert row.canonical_key != old_key and row.scope == "chemistry"
        with pytest.raises(AppError):
            memory.edit_entry(
                db, actor.id, row.id, MemoryEdit(version=old_version, content="stale")
            )
        memory.delete_entry(db, actor.id, row.id, edited["version"])
        assert row.source_details == {} and row.content is None
        assert all(
            r.content is None and r.details == {}
            for r in db.scalars(select(MemoryRevision).where(MemoryRevision.entry_id == row.id))
        )


def test_summary_expiry_off_and_profile_off_never_reuse_snapshot(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        src = message(db, session, "I prefer examples.", 1)
        _, receipts = save(db, actor, src)
        row = db.get(MemoryEntry, receipts[0]["memory_id"])
        snap = memory.freeze_memory(
            db,
            actor.id,
            "Explain ATP.",
            True,
            policy_version="query_conditioned_memory_v2",
            counter=Counter(),
        )
        assert snap.payload["entries"]
        assert (
            memory.freeze_memory(
                db,
                actor.id,
                "Explain ATP.",
                False,
                policy_version="query_conditioned_memory_v2",
                counter=Counter(),
            )
            is None
        )
        row.expires_at = utcnow() - dt.timedelta(seconds=1)
        db.flush()
        summary = memory_v2.summary(db, actor.id)
        assert summary["active_count"] == 0 and row.content not in summary["summary"]
        assert db.get(MemorySnapshot, snap.id).payload.get("revoked")
        state = memory.settings_for(db, actor.id)
        memory.update_settings(
            db, actor.id, MemorySettingsUpdate(enabled=False, version=state.version)
        )
        assert memory_v2.summary(db, actor.id)["items"] == []
        with pytest.raises(AppError):
            memory.read_snapshot(db, actor.id, snap.id)


def test_source_ownership_is_checked_before_typed_write(runtime):
    with runtime.db() as db:
        owner, session = setup(db)
        src = message(db, session, "I struggle with ATP.", 1)
        other, _ = setup(db)
        with pytest.raises(AppError):
            memory_v2.source_event(db, other.id, src.id)
        _, receipts = save(db, owner, src)
        row = db.get(MemoryEntry, receipts[0]["memory_id"])
        assert row.verification == "self_reported"
        assert row.source_details["source_quote"] == src.content


def test_m2_remains_explicit_original_reader_while_m4_uses_scoped_topics(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        src = message(db, session, "I prefer examples for biology.", 1)
        save(db, actor, src)
        old = memory.freeze_memory(db, actor.id, "Explain ATP.", True)
        new = memory.freeze_memory(
            db,
            actor.id,
            "Explain ATP.",
            True,
            policy_version="query_conditioned_memory_v2",
            counter=Counter(),
        )
        assert (
            old.payload["version"] == "explicit_learning_memory_v1" and old.payload["entries"] == []
        )
        assert new.payload["entries"] and new.payload["query_topics"] == [
            "biology",
            "cellular_energy",
        ]


def test_automatic_assessment_has_real_rubric_and_single_performance_scope(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        question = message(db, session, "What is 2 plus 2?", 1)
        response = message(db, session, "4", 2)
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        body = MemoryAssessmentCreate(
            owner_id=actor.id,
            question_message_id=question.id,
            response_message_id=response.id,
            question_quote=question.content,
            response_quote=response.content,
            scope="chemistry",
            scoring_basis="Addition under an authored numeric rubric.",
            evaluator_id="provided-id-is-not-trusted",
            evaluator_version="caller",
            confirmation="automatic",
            rubric_kind="numeric",
            expected_answer="4",
        )
        result = memory_v2.record_assessment(db, admin, body)
        assert result["verification"] == "automatic_rubric_evaluated"
        assert result["provenance"]["evaluator_id"] == "server:numeric"
        assert result["provenance"]["score"] == 1.0
        assert "does not establish general mastery" in result["content"]
        with pytest.raises(AppError):
            memory_v2.record_assessment(
                db,
                actor,
                body.model_copy(
                    update={
                        "confirmation": "human",
                        "rubric_kind": "recorded",
                        "score": 1.0,
                        "reviewer_attestation": True,
                        "evaluator_id": actor.id,
                    }
                ),
            )
