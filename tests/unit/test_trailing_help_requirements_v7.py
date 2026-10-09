"""Literal span separation only; authored fixtures carry no semantic labels."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from conversation import query_v20, query_v21
from conversation.requirements_v7 import separate_embedded_help_depth

QUESTION = (
    "Why can prairie dogs get used to harmless footsteps, while a duckling follows "
    "the first adult it sees? Compare the kind of experience and timing involved "
    "in these two learning examples. Please give me one hint for this step."
)
ROOT = Path(__file__).resolve().parents[2]


def requirements(text, module=query_v21):
    return module.describe_requirements(text, module.prepare_query(text).model_dump())


def test_actual_g010_separates_only_final_help_sentence_and_preserves_science():
    old = requirements(QUESTION, query_v20)
    before = deepcopy(old)
    new = requirements(QUESTION)
    assert old == before
    assert new["version"] == "question_requirements_v7"
    assert old["presentation_requests"] == []
    assert new["required_knowledge"][0] == old["required_knowledge"][0] | {
        "presentation_request_ids": ["presentation_01"]
    }
    old_point, point = old["required_knowledge"][1], new["required_knowledge"][1]
    assert old_point["request_span"] == {
        "coordinate_space": "requirement_source_text",
        "start": 103,
        "end": 223,
    }
    assert point["request_span"] == {
        "coordinate_space": "requirement_source_text",
        "start": 103,
        "end": 184,
    }
    assert point["request"] == point["verbatim_request"] == QUESTION[103:184]
    for key in ("id", "intent", "relation", "conditions", "origin"):
        assert point[key] == old_point[key]
    assert point["id"] == "requirement_02"
    assert {"one", "hint", "step"}.isdisjoint(point["terms"])
    presentation = new["presentation_requests"][0]
    assert presentation["request"] == QUESTION[186:223]
    assert presentation["request_span"] == {
        "coordinate_space": "requirement_source_text",
        "start": 186,
        "end": 223,
    }
    assert presentation["original_requirement_id"] == point["id"]
    assert presentation["applies_to_requirement_ids"] == ["requirement_01", "requirement_02"]
    for key in (
        "original_message",
        "requirement_source_text",
        "standalone_query",
        "original_question_hash",
        "preserved_constraints",
        "intent",
        "topic_relation",
    ):
        assert new[key] == old[key]
    assert new["requested_facets"] == new["required_knowledge"]


@pytest.mark.parametrize("space", [" ", "\t", "\r\n", "  \t"])
@pytest.mark.parametrize(
    "clause", ["Please give me one hint for this step", "Please give me a hint"]
)
def test_raw_whitespace_and_help_case_coordinates_roundtrip(space, clause):
    text = "\t " + QUESTION[:185] + space + clause + ".  "
    old, new = requirements(text, query_v20), requirements(text)
    source = new["requirement_source_text"]
    assert source == old["requirement_source_text"]
    assert new["original_message"] == old["original_message"] == text
    assert len(new["presentation_requests"]) == 1
    point = new["required_knowledge"][1]
    span = point["request_span"]
    assert source[span["start"] : span["end"]] == point["request"]
    presentation = new["presentation_requests"][0]
    span = presentation["request_span"]
    assert source[span["start"] : span["end"]] == presentation["request"] == clause


def test_exact_raw_literal_coordinate_fixture_preserves_leading_tabs_and_spaces():
    baseline = requirements(QUESTION, query_v20)
    raw = " \t" + QUESTION + " \t"
    baseline["requirement_source_text"] = raw
    for point in baseline["required_knowledge"]:
        point["request_span"]["start"] += 2
        point["request_span"]["end"] += 2
    new = separate_embedded_help_depth(baseline)
    assert new["requirement_source_text"] == raw
    for point in new["required_knowledge"]:
        span = point["request_span"]
        assert raw[span["start"] : span["end"]] == point["request"]
    presentation = new["presentation_requests"][0]
    span = presentation["request_span"]
    assert raw[span["start"] : span["end"]] == presentation["request"]


@pytest.mark.parametrize(
    "text",
    [
        "Give me one hint. Please give me one hint for this step.",
        "Compare DNA and RNA and please give me one hint for this step.",
        "Compare DNA and RNA. Please give me one hint if the temperature is fixed.",
        "Compare DNA and RNA. Do not give me one hint for this step.",
        "Compare DNA and RNA. Please give me two hints for this step.",
        "Compare DNA and RNA. Please give me one hint for the earlier step.",
        "Compare DNA and RNA. Please give me one hint for this step and name a source.",
        "Compare DNA and RNA. Please give me one hint for this step. Calculate 2 + 3.",
        "Compare DNA and RNA.. Please give me one hint for this step.",
        "What does this demonstrate? Please give me one hint for this step.",
    ],
)
def test_unsupported_conditional_ambiguous_and_same_sentence_cases_keep_science(text):
    old, new = requirements(text, query_v20), requirements(text)
    assert new["required_knowledge"] == old["required_knowledge"]
    assert new["presentation_requests"] == old["presentation_requests"]
    assert "embedded_help_depth_separation" not in new


@pytest.mark.parametrize(
    "mutation", ["end", "start_bool", "foreign_space", "literal", "origin", "clarification"]
)
def test_invalid_frozen_literal_and_coordinate_cannot_carve_or_mutate(mutation):
    old = requirements(QUESTION, query_v20)
    point = old["required_knowledge"][1]
    if mutation == "end":
        point["request_span"]["end"] -= 1
    elif mutation == "start_bool":
        point["request_span"]["start"] = True
    elif mutation == "foreign_space":
        point["request_span"]["coordinate_space"] = "standalone_query"
    elif mutation == "literal":
        point["verbatim_request"] += " tampered"
    elif mutation == "origin":
        point["origin"] = "reader_reference_resolution"
    else:
        old["needs_clarification"] = True
    before = deepcopy(old)
    new = separate_embedded_help_depth(old)
    assert old == before
    assert new["required_knowledge"] == old["required_knowledge"]
    assert "embedded_help_depth_separation" not in new


def test_quantities_negation_conditions_and_requirement_identity_are_preserved():
    text = "Compare DNA and RNA at 300 K, not 280 K, without removing the strand condition. Please give me one hint for this step."
    old, new = requirements(text, query_v20), requirements(text)
    assert new["preserved_constraints"] == old["preserved_constraints"]
    assert new["preserved_constraints"]["quantities_and_units"]
    assert new["required_knowledge"][0]["conditions"] == old["required_knowledge"][0]["conditions"]
    assert "not 280 K" in new["required_knowledge"][0]["request"]
    assert "without removing" in new["required_knowledge"][0]["request"]


def test_preparation_and_json_transport_retain_frozen_original_and_version():
    old = query_v20.prepare_query(QUESTION).model_dump()
    new = query_v21.prepare_query(QUESTION).model_dump()
    assert new | {"preparation_version": old["preparation_version"]} == old
    transported = json.loads(json.dumps(new))
    data = query_v21.describe_requirements(QUESTION, transported)
    assert data["preparation_dependency"]["frozen_preparation_version"] == query_v21.VERSION
    assert data["preparation_dependency"]["requirements_version"] == "question_requirements_v7"
    assert data["standalone_query"] == QUESTION
    assert data["requirement_source_text"] == QUESTION
    assert json.loads(json.dumps(data)) == data
    with pytest.raises(ValueError):
        query_v21.describe_requirements(QUESTION, old)
    with pytest.raises(ValueError):
        query_v21.prepare_query(QUESTION, version=query_v20.VERSION)
    with pytest.raises(ValueError):
        separate_embedded_help_depth({"version": "question_requirements_v5"})


def test_historical_v20_still_contains_the_literal_help_in_scientific_span():
    old = requirements(QUESTION, query_v20)
    assert old["version"] == "question_requirements_v6"
    assert old["required_knowledge"][1]["request"] == QUESTION[103:223]
    assert old["presentation_requests"] == []


def _private_module(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v7_alias_reaches_existing_unit_lookup_without_threshold_or_scope_change():
    plan = _private_module("generation/unit_definition_plan_v1.py", "private_unit_definition").plan
    text = "Which pressure units are consistent with Pa?"
    old, new = requirements(text, query_v20), requirements(text)
    coverage = {"locatable_missing": [{"id": row["id"]} for row in old["required_knowledge"]]}
    assert plan(text, coverage, old) == plan(text, coverage, new)
    assert plan(text, coverage, new)["status"] != "unsupported_requirement_producer"
    assert (
        plan(text, coverage, {**new, "version": "question_requirements_v99"})["status"]
        == "unsupported_requirement_producer"
    )


def test_v7_alias_keeps_comparison_axis_literal_gate_and_rejects_tampering():
    explicit = _private_module(
        "retrieval/complementary_spans.py", "retrieval.private_complementary"
    )._explicit_axis_terms
    text = "Compare DNA and RNA in their sugars and structures."
    new = requirements(text)
    assert explicit(new)
    tampered = deepcopy(new)
    tampered["required_knowledge"][0]["request_span"]["end"] -= 1
    assert not explicit(tampered)


@pytest.mark.parametrize("enhancement", [None, "learning_enhancement_v1"])
def test_v21_clarification_consumer_retains_zero_generator_and_checker_calls(enhancement):
    from generation import GenerationRequest

    service = _private_module(
        "generation/service.py", "generation.private_service"
    ).GenerationService
    question = "What does this illustrate about a fixed action pattern?"
    prepared = query_v21.prepare_query(question).model_dump()
    understanding = query_v21.describe_requirements(question, prepared)
    assert prepared["needs_clarification"] is True
    generator, checker = Mock(), Mock()
    outcome = service(generator, checker_adapter=checker).generate(
        GenerationRequest(
            request_id="authored-v21-clarification",
            mode="interactive_chat",
            condition="E1",
            question=question,
            prepared_query=prepared,
            understanding=understanding,
            enhancement_version=enhancement,
        )
    )
    assert outcome.error is None
    assert outcome.response["response_type"] == "clarification"
    assert outcome.response["citations"] == []
    assert outcome.budget["consumed_calls"] == 0
    generator.generate.assert_not_called()
    checker.generate.assert_not_called()


def test_v21_practice_dispatch_keeps_public_conditions_and_private_rubric_out():
    module = _private_module("conversation/practice_context.py", "conversation.private_practice")
    text = "Help me with the current practice step without giving the answer."
    teaching = {
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "owned-v21-step",
            "progress_version": 1,
            "current_step": 1,
            "prompt": "Describe the energy source used by photosynthetic organisms.",
            "current_step_prompt": "Identify the energy input under the stated conditions.",
            "conditions": ["Assume 25 C and no artificial illumination."],
            "concepts": ["photosynthesis"],
            "source": {"source_unit_id": "owned-source"},
            "private_rubric": {"answer_key": "PRIVATE_V21_GRADING_CANARY"},
        },
        "turn_role": "user_question",
    }
    prepared, understanding = module.resolve(
        text,
        query_v21.prepare_query(text).model_dump(),
        teaching,
        policy=module.VERSION,
        preparation_version=query_v21.VERSION,
    )
    assert prepared["preparation_version"] == query_v21.VERSION
    assert understanding["version"] == "question_requirements_v7"
    assert "25 C and no artificial illumination" in prepared["standalone_query"]
    assert "PRIVATE_V21_GRADING_CANARY" not in repr((prepared, understanding))
    source = understanding["requirement_source_text"]
    for point in understanding["required_knowledge"]:
        span = point["request_span"]
        assert source[span["start"] : span["end"]] == point["verbatim_request"]
