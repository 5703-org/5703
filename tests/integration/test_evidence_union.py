"""Real disposable PostgreSQL source membership and current-query score boundaries."""

import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from app.modules.knowledge.models import Document, Chunk, ActiveCorpus
from conversation.query import VERSION, LEGACY_VERSION
from retrieval.relevance import MODEL, REVISION
from .test_chat_runtime import corpus, session, submit, finish
from .test_chat_retrieval_policy import POLICY


def test_new_request_persists_requirements_and_legacy_version_is_frozen(runtime):
    rt = runtime
    corpus(rt)
    s = session(rt)
    message = "Why does photosynthesis not happen without light at 20 C?"
    receipt = submit(rt, s, message)
    finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command["preparation_version"] == VERSION
        assert req.trace["understanding"]["original_message"] == message
        assert req.trace["understanding"]["constraints"]["negation"] == ["not", "without"]
        assert "20 C" in req.trace["understanding"]["constraints"]["numbers"]
        for key in ("coverage_estimate", "evidence_packing", "citation_audit", "teaching_plan"):
            assert req.trace[key] == req.trace["token_budget"][key]
    legacy = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        req = db.get(AnswerRequest, legacy["request_id"])
        req.command = {
            key: value
            for key, value in req.command.items()
            if key not in ("preparation_version", "evidence_selection_policy")
        }
        db.commit()
    finish(rt, legacy)
    with rt.db() as db:
        req = db.get(AnswerRequest, legacy["request_id"])
        assert req.trace["prepared_query"]["preparation_version"] == LEGACY_VERSION
        assert req.trace["understanding"] is None


def test_prior_citation_outside_new_release_cannot_be_reused(runtime):
    rt = runtime
    corpus(rt)
    s = session(rt)
    first = finish(rt, submit(rt, s))
    original = deepcopy(first)
    _, replacement = corpus(rt)
    follow = submit(rt, s, "Explain that more simply")
    with patch.object(service, "retrieve") as retrieval:
        second = finish(rt, follow)
        retrieval.assert_not_called()
    assert second["response"]["response_type"] == "refusal" and second["evidence"] == []
    with rt.db() as db:
        req = db.get(AnswerRequest, follow["request_id"])
        record = req.trace["retrieval_execution"]["inherited_evidence"]
        assert record["release_id"] == replacement["release_id"]
        assert record["eligible_count"] == 0
        assert record["excluded"] and all(
            row["reason"] == "outside_frozen_release" for row in record["excluded"]
        )
        assert not set(ev["chunk_id"] for ev in first["evidence"]) & set(
            ev["chunk_id"] for ev in second["evidence"]
        )
    assert first == original


@pytest.mark.parametrize(
    "mutation,reason", [("revoke", "source_unavailable"), ("hash", "source_identity_mismatch")]
)
def test_inherited_validation_rejects_current_visibility_and_identity_changes(
    runtime, mutation, reason
):
    rt = runtime
    corpus(rt)
    answer = finish(rt, submit(rt, session(rt)))
    with rt.db() as db:
        pointer = db.get(ActiveCorpus, 1)
        original = answer["evidence"][0]
        if mutation == "revoke":
            db.get(Document, original["asset_id"]).revoked = True
        else:
            db.get(Chunk, original["chunk_id"]).text_hash = "0" * 64
        db.flush()
        selected, trace = service.inherited_candidates(db, pointer.release_id, [original])
        assert selected == [] and trace["excluded"] == [
            {"chunk_id": original["chunk_id"], "reason": reason}
        ]
        db.rollback()


def test_fresh_and_prior_union_is_rescored_and_rejected_on_current_query(runtime, tmp_path):
    rt = runtime
    corpus(rt)
    s = session(rt)
    first = finish(rt, submit(rt, s))
    old_ids = {
        row["chunk_id"]
        for row in first["evidence"]
        if row["evidence_id"] in first["response"]["citations"]
    }
    assert old_ids
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(POLICY))
    rt.settings.chat_retrieval_config = str(path)
    rt.settings.chat_relevance_gate = True
    receipt = submit(rt, s, "Why does it need light?")
    actual_retrieve = service.retrieve
    seen = {}

    def fresh_only(*args, **kwargs):
        return [row for row in actual_retrieve(*args, **kwargs) if row["chunk_id"] not in old_ids]

    def current_rank(query, rows, policy, **kwargs):
        seen["query"] = query
        seen["rows"] = deepcopy(rows)
        return [
            {
                **row,
                "score": -10.0,
                "score_type": "cross_encoder",
                "reranker_model": MODEL,
                "reranker_revision": REVISION,
            }
            for row in rows
        ], {"policy": policy}

    with (
        patch.object(service, "retrieve", side_effect=fresh_only),
        patch.object(service, "rerank_candidates", side_effect=current_rank),
    ):
        answer = finish(rt, receipt)
    assert "photosynthesis" in seen["query"].casefold() and "light" in seen["query"]
    assert old_ids <= {row["chunk_id"] for row in seen["rows"]}
    assert all(row.get("inherited_from") for row in seen["rows"] if row["chunk_id"] in old_ids)
    assert len(seen["rows"]) <= POLICY["candidate_count"]
    assert answer["response"]["refusal_reason"] == "NO_EVIDENCE" and not answer["evidence"]
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        trace = req.trace["retrieval_execution"]
        assert old_ids <= set(trace["inherited_evidence"]["rescored_chunk_ids"])
        assert trace["relevance_gate"]["accepted_count"] == 0
        assert req.budget["consumed_calls"] == 0
