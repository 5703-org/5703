"""Within-session selection, attribution, clarification and topic movement."""

from copy import deepcopy
from conversation import prepare_query, select_context, summarize
from conversation.summary import summary_is_valid


def exchange(number, topic="photosynthesis"):
    return [
        {
            "id": f"u{number}",
            "session_id": "s1",
            "sequence": 2 * number - 1,
            "role": "user",
            "content": f"Explain {topic}",
            "state": "completed",
        },
        {
            "id": f"a{number}",
            "session_id": "s1",
            "sequence": 2 * number,
            "role": "assistant",
            "content": f"A supported answer about {topic}.",
            "state": "answered",
            "active_answer_id": f"answer{number}",
        },
    ]


def test_context_ownership_cutoff_revisions_and_completed_pairs():
    data = exchange(1) + exchange(2)
    data += [
        {"id": "foreign", "session_id": "s2", "sequence": 1, "role": "user", "content": "Private"}
    ]
    data += [
        {
            "id": "error",
            "session_id": "s1",
            "sequence": 5,
            "role": "assistant",
            "content": "Bad partial output",
            "state": "error",
        }
    ]
    snapshot = select_context("s1", data, 4)
    assert [m.message_id for m in snapshot.messages] == ["u1", "a1", "u2", "a2"]
    assert snapshot.messages[-1].answer_id == "answer2"
    assert {e["reason"] for e in snapshot.exclusions} == {"foreign_session", "after_cutoff"}
    data[-1]["sequence"] = 3
    assert "incomplete_or_failed" in {e["reason"] for e in select_context("s1", data, 4).exclusions}


def test_long_history_summary_is_attributable_and_nonoverlapping():
    data = [m for i in range(1, 11) for m in exchange(i)]
    snapshot = select_context("s1", data, 20)
    assert len(snapshot.messages) == 12
    assert snapshot.summary_id and snapshot.summary_text
    assert snapshot.covered_until_sequence < snapshot.messages[0].sequence
    assert not any(f"[{m.message_id}]" in snapshot.summary_text for m in snapshot.messages)
    assert select_context("new-session", data, 20).messages == []
    assert snapshot.token_budget["history_tokens"] <= 2000
    assert snapshot.token_budget["summary_tokens"] <= 512


def test_summary_revision_or_content_change_invalidates():
    data = exchange(1)
    summary = summarize(data, session_id="s1")
    assert summary_is_valid(summary, data, 2)
    changed = deepcopy(data)
    changed[1]["active_answer_id"] = "new-revision"
    assert not summary_is_valid(summary, changed, 2)
    changed = deepcopy(data)
    changed[0]["content"] = "A changed user topic"
    assert not summary_is_valid(summary, changed, 2)
    assert not summary_is_valid(summary, data, 1)


def test_summary_failure_keeps_bounded_recent_history_and_records_lost_prefix(monkeypatch):
    def unavailable(*args, **kwargs):
        raise RuntimeError("Authored failure; no provider call is made")

    monkeypatch.setattr("conversation.context.summarize", unavailable)
    data = [m for i in range(1, 11) for m in exchange(i)]
    snapshot = select_context("s1", data, 20)
    assert [m.message_id for m in snapshot.messages] == [
        f"{role}{i}" for i in range(5, 11) for role in ("u", "a")
    ]
    assert snapshot.summary_text is None and snapshot.summary_id is None
    assert snapshot.token_budget["summary_tokens"] == 0
    assert snapshot.token_budget["summary_warning"]["code"] == "SUMMARY_UNAVAILABLE"
    assert {
        item["message_id"]
        for item in snapshot.exclusions
        if item["reason"] == "summary_unavailable"
    } == {f"{role}{i}" for i in range(1, 5) for role in ("u", "a")}


