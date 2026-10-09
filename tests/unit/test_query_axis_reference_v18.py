"""Authored axis-reference cases assert identity, scope and frozen coordinates."""

from copy import deepcopy
import hashlib
from unittest.mock import Mock

import pytest

from conversation import query_v17, query_v18
from conversation.query import evidence_strategy

PRIOR = "Compare DNA and RNA in their sugars, nitrogenous bases and usual strand structure. Explain each difference separately."
CURRENT = "Explain the sugar difference in simpler language."


def pair(prior=PRIOR, response_type="refusal"):
    return [
        {"role": "user", "content": prior, "message_id": "owned-user"},
        {
            "role": "assistant",
            "content": "AUTHORED_ASSISTANT_BODY_IS_NOT_REFERENCE_AUTHORITY",
            "message_id": "owned-assistant",
            "answer_id": "owned-answer",
            "answer_response_type": response_type,
            "latest_exchange_available": True,
        },
    ]


def extract(current=CURRENT, history=None):
    history = pair() if history is None else history
    prepared = query_v18.prepare_query(current, history).model_dump()
    return prepared, query_v18.describe_requirements(current, prepared, history)


@pytest.mark.parametrize("response_type", ["answer", "refusal"])
def test_explicit_axis_uses_owned_user_question_and_new_retrieval(response_type):
    history = pair(response_type=response_type)
    before = deepcopy(history)
    prepared, requirements = extract(history=history)
    assert prepared["needs_clarification"] is False
    assert prepared["intent"] == "comparison"
    assert prepared["topic_relation"] == "same_topic"
    assert prepared["referenced_message_ids"] == ["owned-user"]
    assert prepared["fallback_reason"] == query_v18.RESOLUTION_VERSION
    assert evidence_strategy(CURRENT, prepared) == "retrieve_and_reuse"
    assert prepared["standalone_query"].startswith(CURRENT + "\n")
    assert PRIOR in prepared["standalone_query"]
    assert history[-1]["content"] not in prepared["standalone_query"]
    (point,) = requirements["required_knowledge"]
    assert point["objects"] == ["DNA", "RNA"]
    assert point["requested_axes"] == ["sugars"]
    assert "nitrogenous bases" not in point["requested_axes"]
    assert point["intent"] == "comparison"
    assert requirements["requirement_source_text"] == CURRENT
    assert requirements["original_question_hash"] == hashlib.sha256(CURRENT.encode()).hexdigest()
    assert requirements["version"] == "question_requirements_v5"
    assert history == before


@pytest.mark.parametrize(
    "prior,current,objects,axis",
    [
        (
            "Compare cathodes and anodes in their charges and electron flow.",
            "Describe the charge comparison briefly.",
            ["cathodes", "anodes"],
            "charges",
        ),
        (
            "Compare water and ethanol in their boiling points and densities.",
            "Explain the boiling point difference in plain language.",
            ["water", "ethanol"],
            "boiling points",
        ),
        (
            "Compare diffusion and active transport in their energy requirements and movement directions.",
            "Explain the energy requirement difference in simpler terms.",
            ["diffusion", "active transport"],
            "energy requirements",
        ),
        (
            PRIOR,
            "Describe the structure comparison briefly.",
            ["DNA", "RNA"],
            "usual strand structure",
        ),
        (PRIOR, "Explain the sugar differences in simpler language.", ["DNA", "RNA"], "sugars"),
    ],
)
def test_axis_recovery_is_generic_and_every_accepted_variant_retrieves(
    prior, current, objects, axis
):
    prepared, requirements = extract(current, pair(prior))
    assert prepared["fallback_reason"] == query_v18.RESOLUTION_VERSION
    assert evidence_strategy(current, prepared) == "retrieve_and_reuse"
    (point,) = requirements["required_knowledge"]
    assert point["objects"] == objects
    assert point["requested_axes"] == [axis]


