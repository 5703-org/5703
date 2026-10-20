"""Owner memory, controlled presentation and task lifecycle in disposable PostgreSQL."""

from uuid import uuid4
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import patch
from sqlalchemy import select
from app.modules.answering.models import Job, AnswerRequest, Message, Attempt
from app.modules.answering.service import execute_answer
from app.modules.learning_state.models import (
    MemoryEntry,
    MemorySnapshot,
    MemoryRevision,
    PrivateAnswerDraft,
    LearningExposure,
)
from app.modules.learning_state import memory
from app.modules.answering.service import ExecutionCancelled
import pytest
from generation import GenerationService
from generation.types import ProviderResult
from generation.adapters import chat_value
from .test_chat_runtime import call, corpus, session, submit


def execute(rt, receipt):
    token = str(uuid4())
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        job.state, job.execution_token = "running", token
        db.commit()
    execute_answer(rt.engine, rt.settings, receipt["job_id"], token)
    result = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert result["state"] == "succeeded", str(result)
    return call(rt, "GET", "/answers/" + result["answer_id"])


def test_new_direct_mock_publishes_structural_presentation(runtime):
    rt = runtime
    corpus(rt)
    answer = execute(rt, submit(rt, session(rt)))
    assert answer["teaching_mode"] == "direct"
    assert answer["presentation"]["id"]
    assert answer["evidence"]
    assert answer["attribution"]["fragments"]
    assert all(c["support"]["status"] != "supported" for c in answer["attribution"]["claims"])


def send(rt, s, text, **values):
    return call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": text, **values},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )


def enable(rt, value):
    state = call(rt, "GET", "/me/memory/settings")
    updated = call(
        rt, "PATCH", "/me/memory/settings", {"enabled": value, "version": state["version"]}
    )
    assert updated["enabled"] is value
    assert call(rt, "GET", "/me/memory/settings")["enabled"] is value
    return updated


