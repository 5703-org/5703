"""Explicit mode choice is frozen per request; authored mock infrastructure only."""

from uuid import uuid4
from copy import deepcopy
from unittest.mock import patch
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from .test_chat_runtime import call, corpus, session, submit, finish


def test_explicit_general_mode_bypasses_corpus_and_regeneration_preserves_choice(runtime):
    rt = runtime
    corpus(rt)
    s = session(rt)
    original = finish(rt, submit(rt, s))
    snapshot = deepcopy(original)
    # An unavailable textbook ranking configuration cannot block an explicitly
    # independent general-knowledge request; it is never loaded in that mode.
    rt.settings.chat_retrieval_config = "missing-textbook-policy.json"
    receipt = call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {
            "content": "Explain what a software compiler does.",
            "use_profile": True,
            "answer_mode": "general_knowledge",
        },
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    retried = call(
        rt,
        "POST",
        "/answer-requests/" + receipt["request_id"] + "/retry",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    assert retried["request_id"] == receipt["request_id"] and retried["job_id"] != receipt["job_id"]
    receipt = retried
    with (
        patch.object(service, "retrieve") as retrieve,
        patch.object(service, "rerank_candidates") as rerank,
    ):
        answer = finish(rt, receipt)
    retrieve.assert_not_called()
    rerank.assert_not_called()
    assert answer["answer_mode"] == "general_knowledge"
    assert answer["source_provenance"] == "model_general_knowledge_unverified"
    assert answer["evidence"] == answer["response"]["citations"] == []
    assert answer["model_mode"] == "mock" and answer["response"]["response_type"] == "refusal"
    assert answer["conversation_snapshot"]["messages"]
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.release_id is None and req.command["answer_mode"] == "general_knowledge"
        assert req.command["answer_mode_policy"] == "explicit_per_request_v1"
        assert (
            req.command["retrieval_policy"] is None and req.command["facet_fallback_policy"] is None
        )
        assert req.trace["evidence_strategy"] == "general_knowledge_no_textbook_retrieval"
    regeneration = call(
        rt,
        "POST",
        "/answers/" + answer["id"] + "/regenerate",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with patch.object(service, "retrieve") as retrieve:
        assert rt.work()
    retrieve.assert_not_called()
    failed_revision = call(rt, "GET", "/jobs/" + regeneration["job_id"])
    assert (
        failed_revision["state"] == "failed"
        and failed_revision["error"]["code"] == "REGENERATION_FAILED"
    )
    with rt.db() as db:
        revision = db.get(AnswerRequest, regeneration["request_id"])
        assert (
            revision.command["answer_mode"] == "general_knowledge" and revision.release_id is None
        )
    assert (
        call(rt, "GET", f"/sessions/{s['id']}/messages")["items"][-1]["active_answer_id"]
        == answer["id"]
    )
    # The old answer and snapshots remain exactly stored; only dynamic tail
    # regeneration eligibility legitimately changes after new messages arrive.
    reread = call(rt, "GET", "/answers/" + original["id"])
    assert {k: v for k, v in reread.items() if k != "can_regenerate"} == {
        k: v for k, v in snapshot.items() if k != "can_regenerate"
    }
    rt.settings.chat_retrieval_config = None
    textbook = finish(rt, submit(rt, s, "What is photosynthesis?"))
    assert (
        textbook["answer_mode"] == "textbook"
        and textbook["source_provenance"] == "textbook_evidence"
    )
    assert textbook["evidence"]


def test_invalid_general_mode_is_rejected_without_submission(runtime):
    rt = runtime
    s = session(rt)
    call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": "Hello", "answer_mode": "automatic"},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        422,
    )
    assert call(rt, "GET", f"/sessions/{s['id']}/messages")["items"] == []


def test_default_mode_preserves_legacy_idempotency_and_explicit_general_is_distinct(runtime):
    rt = runtime
    s = session(rt)
    key = str(uuid4())
    receipt = submit(rt, s, "Hello", key=key)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.body_hash == service.digest({"content": "Hello", "use_profile": True})
        req.command = {
            name: value
            for name, value in req.command.items()
            if name not in ("answer_mode", "answer_mode_policy")
        }
        db.commit()
    repeated = call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": "Hello", "answer_mode": "textbook"},
        {**rt.headers(), "Idempotency-Key": key},
        202,
    )
    assert repeated == receipt
    call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": "Hello", "answer_mode": "general_knowledge"},
        {**rt.headers(), "Idempotency-Key": key},
        409,
    )
    answer = finish(rt, receipt)
    assert answer["answer_mode"] == "textbook"
