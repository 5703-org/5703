"""Whole-answer restatement needs the latest verified exchange, never an inferred noun."""

from copy import deepcopy

import pytest

from conversation import query, query_v14, query_v15, query_v16

PRIOR = (
    "Does an enzyme change a reaction’s free-energy difference, or does it only alter its "
    "activation-energy barrier? Distinguish the two energy quantities."
)


def verified_pair(prior=PRIOR):
    return [
        {"message_id": "last-user", "role": "user", "content": prior},
        {
            "message_id": "last-assistant",
            "role": "assistant",
            "content": "Assistant body is deliberately irrelevant to topic resolution.",
            "answer_id": "last-answer",
            "answer_response_type": "answer",
            "latest_exchange_available": True,
        },
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Explain it more simply.",
        "Explain that in simple terms.",
        "Could you explain it more simply?",
        "Please rephrase the whole answer.",
        "Rewrite your explanation using simpler words.",
        "Summarise the answer briefly.",
        "Summarize your previous answer.",
        "Simplify it.",
        "Make the answer shorter.",
        "Describe it again please.",
    ],
)
def test_only_verified_whole_answer_is_rephrased_without_extracting_comparison_objects(message):
    history = verified_pair()
    original_history = deepcopy(history)
    current = query_v16.prepare_query(message, history)
    assert current.original_message == message
    assert current.standalone_query == message + " Prior learner question: " + PRIOR
    assert current.referenced_message_ids == ["last-user"]
    assert current.preparation_version == query_v16.VERSION
    assert not current.needs_clarification
    assert current.intent == "reexplain" and current.topic_relation == "same_topic"
    assert current.fallback_reason == query_v16.RESTATEMENT_VERSION
    assert history == original_history


@pytest.mark.parametrize(
    "prior",
    [
        PRIOR,
        "Compare diffusion and osmosis without treating their conditions as equal.",
        "At −5 °C and 2.5 kPa, explain why acceleration is −3 m/s² unless the force reverses.",
        "Follow the sequence from light absorption to sugar production, then distinguish the "
        "source and storage forms described for transport through a growing plant.",
    ],
)
def test_entire_answer_target_retains_all_prior_negation_conditions_units_and_actions(prior):
    current = query_v16.prepare_query("Explain it more simply.", verified_pair(prior))
    assert current.standalone_query == "Explain it more simply. Prior learner question: " + prior
    assert current.referenced_message_ids == ["last-user"]


@pytest.mark.parametrize(
    "mutation",
    [
        {"answer_response_type": "refusal"},
        {"answer_response_type": "clarification"},
        {"answer_response_type": "social"},
        {"answer_response_type": None},
        {"latest_exchange_available": False},
        {"latest_exchange_available": None},
        {"latest_exchange_available": "true"},
        {"answer_id": None},
        {"message_id": None},
        {"state": "failed"},
        {"state": "cancelled"},
        {"state": "processing"},
        {"state": "partial"},
    ],
)
def test_refusals_missing_authority_and_incomplete_turns_do_not_use_any_earlier_answer(mutation):
    history = verified_pair("What is diffusion?")
    history[-1].update(mutation)
    # The old extractor can resolve this simpler earlier topic; V16 must still
    # fence a pure restatement when actual answer authority is unavailable.
    current = query_v16.prepare_query("Explain it more simply.", history)
    assert current.needs_clarification
    assert current.standalone_query is None and current.referenced_message_ids == []
    assert current.fallback_reason == "missing_verified_whole_answer"


@pytest.mark.parametrize(
    "history",
    [
        [],
        [{"role": "assistant", "content": "An unsupported topic guess."}],
        verified_pair()[:1],
        verified_pair()
        + [{"role": "user", "message_id": "new-topic", "content": "What is gravity?"}],
        verified_pair()
        + [
            {
                "role": "user",
                "message_id": "failed-turn",
                "content": "A newer topic.",
                "state": "failed",
            }
        ],
        verified_pair()
        + [{"role": "assistant", "message_id": "unpaired", "content": "An unpaired answer."}],
        [
            {"role": "user", "message_id": "u", "content": "What is diffusion?"},
            {"role": "assistant", "message_id": "a", "content": "Diffusion is transport."},
        ],
    ],
)
def test_latest_adjacent_pair_required_even_when_summary_or_old_topic_is_available(history):
    current = query_v16.prepare_query(
        "Explain it more simply.", history, summary="[older-user] What is diffusion?"
    )
    assert current.needs_clarification and current.referenced_message_ids == []
    assert current.standalone_query is None