@pytest.mark.parametrize("padding", ["", "  ", "\t "])
def test_current_and_prior_offsets_use_separate_literal_source_spaces(padding):
    original = padding + CURRENT + padding
    prior = padding + PRIOR + padding
    prepared, requirements = extract(original, pair(prior))
    assert prepared["original_message"] == CURRENT
    assert requirements["original_message"] == original
    assert requirements["requirement_source_text"] == original
    resolution = requirements["comparison_axis_resolution"]
    assert resolution["prior_source_text"] == prior
    assert resolution["prior_source_sha256"] == hashlib.sha256(prior.encode()).hexdigest()
    current_span = resolution["current_axis_span"]
    assert current_span["coordinate_space"] == "requirement_source_text"
    assert original[current_span["start"] : current_span["end"]] == current_span["text"] == "sugar"
    prior_span = resolution["prior_axis_span"]
    assert prior_span["coordinate_space"] == "prior_source_text"
    assert prior[prior_span["start"] : prior_span["end"]] == prior_span["text"] == "sugars"
    for point in requirements["required_knowledge"]:
        span = point["request_span"]
        assert original[span["start"] : span["end"]] == point["verbatim_request"]
    assert resolution["human_rating"] is None
    assert resolution["semantic_equivalence"] is None
    assert resolution["semantic_sufficiency"] is None


def test_conditions_negation_and_decimal_units_remain_literal_and_required():
    prior = "Compare diffusion and active transport in their energy requirements and movement directions at 25 C without assuming equilibrium."
    current = (
        "Explain the energy requirement difference at 5.0 atm without assuming ideal conditions."
    )
    prepared, requirements = extract(current, pair(prior))
    assert prepared["fallback_reason"] == query_v18.RESOLUTION_VERSION
    assert prior in prepared["standalone_query"] and current in prepared["standalone_query"]
    (point,) = requirements["required_knowledge"]
    assert point["requested_axes"] == ["energy requirements"]
    assert "5.0 atm" in point["conditions"]
    assert "25 C" in point["conditions"]
    assert "without" in point["conditions"]
    for spans in requirements["preserved_constraints"].values():
        for span in spans:
            assert current[span["start"] : span["end"]] == span["text"]
    for spans in requirements["comparison_axis_resolution"]["inherited_constraints"].values():
        for span in spans:
            assert span["coordinate_space"] == "prior_source_text"
            assert prior[span["start"] : span["end"]] == span["text"]


@pytest.mark.parametrize(
    "current",
    [
        "Explain the difference in simpler language.",
        "Explain its sugar difference in simpler language.",
        "Explain the cost difference in simpler language.",
        "Explain the sugar and structure difference in simpler language.",
        "Explain the sugar difference in plain language about light reactions.",
        "Explain the sugar difference in simpler language and explain ATP.",
        "Explain the sugar difference when heated and how ATP works.",
        "Explain the sugar difference when heated. Explain ATP.",
        "Explain the sugar difference when heated and provide an ATP example.",
        "Explain the DNA sugar difference in simpler language.",
        "Explain it more simply.",
        "Summarize the whole answer.",
    ],
)
def test_unclear_whole_or_new_topic_requests_preserve_v17_semantics(current):
    old = query_v17.prepare_query(current, pair()).model_dump()
    new = query_v18.prepare_query(current, pair()).model_dump()
    assert new.pop("preparation_version") == query_v18.VERSION
    old.pop("preparation_version")
    assert new == old


@pytest.mark.parametrize(
    "field,value",
    [
        ("latest_exchange_available", False),
        ("latest_exchange_available", None),
        ("answer_id", None),
        ("message_id", None),
        ("answer_response_type", None),
        ("answer_response_type", "social"),
        ("answer_response_type", "clarification"),
        ("state", "failed"),
        ("state", "processing"),
        ("state", "pending"),
    ],
)
def test_missing_or_non_factual_completed_pair_does_not_recover(field, value):
    history = pair()
    history[-1][field] = value
    prepared = query_v18.prepare_query(CURRENT, history)
    assert prepared.needs_clarification is True
    assert prepared.fallback_reason != query_v18.RESOLUTION_VERSION