def test_memory_opt_in_profile_off_durable_save_edit_delete_and_source_isolation(runtime):
    rt = runtime
    enable(rt, False)
    s = session(rt)
    first = submit(rt, s, "I prefer simple examples before formulas.")
    execute(rt, first)
    with rt.db() as db:
        req = db.get(AnswerRequest, first["request_id"])
        assert req.command["memory_snapshot_id"] is None
        assert not list(
            db.scalars(
                select(Job).where(
                    Job.kind == "memory",
                    Job.payload["source_message_id"].as_string() == first["user_message_id"],
                )
            )
        )
    enable(rt, True)
    off = submit(rt, s, "I prefer numbered learning steps.", profile=False)
    execute(rt, off)
    with rt.db() as db:
        assert db.get(AnswerRequest, off["request_id"]).command["memory_snapshot_id"] is None
    receipt = submit(rt, s, "I prefer simple examples before formulas.")
    execute(rt, receipt)
    # V2 publishes explicit typed statements in the submission transaction.
    with rt.db() as db:
        assert db.scalar(
            select(MemoryEntry).where(MemoryEntry.source_message_id == receipt["user_message_id"])
        )
    entries = call(rt, "GET", "/me/memories")
    saved = next(e for e in entries if e["source_message_id"] == receipt["user_message_id"])
    source = call(rt, "GET", f"/me/memories/{saved['id']}/source")
    assert source["content"] == "I prefer simple examples before formulas."
    call(
        rt,
        "GET",
        f"/me/memories/{saved['id']}/source",
        headers=rt.headers("admin@example.com"),
        status=404,
    )
    notice = call(rt, "GET", f"/sessions/{s['id']}/memory-notices")
    assert any(n["memory_id"] == saved["id"] and n["action"] == "undo_save" for n in notice)
    amended = call(
        rt,
        "PATCH",
        f"/me/memories/{saved['id']}",
        {"version": saved["version"], "content": "Use precise terminology and then an example."},
    )
    call(
        rt,
        "PATCH",
        f"/me/memories/{saved['id']}",
        {"version": saved["version"], "content": "stale overwrite"},
        status=409,
    )
    pending = submit(rt, session(rt), "Hello")
    with rt.db() as db:
        req = db.get(AnswerRequest, pending["request_id"])
        snapshot_id = req.command["memory_snapshot_id"]
        assert db.get(MemorySnapshot, snapshot_id).payload["entries"]
        db.add(
            PrivateAnswerDraft(
                request_id=req.id,
                memory_snapshot_id=snapshot_id,
                phase="generated_draft",
                payload={"text": amended["content"]},
            )
        )
        db.commit()
    call(rt, "POST", f"/me/memories/{saved['id']}/undo", {"version": amended["version"]})
    assert call(rt, "GET", "/jobs/" + pending["job_id"])["state"] == "cancelled"
    call(
        rt,
        "POST",
        "/answer-requests/" + pending["request_id"] + "/retry",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        409,
    )
    with rt.db() as db:
        row = db.get(MemoryEntry, saved["id"])
        assert row.content is None and row.source_message_id is None and row.status == "deleted"
        assert all(
            r.content is None
            for r in db.scalars(select(MemoryRevision).where(MemoryRevision.entry_id == row.id))
        )
        assert db.get(MemorySnapshot, snapshot_id).invalidated
        assert all(
            d.payload == {"redacted": "memory_revoked"}
            for d in db.scalars(
                select(PrivateAnswerDraft).where(
                    PrivateAnswerDraft.memory_snapshot_id == snapshot_id
                )
            )
        )
        # Chat deletion is separate; erasure cannot secretly restore the memory.
        assert db.get(Message, receipt["user_message_id"]).content == source["content"]
        before = len(list(db.scalars(select(Job).where(Job.kind == "memory"))))
        memory.enqueue_extraction(
            db,
            row.owner_id,
            db.get(Message, receipt["user_message_id"]),
            {"provider": "mock"},
            True,
        )
        assert len(list(db.scalars(select(Job).where(Job.kind == "memory")))) == before
    enable(rt, False)


class ScriptedCheckedTransport:
    """Deterministic fixture verdicts test plumbing, never semantic quality."""

    def generate(self, messages, **kwargs):
        if kwargs["response_schema_name"] in {"joint_check_v1", "joint_check_v2"}:
            data = json.loads(messages[-1]["content"])
            value = {
                "claims": [
                    {
                        "claim_id": c["claim_id"],
                        "factual": True,
                        "status": "supported",
                        "fragment_ids": [
                            next(
                                f["fragment_id"]
                                for f in data["SOURCE_FRAGMENTS"]
                                if f["evidence_id"] in c["evidence_ids"]
                            )
                        ],
                        "reason": "Scripted fixture association.",
                    }
                    for c in data["CLAIMS"]
                ],
                "body_ok": True,
                "specific_help": True,
                "scope_ok": True,
                "suggestions_ok": True,
                "evidence_display_ok": True,
                "cumulative_ok": True,
                "complete_answer": False,
                "reason": "Scripted fixture verdict, not human or model validation.",
            }
            if kwargs["response_schema_name"] == "joint_check_v2":
                value.update(
                    coverage="full",
                    missing_facets=[],
                    limitations_explicit=False,
                    repair_fragment_ids=[],
                )
                for claim in value["claims"]:
                    claim.update(basis="textbook", problem_quote=None, derivation=None)
        else:
            evidence_id = next(
                item["evidence_id"]
                for item in kwargs["request_context"]["evidence"]
                if "Photosynthesis captures" in item["text"]
            )
            value = chat_value(
                "answer", f"Consider the energy input. [{evidence_id}]", citations=[evidence_id]
            )
        return ProviderResult(
            raw_text=json.dumps(value),
            provider="scripted_fixture",
            model="scripted_fixture",
            request_submitted=True,
        )


