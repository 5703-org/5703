"""Exact help clauses separate; scientific requests and old producers retain."""

from copy import deepcopy

import pytest

from conversation import query_v19, query_v20
from conversation.requirements_v6 import separate_help_depth
from generation.unit_definition_plan_v1 import plan
from retrieval.complementary_spans import _explicit_axis_terms, select_context

QUESTION = (
    "A breeding male stickleback attacks a red-bottomed object that does not resemble "
    "a fish. What does this illustrate about a fixed action pattern, its triggering "
    "stimulus and completion after the stimulus is removed?"
)


def requirements(text, module=query_v20):
    prepared = module.prepare_query(text).model_dump()
    return module.describe_requirements(text, prepared)


@pytest.mark.parametrize(
    "clause", ["Please give me one hint for this step", "Give me a hint", "give me one hint"]
)
def test_exact_help_depth_separates_with_original_coordinates(clause):
    text = QUESTION + " " + clause + "."
    old = requirements(text, query_v19)
    new = requirements(text)
    moved = old["required_knowledge"][-1]
    assert new["version"] == "question_requirements_v6"
    assert new["required_knowledge"] == old["required_knowledge"][:-1]
    assert new["requested_facets"] == old["requested_facets"][:-1]
    assert new["requirement_source_text"] == old["requirement_source_text"] == text
    assert new["preserved_constraints"] == old["preserved_constraints"]
    presentation = new["presentation_requests"][-1]
    assert presentation["kind"] == "help_depth"
    assert presentation["original_requirement_id"] == moved["id"]
    assert presentation["request_span"] == moved["request_span"]
    span = presentation["request_span"]
    assert text[span["start"] : span["end"]] == presentation["request"] == clause
    assert presentation["applies_to_requirement_ids"] == [
        point["id"] for point in new["required_knowledge"]
    ]
    assert new.get("current_message_resolution") == old.get("current_message_resolution")
    assert new["preparation_dependency"]["frozen_preparation_version"] == query_v20.VERSION
    assert new["preparation_dependency"]["requirements_version"] == "question_requirements_v6"


@pytest.mark.parametrize(
    "clause",
    [
        "Do not give me one hint for this step",
        "Give me one hint about the triggering stimulus",
        "Give me one hint for this step and explain why the pattern continues",
        "Give me one hint for this step if the stimulus is removed",
        "Give me one hint for this step without losing the temperature condition",
        "Give me two hints for this step",
        "Give me one hint for that earlier step",
    ],
)
def test_negative_mixed_conditional_and_unknown_clauses_keep_all_points(clause):
    text = QUESTION + " " + clause + "."
    old = requirements(text, query_v19)
    new = requirements(text)
    assert new["required_knowledge"] == old["required_knowledge"]
    assert new["presentation_requests"] == old["presentation_requests"]
    assert "help_depth_separation" not in new


def test_help_only_without_factual_request_is_retained():
    old = requirements("Give me one hint.", query_v19)
    new = requirements("Give me one hint.")
    assert new["required_knowledge"] == old["required_knowledge"]
    assert "help_depth_separation" not in new


def test_hint_first_keeps_nonconsecutive_scientific_ids():
    text = "Give me one hint. Explain completion after the stimulus is removed."
    old = requirements(text, query_v19)
    new = requirements(text)
    assert new["required_knowledge"] == old["required_knowledge"][1:]
    assert new["required_knowledge"][0]["id"] == "requirement_02"


def test_invalid_coordinate_cannot_drop_a_requirement_or_mutate_baseline():
    old = requirements(QUESTION + " Please give me one hint for this step.", query_v19)
    old["required_knowledge"][-1]["request_span"]["end"] -= 1
    before = deepcopy(old)
    new = separate_help_depth(old)
    assert old == before
    assert new["required_knowledge"] == old["required_knowledge"]
    assert "help_depth_separation" not in new


@pytest.mark.parametrize(
    "text", [QUESTION, "What does this illustrate about a fixed action pattern?", "Give me a hint."]
)
def test_query_behavior_is_exact_v19_except_version(text):
    old = query_v19.prepare_query(text).model_dump()
    new = query_v20.prepare_query(text).model_dump()
    new["preparation_version"] = old["preparation_version"]
    assert new == old


def test_frozen_versions_reject_cross_dispatch():
    with pytest.raises(ValueError):
        query_v20.prepare_query(QUESTION, version=query_v19.VERSION)
    with pytest.raises(ValueError):
        query_v20.describe_requirements(QUESTION, query_v19.prepare_query(QUESTION).model_dump())


