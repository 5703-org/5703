"""Topic changes retrieve afresh; resolved continuations reuse the paired answer."""

from unittest.mock import patch
from app.modules.answering.models import AnswerRequest
from app.modules.answering import service
from .test_chat_runtime import corpus, session, submit, finish


def test_explicit_new_topic_retrieves_and_resolved_followup_reuses_that_topic(runtime):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    photosynthesis = finish(rt, submit(rt, chat))
    with patch.object(service, "retrieve", wraps=service.retrieve) as retrieval:
        diffusion = finish(rt, submit(rt, chat, "Give an example of diffusion"))
        assert retrieval.call_count == 1
        assert retrieval.call_args.args[1] == "Give an example of diffusion"
        assert all(item["inherited_from"] is None for item in diffusion["evidence"])
        retrieval.reset_mock()
        sources = finish(rt, submit(rt, chat, "Show the sources for that"))
        assert retrieval.call_count == 0
        assert sources["evidence"] and all(
            item["inherited_from"]["request_id"] == diffusion["request_id"]
            for item in sources["evidence"]
        )
        assert all(
            item["inherited_from"]["request_id"] != photosynthesis["request_id"]
            for item in sources["evidence"]
        )
        with rt.db() as db:
            prepared = db.get(AnswerRequest, sources["request_id"]).trace["prepared_query"]
            assert prepared["topic_relation"] == "same_topic"
            assert "diffusion" in prepared["standalone_query"].lower()
            assert prepared["referenced_message_ids"]
        retrieval.reset_mock()
        new_sources = finish(rt, submit(rt, chat, "Show sources for photosynthesis"))
        with rt.db() as db:
            req = db.get(AnswerRequest, new_sources["request_id"])
            supplement = req.trace["retrieval_execution"]["coverage_supplement"]
            assert req.trace["prepared_query"]["intent"] == "source_request"
            assert req.trace["prepared_query"]["topic_relation"] == "new_topic"
        assert retrieval.call_count == 1, {
            "queries": [call.args[1] for call in retrieval.call_args_list],
            "supplement": supplement,
        }
        assert retrieval.call_args.args[1] == "Show sources for photosynthesis"
        assert supplement["retrieval_passes"] == 0 and not supplement["triggered"]
        assert all(item["inherited_from"] is None for item in new_sources["evidence"])


def test_restatement_reuses_but_expansion_retrieves_with_exact_trace(runtime):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    finish(rt, submit(rt, chat))
    with patch.object(service, "retrieve", wraps=service.retrieve) as retrieval:
        short = finish(rt, submit(rt, chat, "Explain that more simply"))
        assert retrieval.call_count == 0
        detailed = finish(rt, submit(rt, chat, "Give an example of that"))
        assert retrieval.call_count == 1
        assert "photosynthesis" in retrieval.call_args.args[1].casefold()
    with rt.db() as db:
        assert db.get(AnswerRequest, short["request_id"]).trace["evidence_strategy"] == "reuse_only"
        req = db.get(AnswerRequest, detailed["request_id"])
        assert req.trace["evidence_strategy"] == "retrieve_and_reuse"
        trace = req.trace["evidence_selection"]
        assert trace["candidate_count"] == len(trace["candidate_chunk_ids"])
        assert trace["submitted_count"] == len(detailed["evidence"])
        assert trace["submitted_chunk_ids"] == [item["chunk_id"] for item in detailed["evidence"]]
        assert trace["cited_count"] == len(detailed["response"]["citations"])
        assert set(trace["cited_evidence_ids"]) <= set(trace["submitted_evidence_ids"])


def test_named_detailed_question_retrieves_and_dependent_restatement_uses_latest_answer(runtime):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    finish(rt, submit(rt, chat))
    recent = finish(rt, submit(rt, chat, "Why does it need light?"))
    simple = finish(rt, submit(rt, chat, "Explain that more simply."))
    assert simple["evidence"]
    assert all(
        e["inherited_from"]["request_id"] == recent["request_id"] for e in simple["evidence"]
    )
    question = "Explain osmosis in detail, including membrane permeability, concentration gradients, and an example involving a cell."
    with patch.object(service, "retrieve", return_value=[]) as retrieval:
        no_source = finish(rt, submit(rt, session(rt), question))
    # V5 can try one bounded lookup for a named missing requirement after the
    # initial empty retrieval. Both passes still lead to a zero-model refusal.
    assert retrieval.call_count == 2
    assert retrieval.call_args_list[0].args[1] == question
    with rt.db() as db:
        req = db.get(AnswerRequest, no_source["request_id"])
        supplement = req.trace["retrieval_execution"]["coverage_supplement"]
        assert supplement["triggered"] and supplement["retrieval_passes"] == 1
        assert retrieval.call_args_list[1].args[1] == supplement["query"]
        assert retrieval.call_args_list[1].kwargs["top_k"] == supplement["candidate_limit"] == 10
        assert supplement["candidate_chunk_ids"] == []
        assert supplement["added_chunk_ids"] == []
        assert not req.trace["prepared_query"]["needs_clarification"]
        assert req.trace["response_origin"] == "programmatic_no_evidence"
        assert req.budget["consumed_calls"] == 0