def scripted_service(**kwargs):
    adapter = ScriptedCheckedTransport()
    return GenerationService(adapter, checker_adapter=adapter, **kwargs)


def test_hint_mock_needs_checker_and_scripted_hint_projection_is_consistent(runtime):
    rt = runtime
    corpus(rt)
    s = session(rt)
    blocked = send(rt, s, "What is photosynthesis?", teaching_mode="hint")
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + blocked["job_id"])
    assert job["state"] == "failed" and job["error"]["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
    with rt.db() as db:
        assert db.get(AnswerRequest, blocked["request_id"]).budget["consumed_calls"] == 0
    s = session(rt)
    receipt = send(rt, s, "What is photosynthesis?", teaching_mode="hint")
    with patch("app.modules.answering.service.GenerationService", scripted_service):
        answer = execute(rt, receipt)
    assert answer["teaching_mode"] == "hint" and answer["help_level"] == 1
    assert (
        answer["evidence"] == []
        and answer["conversation_snapshot"] is None
        and answer["profile_snapshot"] is None
    )
    view = answer["presentation"]["citation_views"][0]
    assert not view["source_url"]
    direct = call(rt, "GET", f"/answers/{answer['id']}/evidence/{view['evidence_id']}")
    assert direct == view and "text" not in direct
    history = call(rt, "GET", f"/sessions/{s['id']}/messages")
    assert history["items"][-1]["answer"] == answer
    claim = answer["attribution"]["claims"][0]
    per_claim = call(rt, "GET", f"/answers/{answer['id']}/claims/{claim['claim_id']}/sources")
    assert per_claim[0]["claim_ids"] == [claim["claim_id"]]
    headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    body = {
        "kind": "full_source_requested",
        "presentation_id": answer["presentation"]["id"],
        "evidence_id": view["evidence_id"],
        "surface": "full_source",
    }
    expanded = call(rt, "POST", f"/answers/{answer['id']}/exposures", body, headers)
    assert expanded == call(rt, "POST", f"/answers/{answer['id']}/exposures", body, headers)
    assert "Photosynthesis captures" in expanded["citation_view"]["segments"][0]["text"]
    call(
        rt,
        "POST",
        f"/answers/{answer['id']}/exposures",
        {
            "kind": "rendered",
            "presentation_id": body["presentation_id"],
            "surface": "full_source",
            "evidence_id": view["evidence_id"],
        },
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        422,
    )
    call(
        rt,
        "POST",
        f"/answers/{answer['id']}/exposures",
        {
            "kind": "rendered",
            "presentation_id": body["presentation_id"],
            "surface": "full_source",
            "evidence_id": view["evidence_id"],
            "parent_exposure_id": expanded["id"],
        },
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
    )
    next_request = send(
        rt,
        s,
        "Another hint, please.",
        teaching_mode="hint",
        task_id=answer["task_id"],
        task_action="more_hint",
    )
    with rt.db() as db:
        frozen = db.get(AnswerRequest, next_request["request_id"]).command["teaching_context"]
        assert frozen["help_level"] == 2 and frozen["task_id"] == answer["task_id"]
        assert len(frozen["delivered_turns"]) == 1
        assert any(e["kind"] == "full_source_requested" for e in frozen["disclosure_events"])
    call(rt, "POST", "/jobs/" + next_request["job_id"] + "/cancel", {})
    new_problem = send(rt, s, "What is diffusion?", task_action="new")
    fresh = execute(rt, new_problem)
    assert (
        fresh["task_id"] != answer["task_id"]
        and fresh["teaching_mode"] == "direct"
        and fresh["help_level"] == 0
    )


def test_memory_settings_compare_and_swap_allows_one_concurrent_writer(runtime):
    rt = runtime
    state = enable(rt, False)
    headers = rt.headers()

    def update():
        response = rt.client.patch(
            "/api/v1/me/memory/settings",
            headers=headers,
            json={"enabled": True, "version": state["version"]},
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: update(), range(2)))
    assert sorted(code for code, _ in statuses) == [200, 409], str((state, statuses))
    enable(rt, False)


