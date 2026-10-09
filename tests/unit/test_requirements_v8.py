"""Bounded V8 preference controls against frozen V21/V7 producers.

Authored passages establish lexical controls only. No provider, database or
semantic support claim is involved.
"""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

from conversation import query_v21, query_v22, requirements_v8 as v8

from generation import adapters
from generation.coverage_v4 import assess_evidence_coverage


QUESTION = (
    "I prefer examples for photosynthesis. Explain how sunlight supplies energy "
    "for photosynthesis in the selected passage."
)


@pytest.fixture(autouse=True)
def no_provider_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Candidate requirement controls forbid provider transport")

    monkeypatch.setattr(adapters, "open_provider", forbidden)
    monkeypatch.setattr(adapters.LLMAdapter, "_call", forbidden)


def extract(question, *, module=query_v21, reader=False, literal_query=False):
    prepared = module.prepare_query(question).model_dump()
    if literal_query:
        # Explicit authored immutable source fixture, not a claim that native
        # preparation preserves unexpanded acronym declarations.
        prepared["standalone_query"] = question
    if reader:
        prepared.update(
            standalone_query=question + "\nTextbook section: Photosynthesis",
            needs_clarification=False,
            intent="factual",
            topic_relation="new_topic",
            fallback_reason="verified_reading_selection",
        )
    return prepared, module.describe_requirements(question, prepared)


def transformed(question, **kwargs):
    prepared, baseline = extract(question, **kwargs)
    before = deepcopy(baseline)
    result = v8.separate_leading_example_preference(baseline)
    assert baseline == before
    return prepared, baseline, result


def assert_strict(baseline):
    before = deepcopy(baseline)
    result = v8.separate_leading_example_preference(baseline)
    assert baseline == before
    assert result == {**before, "version": v8.VERSION}
    assert "preference_separation" not in result


def test_exact_reader_preference_moves_with_sparse_science_id_and_literal_span():
    _, baseline, result = transformed(QUESTION, reader=True)
    assert baseline["version"] == "question_requirements_v7"
    assert len(baseline["required_knowledge"]) == 2
    assert baseline["presentation_requests"] == []
    assert result["version"] == "question_requirements_v8"
    assert [point["id"] for point in result["required_knowledge"]] == ["requirement_02"]
    assert result["required_knowledge"][0] == {
        **baseline["required_knowledge"][1],
        "presentation_request_ids": ["presentation_01"],
    }
    assert result["requested_facets"] == result["required_knowledge"]
    assert result["semantic_intents"] == ["explanation"]
    presentation = result["presentation_requests"][0]
    assert presentation["request"] == "I prefer examples for photosynthesis"
    assert presentation["kind"] == "response_style"
    assert presentation["style"] == "examples"
    assert presentation["topic"] == "photosynthesis"
    assert presentation["original_requirement_id"] == "requirement_01"
    assert presentation["applies_to_requirement_ids"] == ["requirement_02"]
    assert presentation["request_span"] == {
        "coordinate_space": "requirement_source_text",
        "start": 0,
        "end": 36,
    }
    span = presentation["request_span"]
    assert result["requirement_source_text"][span["start"] : span["end"]] == presentation["request"]
    for key in (
        "original_message",
        "standalone_query",
        "requirement_source_text",
        "original_question_hash",
        "preserved_constraints",
        "constraints",
        "reader_reference_resolution",
        "intent",
        "topic_relation",
        "preparation_dependency",
        "requirement_structure",
    ):
        assert result[key] == baseline[key]
    assert result["preference_separation"]["semantic_applicability"] is None
    assert result["preference_separation"]["semantic_sufficiency"] is None
    assert result["preference_separation"]["human_rating"] is None