@pytest.mark.parametrize("state", ["failed", "pending", "processing", "cancelled"])
def test_unavailable_user_turn_cannot_supply_the_comparison(state):
    history = pair()
    history[0]["state"] = state
    assert query_v18.prepare_query(CURRENT, history).fallback_reason != query_v18.RESOLUTION_VERSION


@pytest.mark.parametrize(
    "prior",
    [
        "Compare the first and the second in their sugars and usual strand structure.",
        "Compare the one and the other in their sugars and usual strand structure.",
        "Compare DNA and RNA and proteins in their sugars and usual strand structure.",
        "Compare DNA and RNA in their molecular sugars and dietary sugars.",
        "Compare DNA and RNA in their sugars and sugars.",
        "Compare DNA and DNA in their sugars and usual strand structure.",
        "Compare DNA and RNA.",
        "What is photosynthesis?",
    ],
)
def test_unresolved_objects_axes_and_changed_topic_cannot_be_imported(prior):
    history = pair(prior)
    prepared = query_v18.prepare_query(CURRENT, history)
    assert prepared.fallback_reason != query_v18.RESOLUTION_VERSION
    old = query_v17.prepare_query(CURRENT, history).model_dump()
    new = prepared.model_dump()
    old.pop("preparation_version")
    new.pop("preparation_version")
    assert new == old


def test_ambiguous_axis_head_cannot_choose_one_of_two_prior_axes():
    prior = "Compare DNA and RNA in their molecular structure and usual strand structure."
    prepared = query_v18.prepare_query(
        "Explain the structure difference in simpler language.", pair(prior)
    )
    assert prepared.needs_clarification is True
    assert prepared.fallback_reason != query_v18.RESOLUTION_VERSION


def test_summary_or_older_pair_cannot_replace_an_unavailable_latest_exchange():
    assert query_v18.prepare_query(CURRENT, [], PRIOR).needs_clarification is True
    history = pair() + [
        {"role": "user", "content": "A later unfinished question.", "message_id": "new-user"}
    ]
    prepared = query_v18.prepare_query(CURRENT, history, PRIOR)
    assert prepared.fallback_reason != query_v18.RESOLUTION_VERSION
    old = query_v17.prepare_query(CURRENT, history, PRIOR).model_dump()
    new = prepared.model_dump()
    old.pop("preparation_version")
    new.pop("preparation_version")
    assert new == old


def test_frozen_axis_description_fails_when_the_bound_pair_is_missing_or_changed():
    prepared, _ = extract()
    with pytest.raises(ValueError, match="reference is unavailable"):
        query_v18.describe_requirements(CURRENT, prepared, [])
    changed = pair()
    changed[0]["message_id"] = "different-user"
    with pytest.raises(ValueError, match="reference is unavailable"):
        query_v18.describe_requirements(CURRENT, prepared, changed)


def test_same_ids_cannot_bind_a_different_prior_source_or_current_literal():
    prepared, _ = extract()
    changed = pair("Compare glucose and fructose in their sugars and structures.")
    with pytest.raises(ValueError, match="reference is unavailable"):
        query_v18.describe_requirements(CURRENT, prepared, changed)
    with pytest.raises(ValueError, match="reference is unavailable"):
        query_v18.describe_requirements("Describe the sugar comparison briefly.", prepared, pair())


def test_non_axis_messages_keep_every_previous_semantic_field():
    for message in ["What is photosynthesis?", "What is RAG?", "Compare acids and bases.", "Hello"]:
        old = query_v17.prepare_query(message, pair()).model_dump()
        new = query_v18.prepare_query(message, pair()).model_dump()
        assert new.pop("preparation_version") == query_v18.VERSION
        old.pop("preparation_version")
        assert new == old


