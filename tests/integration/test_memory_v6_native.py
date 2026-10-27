"""Native V6 admission, persistence and owner/epoch fences using isolated PostgreSQL."""

import json
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from personalisation import memory_v6
from app.modules.answering.models import AnswerRequest, Job
from app.modules.learning_state import memory, memory_v2 as old, memory_writer_v6 as writer
from app.modules.learning_state.models import MemoryEntry, MemoryWriteEvent, MemoryRevision
from app.core.exceptions import AppError
from app.modules.identity.models import User
from .test_memory_preview_v3 import authored, preview
from .test_memory_v2 import setup, message


@pytest.fixture(autouse=True)
def v6_local_policy(runtime, tmp_path, monkeypatch):
    policy = tmp_path / "memory-policy.json"
    policy.write_text(json.dumps(memory_v6.freeze_policy()))
    runtime.settings.memory_semantic_policy_file = str(policy)

    def deny(*a, **k):
        pytest.fail("Native memory admission must not dispatch a provider")

    monkeypatch.setattr("generation.adapters.open_provider", deny)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", deny)


@pytest.mark.parametrize(
    "source,scope",
    [
        ("From now on, I prefer concise chemistry explanations.", "chemistry"),
        ("I prefer detailed biology explanations.", "biology"),
        ("I prefer short genetics answers.", "genetics"),
        ("I prefer detailed explanations.", "global"),
        ("I prefer concise economics explanations.", None),
        ("My tutor said: I prefer concise chemistry explanations.", None),
    ],
)
def test_native_frozen_policy_exact_once_and_subject_applicability(runtime, source, scope):
    email, owner, _ = authored(runtime, [])
    headers = runtime.headers(email)
    session = runtime.client.post(
        "/api/v1/sessions", headers=headers, json={"title": "Subject applicability"}
    ).json()["data"]
    key = str(uuid4())
    url = f"/api/v1/sessions/{session['id']}/messages"
    response = runtime.client.post(
        url, headers={**headers, "Idempotency-Key": key}, json={"content": source}
    )
    assert response.status_code == 202, response.text
    receipt = response.json()["data"]
    try:
        replay = runtime.client.post(
            url, headers={**headers, "Idempotency-Key": key}, json={"content": source}
        )
        assert (
            replay.status_code == 202
            and replay.json()["data"]["request_id"] == receipt["request_id"]
        )
        with runtime.db() as db:
            req = db.get(AnswerRequest, receipt["request_id"])
            rows = list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
            event = db.scalar(
                select(MemoryWriteEvent).where(
                    MemoryWriteEvent.source_message_id == req.user_message_id
                )
            )
            assert not list(
                db.scalars(select(Job).where(Job.kind == "memory", Job.owner_id == owner))
            )
            if scope is None:
                assert not rows and event.status == "no_op"
            else:
                assert len(rows) == 1 and rows[0].scope == scope and rows[0].content == source
                assert rows[0].writer_version == "typed_memory_v6" and event.status == "applied"
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(MemoryRevision)
                        .where(MemoryRevision.entry_id == rows[0].id)
                    )
                    == 1
                )
                identity = rows[0].id
        if scope not in (None, "global"):
            related = preview(runtime, email, "Explain " + scope + ".")
            assert related["policy_version"] == memory_v6.SELECTOR_VERSION
            assert identity in [r["id"] for r in related["entries"]]
            other = "biology" if scope == "chemistry" else "chemistry"
            assert identity not in [
                r["id"] for r in preview(runtime, email, "Explain " + other + ".")["entries"]
            ]
        assert not preview(runtime, "student2@example.com", "Explain chemistry.")["entries"]
    finally:
        assert (
            runtime.client.post(
                f"/api/v1/jobs/{receipt['job_id']}/cancel", headers=headers
            ).status_code
            == 200
        )


def test_owner_and_revocation_epoch_fences_do_not_write(runtime):
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, "I prefer detailed biology explanations.", 1)
        event = old.source_event(db, actor.id, source.id)
        other = db.scalar(select(User).where(User.email == "student2@example.com"))
        assert other and other.id != actor.id
        with pytest.raises(AppError):
            writer.apply_source(db, other.id, event, source.content)
        state = memory.settings_for(db, actor.id, lock=True)
        state.revocation_epoch += 1
        db.flush()
        assert writer.apply_source(db, actor.id, event, source.content) == []
        assert event.status == "revoked"
        assert not list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == actor.id)))


@pytest.mark.parametrize("fault", [None, "foreign_reference", "paraphrase", "unrequested_delete"])
def test_native_worker_bound_selection_and_terminal_failure(runtime, monkeypatch, fault):
    from generation.types import ModelConfig, ProviderResult
    from personalisation import memory_extraction, memory_source_selection_v1

    source_text = "I prefer explanations that use compact language."

    class Count:
        def __init__(self, *a):
            pass

        def request_input(self, *a):
            return 200

    monkeypatch.setattr(memory_extraction, "TokenCounter", Count)
    calls = []

    def selected(self, messages, **options):
        calls.append(options)
        packet = json.loads(messages[1]["content"])
        assert packet["exact_statement"] == source_text
        assert options["response_schema_name"] == memory_source_selection_v1.VERSION
        row = {
            "operation": "ADD",
            "category": "preference",
            "field_key": "detail_level",
            "source_ref": packet["source_ref"],
            "expires_at": None,
        }
        if fault == "foreign_reference":
            row["source_ref"] = "another_message"
        if fault == "paraphrase":
            row["content"] = "The learner likes brief answers."
        if fault == "unrequested_delete":
            row["operation"] = "DELETE"
        return ProviderResult(
            raw_text=json.dumps({"operations": [row]}), usage={"total_tokens": 20}
        )

    monkeypatch.setattr("generation.adapters.LLMAdapter.generate", selected)
    with runtime.db() as db:
        actor, session = setup(db)
        source = message(db, session, source_text, 1)
        config = ModelConfig(
            provider="local",
            model="offline-source-selection",
            base_url="http://127.0.0.1:9/v1",
            tokenizer_provider="estimate",
        )
        writer.enqueue(
            db, actor.id, source, config.to_dict(), True, policy_version="typed_memory_v6"
        )
        job = db.scalar(select(Job).where(Job.owner_id == actor.id, Job.kind == "memory"))
        assert job
        job.payload = {**job.payload, "budget": {**job.payload["budget"], "max_calls": 1}}
        db.commit()
        identity, owner, source_id = job.id, actor.id, source.id
    runtime.work()
    with runtime.db() as db:
        job = db.get(Job, identity)
        rows = list(db.scalars(select(MemoryEntry).where(MemoryEntry.owner_id == owner)))
        assert len(calls) == 1 and job.payload["budget"]["consumed_calls"] == 1
        if fault:
            assert job.state == "failed" and job.error["code"] == "MEMORY_EXTRACTION_INVALID"
            assert not rows
        else:
            assert job.state == "succeeded", job.error
            assert (
                len(rows) == 1
                and rows[0].content == source_text
                and rows[0].source_message_id == source_id
            )
            assert rows[0].scope == "global" and rows[0].writer_version == "typed_memory_v6"
            assert job.payload["extraction_schema_version"] == memory_source_selection_v1.VERSION
