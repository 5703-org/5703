"""Real disposable PostgreSQL, authored corpus and explicit fake local scores."""

import json
from unittest.mock import patch
import pytest
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from conversation.query import LOCAL_QUESTION_VERSION
from retrieval.relevance import MODEL, REVISION
from .test_chat_runtime import call, corpus, session, submit, finish
from .test_chat_retrieval_policy import POLICY

PARTIAL = "Explain photosynthesis. Also give tomorrow’s exact Bitcoin price."


def configure(rt, tmp_path):
    corpus(rt)
    path = tmp_path / "facet-policy.json"
    path.write_text(json.dumps(POLICY))
    rt.settings.chat_retrieval_config = str(path)
    rt.settings.chat_relevance_gate = True


def ranking(query, rows, policy, **kwargs):
    assert policy == POLICY
    return [
        {
            **row,
            "score": 1.0
            if query == "Explain photosynthesis" and "Photosynthesis" in row["text"]
            else -10.0,
            "score_type": "cross_encoder",
            "reranker_model": MODEL,
            "reranker_revision": REVISION,
        }
        for row in rows
    ], {"policy": policy}


@pytest.mark.parametrize("version", ["conversation_preparer_v9", LOCAL_QUESTION_VERSION])
def test_partial_support_uses_frozen_facets_only_for_new_requests(runtime, tmp_path, version):
    rt = runtime
    configure(rt, tmp_path)
    receipt = submit(rt, session(rt), PARTIAL)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        req.command = {**req.command, "preparation_version": version}
        db.commit()
    with (
        patch.object(service, "rerank_candidates", side_effect=ranking) as ranker,
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieve,
    ):
        answer = finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command["question"] == PARTIAL
        assert req.trace["understanding"]["original_message"] == PARTIAL
        assert req.trace["retrieval_execution"]["relevance_gate"]["accepted_count"] == 0
        if version == "conversation_preparer_v9":
            trace = req.trace["retrieval_execution"]["facet_fallback"]
            assert trace["triggered"] and trace["reason"] == "fallback_completed"
            assert len(trace["attempted_facets"]) == 2
            assert req.trace["retrieval_execution"]["final_selection"]["accepted_count"] > 0
            assert ranker.call_count == retrieve.call_count == 3
            assert req.trace["coverage_estimate"]["status"] == "partial"
            assert req.trace["evidence_selection"]["submitted_count"] > 0
            assert req.budget["active_seconds"] > 0
        else:
            assert "facet_fallback" not in req.trace["retrieval_execution"]
            assert ranker.call_count == retrieve.call_count == 1
            assert req.budget["consumed_calls"] == 0
    # The mock whole-question guard can still refuse: admission is not a claim
    # that a mock answer correctly expresses the supported/unsupported parts.
    assert "Bitcoin" not in str(answer["response"].get("compact_answer"))


def test_expired_shared_budget_prevents_any_facet_model_call(runtime, tmp_path):
    rt = runtime
    configure(rt, tmp_path)
    receipt = submit(rt, session(rt), PARTIAL)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        req.budget = {**req.budget, "active_seconds": 180.0}
        db.commit()
    with (
        patch.object(service, "rerank_candidates", side_effect=ranking) as ranker,
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieve,
        patch.object(service, "GenerationService") as generation,
    ):
        assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["error"]["code"] == "BUDGET_EXHAUSTED"
    assert ranker.call_count == retrieve.call_count == 1
    generation.assert_not_called()
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.budget["consumed_calls"] == 0 and req.budget["active_seconds"] >= 180
        assert req.trace["retrieval_execution"]["facet_fallback"]["reason"] == "budget_exhausted"