def test_v6_keeps_owned_sugar_axis_and_exact_source_coordinates():
    current = "Explain the sugar difference in simpler language."
    prior = "Compare DNA and RNA in their sugars, nitrogenous bases and usual strand structure. Explain each difference separately."
    history = [
        {"role": "user", "content": prior, "message_id": "owned-user"},
        {
            "role": "assistant",
            "content": "Authored refusal.",
            "message_id": "owned-assistant",
            "answer_id": "owned-answer",
            "answer_response_type": "refusal",
            "latest_exchange_available": True,
        },
    ]
    old = query_v19.describe_requirements(
        current, query_v19.prepare_query(current, history).model_dump(), history
    )
    new = query_v20.describe_requirements(
        current, query_v20.prepare_query(current, history).model_dump(), history
    )
    assert new["required_knowledge"] == old["required_knowledge"]
    assert new["comparison_axis_resolution"] == old["comparison_axis_resolution"]
    (point,) = new["required_knowledge"]
    assert point["objects"] == ["DNA", "RNA"] and point["requested_axes"] == ["sugars"]
    span = point["request_span"]
    assert current[span["start"] : span["end"]] == point["verbatim_request"]
    assert _explicit_axis_terms(new) == _explicit_axis_terms(old)
    assert _explicit_axis_terms(new)
    sentences = [
        "DNA and RNA have different sugars.",
        *[f"Neutral block {i}." for i in range(8)],
        "DNA and RNA share a structure discussion.",
    ]
    text = "\n".join(sentences)
    blocks, cursor = [], 0
    for index, sentence in enumerate(sentences):
        blocks.append(
            {
                "evidence_id": "ev_001",
                "fragment_id": f"f{index}",
                "complete_block": True,
                "chunk_start": cursor,
                "chunk_end": cursor + len(sentence),
                "exact_text": sentence,
            }
        )
        cursor += len(sentence) + 1
    evidence = [{"evidence_id": "ev_001", "chunk_id": "authored", "text": text}]
    selected, ranges, _, trace = select_context(evidence, blocks, current, new)
    assert sentences[0] in selected[0]["text"]
    assert "f0" in trace["decisions"][0]["axis_anchor_fragment_ids"]
    assert (
        selected[0]["text"]
        == text[ranges["authored"]["submitted_start"] : ranges["authored"]["submitted_end"]]
    )
    assert len(selected[0]["text"]) <= len(text)
    tampered = deepcopy(new)
    tampered["required_knowledge"][0]["request_span"]["end"] -= 1
    assert not _explicit_axis_terms(tampered)


def test_v6_unit_lookup_retains_v5_query_alias_and_budget_boundary():
    text = "Which pressure units are consistent with Pa?"
    old = requirements(text, query_v19)
    new = requirements(text)
    report = {"locatable_missing": [{"id": point["id"]} for point in old["required_knowledge"]]}
    old_plan, new_plan = plan(text, report, old), plan(text, report, new)
    assert old_plan == new_plan
    assert new_plan["status"] != "unsupported_requirement_producer"
    unknown = {**new, "version": "question_requirements_v999"}
    assert plan(text, report, unknown)["status"] == "unsupported_requirement_producer"


def test_sparse_factual_ids_roundtrip_strict_checker_without_renumbering():
    from generation.reliability_v5 import assess_requirements

    text = "Give me one hint. Explain completion after the stimulus is removed."
    data = requirements(text)
    ids = [point["id"] for point in data["required_knowledge"]]
    assert ids == ["requirement_02"]
    rows = [
        {
            "requirement_id": identity,
            "relevance": "unrelated",
            "sufficiency": "absent",
            "evidence": [],
            "conditions_preserved": True,
            "response_coverage": "deferred_for_hint",
            "missing_information": "Authored missing source passage.",
            "reason": "Authored contract fixture, not a semantic label.",
        }
        for identity in ids
    ]
    judgment = {
        "requirements": rows,
        "limitations_explicit": True,
        "non_repetitive_next_action": True,
    }
    coverage = {"requirements": [{"id": identity} for identity in ids]}
    contract, defects, result = assess_requirements(
        judgment, coverage, [], answer_mode="textbook", teaching_mode="hint"
    )
    assert contract == defects == []
    assert result["requirements"] == rows
    wrong = deepcopy(judgment)
    wrong["requirements"][0]["requirement_id"] = "requirement_01"
    contract, _, _ = assess_requirements(
        wrong, coverage, [], answer_mode="textbook", teaching_mode="hint"
    )
    assert {issue["code"] for issue in contract} == {"REQUIREMENT_IDENTITY_MISMATCH"}
