"""New requirements must retain every frozen V16 query meaning field."""

from copy import deepcopy

import pytest

from conversation import query_v16, query_v17


def verified_pair():
    return [
        {"role": "user", "content": "Compare diffusion and active transport.", "message_id": "u1"},
        {
            "role": "assistant",
            "content": "An owned checked answer.",
            "message_id": "a1",
            "answer_id": "answer1",
            "answer_response_type": "answer",
            "latest_exchange_available": True,
        },
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Compare diffusion and active transport. Explain each difference separately.",
        "What is osmosis and which conditions change its direction?",
        "Why is a catalyst useful, and when does its concentration affect the rate?",
        "How does a plant's light reaction differ from its Calvin cycle?",
        "If the gas is not ideal at 5.0 atm, why must temperature be in kelvin?",
        "Compare RAG1 with RAG2, without discussing AI.",
        "I mean RNA, not DNA.",
        "What is RAG?",
        "What is ragweed allergy?",
        "Explain it more simply.",
        "What is photosynthesis in this selected passage?",
        "In plain language, explain how sunlight supplies chemical energy.",
    ],
)
@pytest.mark.parametrize("history", [[], verified_pair()])
def test_preparation_preserves_every_semantic_field(message, history):
    before = deepcopy(history)
    old = query_v16.prepare_query(message, history).model_dump()
    new = query_v17.prepare_query(message, history).model_dump()
    assert new.pop("preparation_version") == query_v17.VERSION
    old.pop("preparation_version")
    assert new == old
    assert history == before


def test_verified_restatement_and_unavailable_turn_keep_v16_fences():
    for history in [verified_pair(), verified_pair() + [{"role": "user", "content": "Why?"}]]:
        old = query_v16.prepare_query("Explain it more simply.", history)
        new = query_v17.prepare_query("Explain it more simply.", history)
        assert new.standalone_query == old.standalone_query
        assert new.needs_clarification == old.needs_clarification
        assert new.referenced_message_ids == old.referenced_message_ids
        assert new.fallback_reason == old.fallback_reason


def test_dependency_uses_new_requirements_without_mutating_input():
    message = "Compare mitosis and meiosis. Explain each difference separately."
    prepared = query_v17.prepare_query(message).model_dump()
    before = deepcopy(prepared)
    result = query_v17.describe_requirements(message, prepared)
    assert prepared == before
    assert result["original_message"] == message
    assert result["version"] == "question_requirements_v5"
    dependency = result["preparation_dependency"]
    assert dependency["frozen_preparation_version"] == query_v17.VERSION
    assert dependency["restatement_preparation_version"] == query_v16.VERSION
    assert dependency["syntax_preparation_version"] == "conversation_preparer_v13"


def test_new_entrypoints_reject_other_frozen_versions():
    with pytest.raises(ValueError, match="frozen query preparation version"):
        query_v17.prepare_query("What is diffusion?", version=query_v16.VERSION)
    prepared = query_v16.prepare_query("What is diffusion?").model_dump()
    with pytest.raises(ValueError, match="frozen query preparation dependency"):
        query_v17.describe_requirements("What is diffusion?", prepared)


def test_v17_practice_keeps_public_conditions_without_private_rubric():
    from conversation.practice_context import VERSION, resolve

    literal = "Help me with the current practice step without giving the answer."
    teaching = {
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "owned-step-v17",
            "progress_version": 2,
            "current_step": 1,
            "prompt": "Describe the energy source used by photosynthetic organisms.",
            "current_step_prompt": "Identify the energy input under the stated conditions.",
            "conditions": ["Assume 25 C and no added artificial illumination."],
            "concepts": ["photosynthesis"],
            "source": {"source_unit_id": "authorized-source"},
            "private_rubric": {"answer_key": "PRIVATE_V17_RUBRIC_CANARY"},
        },
        "turn_role": "user_question",
    }
    prepared, requirements = resolve(
        literal,
        query_v17.prepare_query(literal).model_dump(),
        teaching,
        policy=VERSION,
        preparation_version=query_v17.VERSION,
    )
    assert prepared["preparation_version"] == query_v17.VERSION
    assert prepared["original_message"] == literal
    assert prepared["needs_clarification"] is False
    assert "25 C and no added artificial illumination" in prepared["standalone_query"]
    assert "PRIVATE_V17_RUBRIC_CANARY" not in repr((prepared, requirements))
    assert requirements["version"] == "question_requirements_v5"
    assert requirements["practice_reference_resolution"]["request_role"] == "teaching_instruction"
    assert requirements["preparation_dependency"]["frozen_preparation_version"] == query_v17.VERSION
    assert all("Help me" not in point["request"] for point in requirements["required_knowledge"])


def test_substantive_practice_question_keeps_requirement_coordinates_after_query_enrichment():
    from conversation.practice_context import VERSION, resolve

    question = "Which input changes the energy available to this process?"
    teaching = {
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "owned-coordinate-case",
            "progress_version": 1,
            "current_step": 1,
            "prompt": "Describe the energy source used by photosynthetic organisms.",
            "current_step_prompt": "Identify the energy input under the given conditions.",
            "conditions": ["Assume 25 C and no added artificial illumination."],
            "concepts": ["photosynthesis", "energy input"],
            "source": {"source_unit_id": "authorized-source"},
            "private_rubric": {"answer_key": "PRIVATE_COORDINATE_CANARY"},
        },
        "turn_role": "user_question",
    }
    prepared, requirements = resolve(
        question,
        query_v17.prepare_query(question).model_dump(),
        teaching,
        policy=VERSION,
        preparation_version=query_v17.VERSION,
    )
    assert prepared["original_message"] == question
    assert "Practice concepts: photosynthesis, energy input" in prepared["standalone_query"]
    source = requirements["requirement_source_text"]
    assert source != requirements["standalone_query"]
    assert "Current learner question: " + question in source
    assert "PRIVATE_COORDINATE_CANARY" not in repr((prepared, requirements))
    assert requirements["requirement_structure"]["coordinate_space"] == "requirement_source_text"
    for point in requirements["required_knowledge"]:
        span = point["request_span"]
        assert span["coordinate_space"] == "requirement_source_text"
        assert source[span["start"] : span["end"]] == point["verbatim_request"]
    assert any(
        requirements["standalone_query"][
            point["request_span"]["start"] : point["request_span"]["end"]
        ]
        != point["verbatim_request"]
        for point in requirements["required_knowledge"]
    )