def test_light_lexical_coverage_loses_only_spurious_prefer_gap():
    question = QUESTION.replace("sunlight", "light")
    _, baseline, result = transformed(question, reader=True)
    evidence = [
        {
            "evidence_id": "ev_authored",
            "chunk_id": "authored_light",
            "text": "Light supplies energy for photosynthesis.",
        }
    ]
    old = assess_evidence_coverage(question, evidence, baseline)
    new = assess_evidence_coverage(question, evidence, result)
    assert old["candidate_coverage"]["missing_requirement_ids"] == ["requirement_01"]
    assert old["locatable_missing"][0]["missing_term_groups"] == [["prefer"]]
    assert new["candidate_coverage"]["missing_requirement_ids"] == []
    assert new["context_sufficiency_estimate"] == "lexically_complete"
    assert new["semantic_sufficiency"] is None


def test_same_original_mock_refusal_remains_for_unchanged_match_query():
    prepared, baseline, result = transformed(QUESTION, reader=True)
    evidence = [
        {
            "evidence_id": "ev_authored",
            "chunk_id": "authored_light",
            "text": "Light supplies energy for photosynthesis.",
        }
    ]
    context = {
        "question": QUESTION,
        "prepared_query": prepared,
        "mode": "interactive_chat",
        "condition": "E1",
        "evidence": evidence,
    }
    old = adapters.mock_payload({**context, "understanding": baseline})
    new = adapters.mock_payload({**context, "understanding": result})
    assert new == old
    assert new["response_type"] == "refusal"
    assert new["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
    assert new["citations"] == []


@pytest.mark.parametrize(
    "topic",
    [
        "photosynthesis",
        "osmosis",
        "diffusion",
        "cellular respiration",
        "calvin cycle",
        "mitosis",
        "meiosis",
        "ideal gas law",
        "activation energy",
    ],
)
def test_known_literal_topics_bind_the_following_explicit_owner(topic):
    question = f"I prefer examples for {topic}. Explain {topic}."
    _, baseline, result = transformed(question)
    assert len(result["required_knowledge"]) == 1
    assert result["presentation_requests"][0]["topic"] == topic
    assert result["presentation_requests"][0]["applies_to_requirement_ids"] == [
        baseline["required_knowledge"][1]["id"]
    ]


@pytest.mark.parametrize("topic", ["DNA", "RNA", "ATP", "PCR"])
def test_authored_literal_acronym_catalogue_does_not_claim_native_expansion_support(topic):
    question = f"I prefer examples for {topic}. Explain {topic}."
    _, _, literal = transformed(question, literal_query=True)
    assert literal["presentation_requests"][0]["topic"] == topic.casefold()
    _, native = extract(question)
    assert native["required_knowledge"][0]["request"] != f"I prefer examples for {topic}"
    assert_strict(native)


@pytest.mark.parametrize("space", [" ", "\t", "\r\n", "  \t"])
def test_case_whitespace_and_raw_coordinate_round_trip(space):
    question = " \tI PREFER examples for Photosynthesis." + space + "Explain Photosynthesis.  "
    _, baseline, result = transformed(question)
    assert len(result["presentation_requests"]) == 1
    for row in result["required_knowledge"] + result["presentation_requests"]:
        span = row["request_span"]
        expected = row.get("verbatim_request", row["request"])
        assert result["requirement_source_text"][span["start"] : span["end"]] == expected
    assert result["original_message"] == baseline["original_message"] == question


def test_global_constraints_survive_when_the_science_owner_is_qualified():
    question = (
        "I prefer examples for photosynthesis. Explain photosynthesis without oxygen "
        "at 280 K in the selected passage."
    )
    _, baseline, result = transformed(question, reader=True)
    assert baseline["required_knowledge"][0]["conditions"]
    assert len(result["presentation_requests"]) == 1
    assert result["preserved_constraints"] == baseline["preserved_constraints"]
    assert (
        result["required_knowledge"][0]["conditions"]
        == baseline["required_knowledge"][1]["conditions"]
    )
    assert result["preserved_constraints"]["negation"][0]["text"] == "without"
    assert result["preserved_constraints"]["quantities_and_units"][0]["text"] == "280 K"
    report = assess_evidence_coverage(
        question,
        [
            {
                "evidence_id": "ev_authored",
                "chunk_id": "bare_definition",
                "text": "Photosynthesis uses light.",
            }
        ],
        result,
    )
    assert report["candidate_coverage"]["missing_requirement_ids"] == ["requirement_02"]
    missing = {
        term for group in report["locatable_missing"][0]["missing_term_groups"] for term in group
    }
    assert {"without", "oxygen", "280", "k"} <= missing


def test_genuine_conjunction_and_different_topic_remain_independent_science():
    question = (
        "I prefer examples for photosynthesis. Explain how light supplies energy for photosynthesis "
        "and describe how photosynthesis stores energy. Explain osmosis."
    )
    _, baseline, result = transformed(question)
    assert [point["id"] for point in result["required_knowledge"]] == [
        "requirement_02",
        "requirement_03",
        "requirement_04",
    ]
    assert result["presentation_requests"][0]["applies_to_requirement_ids"] == [
        "requirement_02",
        "requirement_03",
    ]
    for old, new in zip(baseline["required_knowledge"][1:], result["required_knowledge"]):
        assert {key: value for key, value in new.items() if key != "presentation_request_ids"} == {
            key: value for key, value in old.items() if key != "presentation_request_ids"
        }
    assert result["required_knowledge"][-1]["presentation_request_ids"] == []
    report = assess_evidence_coverage(
        question,
        [
            {
                "evidence_id": "ev_authored",
                "chunk_id": "first_science_only",
                "text": "Light supplies energy for photosynthesis.",
            }
        ],
        result,
    )
    assert report["candidate_coverage"]["missing_requirement_ids"] == [
        "requirement_03",
        "requirement_04",
    ]


def test_existing_presentation_links_and_id_collision_are_preserved():
    _, baseline = extract("I prefer examples for photosynthesis. Explain photosynthesis.")
    baseline["presentation_requests"] = [
        {
            "id": "presentation_01",
            "request": "Existing style",
            "kind": "response_style",
            "applies_to_requirement_ids": ["requirement_02"],
        },
        {
            "id": "presentation_03",
            "request": "Existing hint",
            "kind": "help_depth",
            "applies_to_requirement_ids": ["requirement_02"],
        },
    ]
    baseline["required_knowledge"][1]["presentation_request_ids"] = [
        "presentation_01",
        "presentation_03",
    ]
    baseline["requested_facets"] = deepcopy(baseline["required_knowledge"])
    before = deepcopy(baseline)
    result = v8.separate_leading_example_preference(baseline)
    assert baseline == before
    assert result["presentation_requests"][:2] == before["presentation_requests"]
    assert result["presentation_requests"][-1]["id"] == "presentation_04"
    assert result["required_knowledge"][0]["presentation_request_ids"] == [
        "presentation_01",
        "presentation_03",
        "presentation_04",
    ]


def test_trailing_hint_composition_keeps_hint_metadata_and_only_retained_owners():
    question = (
        "I prefer examples for photosynthesis. Explain photosynthesis. Please give me one hint."
    )
    _, baseline, result = transformed(question)
    old_hint = baseline["presentation_requests"][0]
    assert old_hint["kind"] == "help_depth"
    assert old_hint["applies_to_requirement_ids"] == ["requirement_01", "requirement_02"]
    assert result["presentation_requests"][0] == {
        **old_hint,
        "applies_to_requirement_ids": ["requirement_02"],
    }
    assert result["presentation_requests"][1]["kind"] == "response_style"
    assert result["presentation_requests"][1]["id"] == "presentation_02"
    assert result["required_knowledge"][0]["id"] == "requirement_02"
    assert result["required_knowledge"][0]["presentation_request_ids"] == [
        "presentation_01",
        "presentation_02",
    ]
    assert result["embedded_help_depth_separation"] == baseline["embedded_help_depth_separation"]
    retained_ids = {point["id"] for point in result["required_knowledge"]}
    assert all(
        set(row["applies_to_requirement_ids"]) <= retained_ids
        for row in result["presentation_requests"]
    )


def test_existing_presentation_with_only_preference_owner_prevents_separation():
    _, baseline = extract("I prefer examples for photosynthesis. Explain photosynthesis.")
    baseline["presentation_requests"] = [
        {
            "id": "presentation_01",
            "request": "Existing unsupported binding",
            "kind": "response_style",
            "applies_to_requirement_ids": ["requirement_01"],
        }
    ]
    baseline["required_knowledge"][0]["presentation_request_ids"] = ["presentation_01"]
    assert_strict(baseline)


@pytest.mark.parametrize(
    "question",
    [
        "I prefer examples for photosynthesis.",
        "I prefer examples for botany. Explain botany.",
        "I prefer examples for photosynthesis and osmosis. Explain photosynthesis.",
        "I prefer examples for photosynthesis except at night. Explain photosynthesis.",
        "I prefer examples for photosynthesis if sunlight is available. Explain photosynthesis.",
        "I do not prefer examples for photosynthesis. Explain photosynthesis.",
        "I no longer prefer examples for photosynthesis. Explain photosynthesis.",
        "My teacher says I prefer examples for photosynthesis. Explain photosynthesis.",
        'I prefer examples for "photosynthesis". Explain photosynthesis.',
        "I prefer examples for photosynthesis. Explain osmosis.",
        "I prefer examples for photosynthesis. Only at night. Explain photosynthesis.",
        "I prefer examples for photosynthesis and explain why photosynthesis requires light.",
        "Explain photosynthesis. I prefer examples for photosynthesis.",
        "I prefer examples for photosynthesis. I prefer examples for photosynthesis. Explain photosynthesis.",
        "I prefer examples for photosynthesis. In plain language, explain photosynthesis.",
        "I prefer examples for photosynthesis. Explain this paragraph.",
        "Sunlight powers photosynthesis. Explain photosynthesis.",
        "Give examples for photosynthesis and explain photosynthesis.",
        "I prefer examples for photosynthesis? Explain photosynthesis.",
        "I prefer examples for photosynthesis! Explain photosynthesis.",
        "I prefer examples for photosynthesis; Explain photosynthesis.",
    ],
)
def test_unknown_mixed_conditional_unowned_and_non_declarative_forms_stay_strict(question):
    _, baseline = extract(question)
    assert_strict(baseline)


@pytest.mark.parametrize(
    "mutation",
    [
        "span_start_bool",
        "span_end_bool",
        "negative_start",
        "past_source_end",
        "foreign_coordinates",
        "changed_literal",
        "changed_request",
        "unknown_origin",
        "missing_id",
        "empty_id",
        "integer_id",
        "duplicate_id",
        "clarification",
        "source_bound",
        "style_transform",
        "drifted_facets",
        "invalid_owner_span",
        "missing_presentation_list",
        "source_is_not_text",
        "non_dict_preference",
        "non_dict_owner",
        "non_dict_span",
        "span_is_none",
        "string_start",
        "float_end",
        "foreign_id",
        "whitespace_id",
        "out_of_range_id",
    ],
)
def test_invalid_frozen_identity_coordinates_or_dependencies_never_move(mutation):
    _, baseline = extract("I prefer examples for photosynthesis. Explain photosynthesis.")
    point = baseline["required_knowledge"][0]
    if mutation == "span_start_bool":
        point["request_span"]["start"] = False
    elif mutation == "span_end_bool":
        point["request_span"]["end"] = True
    elif mutation == "negative_start":
        point["request_span"]["start"] = -1
    elif mutation == "past_source_end":
        point["request_span"]["end"] = len(baseline["requirement_source_text"]) + 1
    elif mutation == "foreign_coordinates":
        point["request_span"]["coordinate_space"] = "original_message"
    elif mutation == "changed_literal":
        point["verbatim_request"] += " altered"
    elif mutation == "changed_request":
        point["request"] += " altered"
    elif mutation == "unknown_origin":
        point["origin"] = "unverified_fixture"
    elif mutation == "missing_id":
        point.pop("id")
    elif mutation == "empty_id":
        point["id"] = ""
    elif mutation == "integer_id":
        point["id"] = 1
    elif mutation == "duplicate_id":
        baseline["required_knowledge"][1]["id"] = point["id"]
    elif mutation == "clarification":
        baseline["needs_clarification"] = True
    elif mutation == "source_bound":
        baseline["reader_reference_resolution"] = {"status": "source_bound"}
    elif mutation == "style_transform":
        baseline["required_knowledge"][1]["request"] = "photosynthesis"
    elif mutation == "drifted_facets":
        baseline["requested_facets"] = []
    elif mutation == "invalid_owner_span":
        baseline["required_knowledge"][1]["request_span"]["start"] += 1
    elif mutation == "missing_presentation_list":
        baseline["presentation_requests"] = None
    elif mutation == "source_is_not_text":
        baseline["requirement_source_text"] = None
    elif mutation == "non_dict_preference":
        baseline["required_knowledge"][0] = "not a requirement object"
    elif mutation == "non_dict_owner":
        baseline["required_knowledge"][1] = None
    elif mutation == "non_dict_span":
        point["request_span"] = [0, 36]
    elif mutation == "span_is_none":
        point["request_span"] = None
    elif mutation == "string_start":
        point["request_span"]["start"] = "0"
    elif mutation == "float_end":
        point["request_span"]["end"] = 36.0
    elif mutation == "foreign_id":
        point["id"] = "foreign_requirement"
    elif mutation == "whitespace_id":
        point["id"] = " "
    elif mutation == "out_of_range_id":
        point["id"] = "requirement_09"
    assert_strict(baseline)


@pytest.mark.parametrize(
    "question",
    [
        QUESTION,
        "Explain it more simply.",
        "What is photosynthesis?",
        "I prefer examples for photosynthesis. Explain photosynthesis without oxygen at 280 K.",
        "Compare diffusion and osmosis. Please give me one hint.",
    ],
)
def test_v22_preparation_keeps_every_frozen_v21_field(question):
    history = [{"role": "user", "content": "Explain osmosis.", "message_id": "u1"}]
    before = deepcopy(history)
    old = query_v21.prepare_query(question, history).model_dump()
    new = query_v22.prepare_query(question, history).model_dump()
    assert new == {**old, "preparation_version": query_v22.VERSION}
    assert history == before


def test_v22_json_transport_cross_dispatch_and_v21_inventory_stay_frozen():
    prepared, old = extract(QUESTION, reader=True)
    old_before = deepcopy(old)
    candidate_prepared = {**prepared, "preparation_version": query_v22.VERSION}
    candidate_before = deepcopy(candidate_prepared)
    result = query_v22.describe_requirements(QUESTION, json.loads(json.dumps(candidate_prepared)))
    assert candidate_prepared == candidate_before
    assert result["preparation_dependency"]["frozen_preparation_version"] == query_v22.VERSION
    assert result["preparation_dependency"]["requirements_version"] == v8.VERSION
    assert [point["id"] for point in result["required_knowledge"]] == ["requirement_02"]
    assert json.loads(json.dumps(result)) == result
    assert query_v21.describe_requirements(QUESTION, prepared) == old_before
    assert len(old_before["required_knowledge"]) == 2
    assert old_before["presentation_requests"] == []
    with pytest.raises(ValueError, match="frozen query preparation version"):
        query_v22.prepare_query(QUESTION, version=query_v21.VERSION)
    with pytest.raises(ValueError, match="frozen query preparation dependency"):
        query_v22.describe_requirements(QUESTION, prepared)
    with pytest.raises(ValueError, match="frozen query preparation dependency"):
        query_v21.describe_requirements(QUESTION, candidate_prepared)
    with pytest.raises(ValueError, match="frozen requirement producer"):
        v8.separate_leading_example_preference(
            {**old_before, "version": "question_requirements_v6"}
        )