@pytest.mark.parametrize("response_type", ["answer", "refusal"])
def test_whole_answer_restatement_keeps_the_previous_authority_rules(response_type):
    history = pair(response_type=response_type)
    current = "Explain it more simply."
    old = query_v17.prepare_query(current, history).model_dump()
    new = query_v18.prepare_query(current, history).model_dump()
    old.pop("preparation_version")
    new.pop("preparation_version")
    assert new == old


def test_invalid_frozen_versions_are_rejected():
    with pytest.raises(ValueError, match="frozen query preparation version"):
        query_v18.prepare_query(CURRENT, pair(), version=query_v17.VERSION)
    with pytest.raises(ValueError, match="frozen query preparation dependency"):
        query_v18.describe_requirements(CURRENT, query_v17.prepare_query(CURRENT).model_dump())


@pytest.mark.parametrize("enhancement", [None, "learning_enhancement_v1"])
def test_unknown_v18_axis_clarifies_without_generation_or_checker_calls(enhancement):
    from generation import GenerationRequest, GenerationService

    question = "Explain the cost difference in simpler language."
    prepared, understanding = extract(question)
    assert prepared["needs_clarification"] is True
    generator, checker = Mock(), Mock()
    outcome = GenerationService(generator, checker_adapter=checker).generate(
        GenerationRequest(
            request_id="authored-v18-clarification",
            mode="interactive_chat",
            condition="E1",
            question=question,
            prepared_query=prepared,
            understanding=understanding,
            history=pair(),
            enhancement_version=enhancement,
        )
    )
    assert outcome.error is None
    assert outcome.response["response_type"] == "clarification"
    assert outcome.response["citations"] == []
    assert outcome.budget["consumed_calls"] == 0
    assert outcome.response_origin == "programmatic_ambiguity_clarification"
    generator.generate.assert_not_called()
    checker.generate.assert_not_called()


def test_legacy_v17_clarification_accounting_is_unchanged():
    from generation import GenerationRequest, GenerationService

    question = "Explain the cost difference in simpler language."
    prepared = query_v17.prepare_query(question, pair()).model_dump()
    outcome = GenerationService().generate(
        GenerationRequest(
            request_id="authored-frozen-v17-clarification",
            mode="interactive_chat",
            condition="E1",
            question=question,
            prepared_query=prepared,
            history=pair(),
        )
    )
    assert outcome.error is None
    assert outcome.response["response_type"] == "clarification"
    assert outcome.budget["consumed_calls"] == 1


def test_v18_practice_keeps_public_conditions_and_excludes_private_grading():
    from conversation.practice_context import VERSION, resolve

    literal = "Help me with the current practice step without giving the answer."
    teaching = {
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "owned-v18-step",
            "progress_version": 1,
            "current_step": 1,
            "prompt": "Describe the energy source used by photosynthetic organisms.",
            "current_step_prompt": "Identify the energy input under the stated conditions.",
            "conditions": ["Assume 25 C and no artificial illumination."],
            "concepts": ["photosynthesis"],
            "source": {"source_unit_id": "owned-source"},
            "private_rubric": {"answer_key": "PRIVATE_V18_GRADING_CANARY"},
        },
        "turn_role": "user_question",
    }
    prepared, requirements = resolve(
        literal,
        query_v18.prepare_query(literal).model_dump(),
        teaching,
        policy=VERSION,
        preparation_version=query_v18.VERSION,
    )
    assert prepared["preparation_version"] == query_v18.VERSION
    assert prepared["original_message"] == literal
    assert "25 C and no artificial illumination" in prepared["standalone_query"]
    assert "PRIVATE_V18_GRADING_CANARY" not in repr((prepared, requirements))
    assert requirements["version"] == "question_requirements_v5"
    assert requirements["preparation_dependency"]["frozen_preparation_version"] == query_v18.VERSION
    source = requirements["requirement_source_text"]
    for point in requirements["required_knowledge"]:
        span = point["request_span"]
        assert source[span["start"] : span["end"]] == point["verbatim_request"]