def test_switching_memory_off_during_provider_extraction_fences_late_save(runtime):
    rt = runtime
    enable(rt, True)
    # Preserve the frozen M2 asynchronous writer path explicitly. New interactive
    # requests synchronously apply this recognized statement under V2.
    s = session(rt)
    from generation.types import ModelConfig

    with rt.db() as db:
        from app.modules.learning.models import ChatSession

        owner_id = db.get(ChatSession, s["id"]).user_id
        source = Message(
            session_id=s["id"],
            sequence=1,
            role="user",
            content="I prefer concise explanations from now on.",
        )
        db.add(source)
        db.flush()
        memory.enqueue_extraction(
            db,
            owner_id,
            source,
            ModelConfig().to_dict(),
            True,
            policy_version="explicit_learning_memory_v1",
        )
        receipt = {"user_message_id": source.id}
        db.commit()

    class MutatingTransport:
        def generate(self, messages, **kwargs):
            enable(rt, False)
            value = {
                "entries": [
                    {
                        "category": "preference",
                        "attribute": "detail_level",
                        "scope": "global",
                        "content": "Use concise explanations.",
                        "source_quote": "I prefer concise explanations from now on.",
                        "expires_at": None,
                    }
                ]
            }
            return ProviderResult(raw_text=json.dumps(value))

    with patch("personalisation.memory.LLMAdapter", return_value=MutatingTransport()):
        assert rt.work()
    with rt.db() as db:
        job = db.scalar(
            select(Job).where(
                Job.kind == "memory",
                Job.payload["source_message_id"].as_string() == receipt["user_message_id"],
            )
        )
        assert job.state == "cancelled" and job.payload["budget"]["consumed_calls"] == 1
        assert not list(
            db.scalars(
                select(MemoryEntry).where(
                    MemoryEntry.source_message_id == receipt["user_message_id"]
                )
            )
        )
        assert len(list(db.scalars(select(Attempt).where(Attempt.job_id == job.id)))) == 1


def test_new_exposure_during_check_blocks_stale_cumulative_publication(runtime):
    rt = runtime
    corpus(rt)
    s = session(rt)
    with patch("app.modules.answering.service.GenerationService", scripted_service):
        first = execute(rt, send(rt, s, "What is photosynthesis?", teaching_mode="hint"))
    next_receipt = send(
        rt,
        s,
        "Another hint",
        teaching_mode="hint",
        task_id=first["task_id"],
        task_action="more_hint",
    )

    class ExposingTransport(ScriptedCheckedTransport):
        def generate(self, messages, **kwargs):
            if kwargs["response_schema_name"] in {"joint_check_v1", "joint_check_v2"}:
                call(
                    rt,
                    "POST",
                    f"/answers/{first['id']}/exposures",
                    {
                        "kind": "full_source_requested",
                        "surface": "full_source",
                        "presentation_id": first["presentation"]["id"],
                        "evidence_id": first["presentation"]["citation_views"][0]["evidence_id"],
                    },
                    {**rt.headers(), "Idempotency-Key": str(uuid4())},
                )
            return super().generate(messages, **kwargs)

    def factory(**kwargs):
        adapter = ExposingTransport()
        return GenerationService(adapter, checker_adapter=adapter, **kwargs)

    with patch("app.modules.answering.service.GenerationService", factory):
        assert rt.work()
    job = call(rt, "GET", "/jobs/" + next_receipt["job_id"])
    assert (
        job["state"] == "failed" and job["error"]["code"] == "CONFLICT" and job["answer_id"] is None
    )
    assert call(rt, "GET", f"/answers/{first['id']}")["response"] == first["response"]
