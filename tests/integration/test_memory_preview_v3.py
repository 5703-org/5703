"""Disposable PostgreSQL preview parity; authored source fixtures and zero cloud calls."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.modules.answering.models import AnswerRequest
from app.modules.learning_state import memory
from app.modules.learning_state import memory_v2 as writer
from app.modules.learning_state.models import MemoryEntry, MemorySnapshot
from contracts.learning import MemoryControlsUpdate, MemoryRecordCreate, MemorySettingsUpdate
from personalisation import memory_v2, memory_v3, memory_v4, memory_v5
from .test_memory_v2 import Counter, message, save, setup


@pytest.fixture(autouse=True)
def no_cloud(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Memory preview and configuration checks must make zero cloud calls")

    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)
    monkeypatch.setattr("generation.adapters.open_provider", forbidden)


def authored(runtime, statements, scopes=None):
    with runtime.db() as db:
        actor, session = setup(db)
        for index, text in enumerate(statements, 1):
            source = message(db, session, text, index)
            if scopes is None:
                save(db, actor, source)
            else:
                # Author-created typed records use the existing owner/source validation.
                writer.create_record(
                    db,
                    actor.id,
                    MemoryRecordCreate(
                        category="preference",
                        field_key=memory_v2.infer_field(text),
                        content=text,
                        scope=scopes[index - 1],
                        source_message_id=source.id,
                        source_quote=text,
                    ),
                )
        email, owner = actor.email, actor.id
        rows = list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
        identifiers = [row.id for row in rows]
        db.commit()
    return email, owner, identifiers


def preview(runtime, email, text, enabled=True, status=200):
    response = runtime.client.post(
        "/api/v1/me/memory/preview",
        headers=runtime.headers(email),
        json={"question": text, "use_profile": enabled},
    )
    assert response.status_code == status, response.text
    return response.json().get("data", response.json())


def test_specific_scope_preview_matches_current_chat_without_changing_old_v2(runtime):
    email, owner, ids = authored(
        runtime, ["I prefer detailed explanations for photosynthesis."], scopes=["photosynthesis"]
    )
    current = preview(runtime, email, "Explain cellular respiration.")
    assert current["policy_version"] == memory_v5.SELECTOR_VERSION
    assert not current["entries"]
    assert current["excluded"][0] == {"id": ids[0], "reason": "specific_scope_not_named"}
    with runtime.db() as db:
        assert db.get(MemoryEntry, ids[0]).scope == "photosynthesis"
        old = memory.freeze_memory(
            db,
            owner,
            "Explain cellular respiration.",
            True,
            policy_version=memory_v2.SELECTOR_VERSION,
            counter=Counter(),
        )
        chat = memory.freeze_memory(
            db,
            owner,
            "Explain cellular respiration.",
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            counter=Counter(),
        )
        assert [entry["id"] for entry in old.payload["entries"]] == ids
        assert chat.payload["entries"] == current["entries"]
        assert chat.payload["excluded"] == current["excluded"]


def test_explicit_override_subject_profile_and_global_precedence(runtime):
    email, _, _ = authored(
        runtime,
        [
            "I prefer detailed explanations.",
            "I prefer detailed explanations for biology.",
        ],
    )
    bio = preview(runtime, email, "Explain ATP in biology.")
    assert [e["scope"] for e in bio["entries"]] == ["biology"]
    explicit = preview(runtime, email, "For this answer, be concise. Explain ATP in biology.")
    assert not explicit["entries"]
    assert any(f["verification"] == "current_user_instruction" for f in explicit["fields"])
    chemistry = preview(runtime, email, "Explain atomic orbitals in chemistry.")
    assert not chemistry["entries"]
    assert any(e["reason"] == "saved_profile_default" for e in chemistry["excluded"])
    other, _, _ = authored(runtime, ["I prefer bullet points."])
    assert preview(runtime, other, "Explain atomic orbitals.")["entries"][0]["scope"] == "global"


def test_standalone_preview_never_guesses_the_source_or_another_session(runtime):
    email, owner, ids = authored(
        runtime, ["I prefer detailed explanations for photosynthesis."], scopes=["photosynthesis"]
    )
    assert not preview(runtime, email, "Can you explain it further?")["entries"]
    with runtime.db() as db:
        assert db.get(MemoryEntry, ids[0]).scope == "photosynthesis"
        snapshot = memory.freeze_memory(
            db,
            owner,
            "Can you explain it further?",
            True,
            policy_version=memory_v3.SELECTOR_VERSION,
            context={"recent_messages": [{"role": "user", "content": "Explain photosynthesis."}]},
            counter=Counter(),
        )
        assert [e["id"] for e in snapshot.payload["entries"]] == ids


def test_pause_disable_and_erasure_remain_owner_scoped_and_create_no_snapshot(runtime):
    email, owner, ids = authored(runtime, ["I prefer detailed explanations for biology."])
    with runtime.db() as db:
        before = db.scalar(select(func.count()).select_from(MemorySnapshot))
    assert not preview(runtime, "student2@example.com", "Explain ATP in biology.")["entries"]
    assert preview(runtime, email, "Explain ATP in biology.")["entries"]
    assert not preview(runtime, email, "Explain ATP in biology.", enabled=False)["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=True)
        )
    assert not preview(runtime, email, "Explain ATP in biology.")["entries"]
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db, owner, row.id, MemoryControlsUpdate(version=row.version, paused=False)
        )
        settings = memory.settings_for(db, owner, lock=True)
        memory.update_settings(
            db, owner, MemorySettingsUpdate(version=settings.version, enabled=False)
        )
    assert not preview(runtime, email, "Explain ATP in biology.")["entries"]
    with runtime.db() as db:
        settings = memory.settings_for(db, owner, lock=True)
        memory.update_settings(
            db, owner, MemorySettingsUpdate(version=settings.version, enabled=True)
        )
        row = db.get(MemoryEntry, ids[0])
        memory.delete_entry(db, owner, row.id, row.version)
    assert not preview(runtime, email, "Explain ATP in biology.")["entries"]
    with runtime.db() as db:
        assert db.get(MemoryEntry, ids[0]).content is None
        assert db.scalar(select(func.count()).select_from(MemorySnapshot)) == before


@pytest.mark.parametrize("raw", ['{"private_source": "do-not-echo-source-content"}', "null"])
def test_invalid_config_returns_safe_503_and_chat_keeps_unavailable_stage(runtime, tmp_path, raw):
    email, _, _ = authored(runtime, ["I prefer detailed explanations for biology."])
    path = tmp_path / "private-policy-location.json"
    path.write_text(raw, encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(path)
    response = preview(runtime, email, "Explain ATP.", status=503)
    assert response["error"]["code"] == "MEMORY_POLICY_UNAVAILABLE"
    assert (
        response["error"]["message"] == "The learning-memory policy configuration is unavailable."
    )
    assert response["error"]["details"] == {}
    assert str(path) not in json.dumps(response) and "do-not-echo-source-content" not in json.dumps(
        response
    )
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Authored policy-error check"}
    ).json()["data"]
    submitted = runtime.client.post(
        f"/api/v1/sessions/{session['id']}/messages",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={"content": "Explain ATP."},
    )
    assert submitted.status_code == 202, submitted.text
    with runtime.db() as db:
        request = db.get(AnswerRequest, submitted.json()["data"]["request_id"])
        assert request.command["memory_snapshot_id"] is None
        assert request.trace["memory_stage"] == {
            "status": "unavailable",
            "policy_version": memory_v5.SELECTOR_VERSION,
            "code": "MEMORY_POLICY_UNAVAILABLE",
        }
    cancelled = runtime.client.post(
        f"/api/v1/jobs/{submitted.json()['data']['job_id']}/cancel", headers=headers
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["state"] == "cancelled"


def test_disabled_preview_does_not_load_unused_policy_or_model_settings(
    runtime, tmp_path, monkeypatch
):
    email, _, _ = authored(runtime, ["I prefer detailed explanations for biology."])
    path = tmp_path / "unused-invalid-policy.json"
    path.write_text("null", encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(path)

    def forbidden(*args, **kwargs):
        pytest.fail("Disabled preview must not resolve policy, model settings or tokenizer")

    monkeypatch.setattr("personalisation.memory_policy.load_policy", forbidden)
    monkeypatch.setattr("app.modules.model_settings.service.resolve_active_model_config", forbidden)
    monkeypatch.setattr("generation.token_counting.TokenCounter", forbidden)
    result = preview(runtime, email, "Explain ATP.", enabled=False)
    assert not result["enabled"] and not result["entries"]
    assert result["policy_version"] == memory_v5.SELECTOR_VERSION


def test_opt_in_semantic_failure_is_visible_and_foreign_source_is_rejected(
    runtime, tmp_path, monkeypatch
):
    # The calibration identity and score below are labelled contract fixtures.
    policy = memory_v3.freeze_policy(enabled=True, threshold=0.85, calibration_id="a" * 64)
    path = tmp_path / "authored-test-policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")
    runtime.settings.memory_semantic_policy_file = str(path)
    email, owner, ids = authored(runtime, ["I prefer detailed explanations for botany."])
    with runtime.db() as db:
        row = db.get(MemoryEntry, ids[0])
        memory.update_controls(
            db,
            owner,
            row.id,
            MemoryControlsUpdate(
                version=row.version, paused=False, match_policy="calibrated_semantic"
            ),
        )

    def unavailable(*args):
        raise OSError("private-local-cache-path")

    monkeypatch.setattr(memory_v3, "scope_scores", unavailable)
    failed = preview(runtime, email, "How do stomata respond?")
    assert any("Local semantic matching is unavailable" in item for item in failed["limitations"])
    assert "private-local-cache-path" not in json.dumps(failed)
    _, foreign, _ = authored(runtime, ["I prefer detailed explanations for botany."])
    with runtime.db() as db:
        source = db.scalar(select(MemoryEntry).where(MemoryEntry.owner_id == foreign))
        row = db.get(MemoryEntry, ids[0])
        row.source_message_id = source.source_message_id
        db.commit()
    monkeypatch.setattr(
        memory_v3, "scope_scores", lambda q, s: pytest.fail("Foreign source must never be scored")
    )
    rejected = preview(runtime, email, "How do stomata respond?")
    assert not rejected["entries"]
    assert any(e["reason"] == "conditional_source_unavailable" for e in rejected["excluded"])