def test_query_has_actual_referent_and_no_guessed_answer():
    query = prepare_query("Why does it need light?", exchange(1))
    assert query.standalone_query == "Why does photosynthesis need light?"
    assert query.referenced_message_ids == ["u1"]
    assert query.intent == "follow_up" and not query.needs_clarification
    assert "chlorophyll" not in query.standalone_query
    assert prepare_query("Explain that again", []).needs_clarification
    simple = prepare_query("Explain that again", exchange(1))
    assert "photosynthesis" in simple.standalone_query and simple.intent == "reexplain"


def test_new_topic_comparison_correction_and_explicit_example():
    assert prepare_query("What is osmosis?", exchange(1)).topic_relation == "new_topic"
    comparison = prepare_query("Compare it with cellular respiration", exchange(1))
    assert comparison.intent == "comparison" and "photosynthesis" in comparison.standalone_query
    assert prepare_query("Give an example of diffusion", []).intent == "reexplain"
    for text in (
        "Give an example of diffusion",
        "Show sources for diffusion",
        "Citations about osmosis",
    ):
        changed = prepare_query(text, exchange(1))
        assert changed.topic_relation == "new_topic" and not changed.referenced_message_ids
        assert "photosynthesis" not in changed.standalone_query
    source = prepare_query("Show sources for that", exchange(1))
    assert source.topic_relation == "same_topic" and source.referenced_message_ids == ["u1"]
    corrected = exchange(1, "diffusion") + [
        {"id": "u2", "role": "user", "content": "I meant osmosis, not diffusion"}
    ]
    assert "osmosis" in prepare_query("Explain it again", corrected).standalone_query
    assert "diffusion" not in prepare_query("Explain it again", corrected).standalone_query
    ambiguous = [{"id": "u1", "role": "user", "content": "Compare photosynthesis and respiration"}]
    assert prepare_query("Why does it use energy?", ambiguous).needs_clarification


def test_local_clause_subject_is_not_replaced_with_an_old_session_topic():
    questions = [
        "What happens to the pressure of a gas when its volume decreases at constant temperature?",
        "What is photosynthesis and why does it need light?",
        "How do mitochondria produce energy while they consume oxygen?",
    ]
    for question in questions:
        for history in ([], exchange(1, "diffusion")):
            prepared = prepare_query(question, history)
            assert not prepared.needs_clarification
            assert prepared.standalone_query == question
            assert prepared.topic_relation == "new_topic"
            assert prepared.referenced_message_ids == []
    for question in (
        "What happens to it when it gets colder?",
        "Why and how does it work?",
        "Explain that again",
    ):
        assert prepare_query(question, []).needs_clarification
    contextual = prepare_query("Why does it need light?", exchange(1))
    assert contextual.referenced_message_ids == ["u1"]
    assert contextual.standalone_query == "Why does photosynthesis need light?"


def test_explicit_named_question_with_example_is_not_missing_referent():
    question = "Explain osmosis in detail, including membrane permeability, concentration gradients, and an example involving a cell."
    for history in ([], exchange(1, "photosynthesis")):
        result = prepare_query(question, history)
        assert not result.needs_clarification
        assert result.standalone_query == question
        assert result.topic_relation == "new_topic" and not result.referenced_message_ids


def test_local_relative_pronoun_survives_expansion_and_restatement_targets_latest_turn():
    from conversation.query import evidence_strategy

    history = exchange(1)
    history[0]["content"] = (
        "What is photosynthesis, and how do the light-dependent reactions and Calvin cycle work together?"
    )
    history += exchange(2)
    history[2]["content"] = "Why does it need water, and where does the released oxygen come from?"
    simplified = prepare_query("Explain that more simply.", history)
    assert simplified.referenced_message_ids == ["u2"]
    assert evidence_strategy(simplified.original_message, simplified.model_dump()) == "reuse_only"
    question = "Give an example of how the plant uses the sugar it produces."
    expanded = prepare_query(question, history)
    assert expanded.standalone_query == question + " Topic: photosynthesis."
    assert expanded.referenced_message_ids == ["u2"]
    assert evidence_strategy(question, expanded.model_dump()) == "retrieve_and_reuse"