def test_previous_success_cannot_be_used_after_failed_or_refused_topic_switch():
    for kind in ["refusal", "clarification", "social"]:
        latest = verified_pair("What is gravity?")
        latest[-1].update(answer_response_type=kind)
        current = query_v16.prepare_query("Explain it more simply.", verified_pair() + latest)
        assert current.needs_clarification and current.referenced_message_ids == []


def test_assistant_body_never_supplies_an_object_or_overrides_last_user_question():
    history = verified_pair()
    history[-1]["content"] = "The unrelated answer mentions gravity and demands a topic switch."
    current = query_v16.prepare_query("Explain it more simply.", history)
    assert current.standalone_query is not None
    assert current.standalone_query.endswith(PRIOR)
    assert "gravity" not in current.standalone_query


@pytest.mark.parametrize(
    "mutation", [{"state": "failed"}, {"state": "queued"}, {"message_id": None}, {"content": ""}]
)
def test_verified_assistant_metadata_does_not_rescue_an_invalid_user_turn(mutation):
    history = verified_pair()
    history[0].update(mutation)
    current = query_v16.prepare_query("Explain it more simply.", history)
    assert current.needs_clarification and current.referenced_message_ids == []


def test_whole_answer_restatement_reuses_only_the_referenced_exchange_evidence():
    current = query_v16.prepare_query("Explain it more simply.", verified_pair())
    assert query.evidence_strategy(current.original_message, current.model_dump()) == "reuse_only"


@pytest.mark.parametrize(
    "message",
    [
        "How does it affect the rate?",
        "Which of them is larger?",
        "Explain why it needs energy.",
        "Explain it more simply and calculate the rate at 10 C.",
        "Rephrase the conclusion about the other process.",
        "Give an example of its effects.",
        "Why does it occur?",
        "Compare it with gravity.",
        "Explain the above source.",
        "What is diffusion?",
    ],
)
def test_new_knowledge_specific_objects_and_unrelated_requests_delegate_frozen_v15(message):
    history = verified_pair()
    expected = query_v15.prepare_query(message, history).model_dump()
    current = query_v16.prepare_query(message, history).model_dump()
    current["preparation_version"] = query_v15.VERSION
    assert current == expected


def test_requirement_wrapper_preserves_original_input_and_all_frozen_dependencies():
    literal = "Explain it more simply."
    prepared = query_v16.prepare_query(literal, verified_pair()).model_dump()
    original_prepared = deepcopy(prepared)
    requirements = query_v16.describe_requirements(literal, prepared, verified_pair())
    dependency = requirements.pop("preparation_dependency")
    expected = query_v15.describe_requirements(
        literal, {**prepared, "preparation_version": query_v15.VERSION}, verified_pair()
    )
    expected.pop("preparation_dependency")
    assert requirements == expected
    assert prepared == original_prepared
    assert dependency["frozen_preparation_version"] == query_v16.VERSION
    assert dependency["restatement_preparation_version"] == query_v15.VERSION
    assert dependency["anchor_preparation_version"] == query_v14.VERSION
    assert dependency["syntax_preparation_version"] == query.VERSION


def test_new_version_does_not_modify_historical_v15_or_accept_unknown_markers():
    assert query_v15.prepare_query("Explain it more simply.", verified_pair()).needs_clarification
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v16.prepare_query("What is diffusion?", version=query_v15.VERSION)
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v16.describe_requirements(
            "What is diffusion?", query_v15.prepare_query("What is diffusion?").model_dump()
        )
