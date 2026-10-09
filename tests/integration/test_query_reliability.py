"""Frozen CPU/relevance routing against disposable PostgreSQL; authored model scores."""

from unittest.mock import patch
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from retrieval.relevance import MODEL, REVISION
from .test_chat_runtime import corpus, session, submit, finish
from .test_chat_retrieval_policy import POLICY


def test_cpu_override_freezes_and_preserves_corpus_configuration(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.local_model_device = "cpu"
    receipt = submit(rt, session(rt))
    rt.settings.local_model_device = "cuda"
    with patch.object(service, "retrieve", wraps=service.retrieve) as retrieval:
        finish(rt, receipt)
        assert retrieval.call_args.kwargs["runtime_device"] == "cpu"
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command["local_model_device"] == "cpu"
        assert req.trace["local_model_execution"]["resolved_device"] == "cpu"


def test_bare_acronym_skips_all_retrieval_and_paid_generation(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_relevance_gate = True
    receipt = submit(rt, session(rt), "Do you know what is rag")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    assert answer["evidence"] == []
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.budget["consumed_calls"] == 0


def test_low_relevance_is_saved_then_refused_without_model_call(runtime, tmp_path):
    import json

    rt = runtime
    corpus(rt)
    config = tmp_path / "retrieval.json"
    config.write_text(json.dumps(POLICY))
    rt.settings.chat_retrieval_config = str(config)
    rt.settings.chat_relevance_gate = True
    receipt = submit(rt, session(rt), "Explain RAG in AI")
    rt.settings.chat_relevance_gate = False

    def rank(query, rows, policy):
        return [
            {
                **r,
                "score": -10.0,
                "score_type": "cross_encoder",
                "reranker_model": MODEL,
                "reranker_revision": REVISION,
            }
            for r in rows
        ], {}

    with patch.object(service, "rerank_candidates", side_effect=rank):
        answer = finish(rt, receipt)
    assert answer["response"]["refusal_reason"] == "NO_EVIDENCE"
    assert answer["evidence"] == []
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        gate = req.trace["retrieval_execution"]["relevance_gate"]
        assert gate["candidate_count"] > 0 and gate["accepted_count"] == 0
        assert gate["excluded"] and req.budget["consumed_calls"] == 0


def test_old_queued_request_has_no_device_or_gate_override(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        req.command = {
            k: v
            for k, v in req.command.items()
            if k not in {"local_model_device", "relevance_policy"}
        }
        db.commit()
    with patch.object(service, "retrieve", wraps=service.retrieve) as retrieval:
        finish(rt, receipt)
        assert "runtime_device" not in retrieval.call_args.kwargs


def test_auto_does_not_require_optional_torch_for_mock_corpus(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.local_model_device = "auto"
    with patch.object(service, "resolve_device", side_effect=AssertionError("Torch is optional")):
        assert finish(rt, submit(rt, session(rt)))["response"]["response_type"] == "answer"
