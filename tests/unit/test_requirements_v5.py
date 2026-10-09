"""Authored syntax regressions retain real scientific obligations."""

import pytest

from conversation import query_v16, query_v17
from conversation.requirements_v5 import describe_requirements
from generation.coverage_v3 import assess_evidence_coverage


def extract(question):
    return query_v17.describe_requirements(question, query_v17.prepare_query(question).model_dump())


def test_attached_presentation_does_not_become_a_second_textbook_fact():
    question = "Compare mitosis and meiosis in their chromosome counts and daughter cells. Explain each difference separately."
    old = query_v16.describe_requirements(question, query_v16.prepare_query(question).model_dump())
    new = extract(question)
    assert len(old["required_knowledge"]) == 2
    assert len(new["required_knowledge"]) == 1
    point = new["required_knowledge"][0]
    assert point["objects"] == ["mitosis", "meiosis"]
    assert point["requested_axes"] == ["chromosome counts", "daughter cells"]
    assert "chromosome" in point["terms"] and "separately" not in point["terms"]
    presentation = new["presentation_requests"][0]
    assert presentation["request"] == "Explain each difference separately"
    assert presentation["applies_to_requirement_ids"] == [point["id"]]
    assert point["presentation_request_ids"] == ["presentation_01"]
    assert new["original_message"] == question
    coverage = assess_evidence_coverage(question, [], new)
    assert len(coverage["locatable_missing"]) == 1
    assert "separately" not in coverage["locatable_missing"][0]["request"]
    assert coverage["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "tail",
    [
        "Explain why each difference matters.",
        "Explain each difference separately without assuming ideal conditions.",
        "Explain each difference separately at 5.0 atm.",
        "Explain each difference in chromosome count separately.",
        "Explain each difference separately and explain its effect on the rate.",
    ],
)
def test_scientific_actions_qualifiers_and_conditions_are_not_removed(tail):
    question = "Compare diffusion and active transport. " + tail
    result = extract(question)
    requests = " ".join(point["request"] for point in result["required_knowledge"])
    if "and explain" in tail:
        assert "explain its effect on the rate" in requests
    else:
        assert tail.rstrip(".") in requests
    assert result["original_message"] == question


@pytest.mark.parametrize(
    "question",
    [
        "Explain each difference separately.",
        "What is osmosis? Explain each difference separately.",
        "Compare these processes. Explain each difference separately.",
    ],
)
def test_presentation_needs_a_resolved_comparison_owner(question):
    result = extract(question)
    assert result["presentation_requests"] == []
    assert any("each difference separately" in p["request"] for p in result["required_knowledge"])


@pytest.mark.parametrize(
    ("question", "count", "last"),
    [
        (
            "Why does osmosis occur and which conditions change its direction?",
            2,
            "which conditions change its direction",
        ),
        (
            "Why does osmosis occur and which membrane is permeable?",
            2,
            "which membrane is permeable",
        ),
        (
            "What is diffusion and when does its net rate reach zero?",
            2,
            "when does its net rate reach zero",
        ),
        (
            "What is a nucleic acid and where is RNA synthesized?",
            2,
            "where is ribonucleic acid (RNA) synthesized",
        ),
        ("Compare acids and bases.", 1, "Compare acids and bases"),
        (
            "Explain the sugar and phosphate backbone of DNA.",
            1,
            "Explain the sugar and phosphate backbone of deoxyribonucleic acid (DNA)",
        ),
        (
            "Explain an enzyme when heated and when cooled.",
            1,
            "Explain an enzyme when heated and when cooled",
        ),
    ],
)
def test_only_independent_question_actions_split(question, count, last):
    result = extract(question)
    assert len(result["required_knowledge"]) == count
    assert result["required_knowledge"][-1]["request"] == last
    assert result["original_message"] == question


def test_relative_which_clause_is_not_an_independent_question():
    question = "Explain enzymes which bind substrate and which change shape."
    result = extract(question)
    assert len(result["required_knowledge"]) == 1
    assert result["required_knowledge"][0]["request"] == question[:-1]
    assert result["original_message"] == question


def test_original_gas_question_keeps_two_obligations_and_complete_units():
    question = "In the ideal gas law PV = nRT, why must temperature be expressed in kelvin, and which pressure and volume units are consistent with R = 8.314 J mol-1 K-1?"
    result = extract(question)
    assert len(result["required_knowledge"]) == 2
    assert "why must temperature" in result["required_knowledge"][0]["request"]
    assert result["required_knowledge"][1]["request"].startswith("which pressure and volume units")
    assert result["preserved_constraints"]["quantities_and_units"] == [
        {
            "text": "8.314 J mol-1 K-1",
            "start": question.index("8.314"),
            "end": len(question) - 1,
        }
    ]
    assert result["requirement_structure"]["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "unit",
    [
        "J mol\u22121 K\u22121",
        "J mol\u20131 K\u20131",
        "J mol^-1 K^-1",
        "J mol\u207b\u00b9 K\u207b\u00b9",
        "Pa m^3",
        "kPa L",
    ],
)
def test_unit_exponents_remain_inside_exact_quantity_spans(unit):
    question = "Explain why R = 8.314 " + unit + " is not compatible with every unit choice."
    result = extract(question)
    row = result["preserved_constraints"]["quantities_and_units"][0]
    assert row["text"] == "8.314 " + unit
    assert question[row["start"] : row["end"]] == row["text"]
    assert any(row["text"] in p["conditions"] for p in result["required_knowledge"])
    assert result["preserved_constraints"]["negation"][0]["text"] == "not"


def test_decimal_negative_condition_and_unknown_unit_survive():
    question = "At -3.5 \u00b0C, why does this not follow the rule and which value is valid at 0.5 customunit?"
    result = extract(question)
    spans = result["preserved_constraints"]["quantities_and_units"]
    assert [row["text"] for row in spans] == ["-3.5 \u00b0C", "0.5 customunit"]
    assert all(question[row["start"] : row["end"]] == row["text"] for row in spans)
    assert result["preserved_constraints"]["negation"][0]["text"] == "not"
    assert result["original_message"] == question


def test_style_prefix_keeps_science_and_exact_request_coordinates():
    question = "In plain language, explain why salt changes the boiling point."
    result = extract(question)
    point = result["required_knowledge"][0]
    assert point["request"] == "explain why salt changes the boiling point"
    assert "salt" in point["terms"]
    assert result["presentation_requests"][0]["request"] == "In plain language"
    presentation = result["presentation_requests"][0]
    presentation_span = presentation["request_span"]
    assert (
        result["requirement_source_text"][presentation_span["start"] : presentation_span["end"]]
        == presentation["request"]
    )
    span = point["request_span"]
    assert span["coordinate_space"] == "requirement_source_text"
    assert (
        result["requirement_source_text"][span["start"] : span["end"]] == point["verbatim_request"]
    )
    assert result["original_message"] == question


def test_selected_source_contract_keeps_exact_frozen_reading_reference():
    question = "Explain this paragraph."
    prepared = query_v17.prepare_query(question).model_dump()
    prepared.update(
        standalone_query=question + "\nTextbook section: 5.1 Photosynthesis",
        fallback_reason="verified_reading_selection",
    )
    result = query_v17.describe_requirements(question, prepared)
    assert result["reader_reference_resolution"]["status"] == "source_bound"
    assert result["required_knowledge"][0]["terms"] == []
    assert result["required_knowledge"][0]["origin"] == "verified_selected_source_referent_v1"
    assert result["presentation_requests"] == []
    assert "Textbook section" not in result["required_knowledge"][0]["request"]


def test_standalone_producer_never_mutates_the_frozen_baseline():
    question = "Compare salts and acids. Explain each difference separately."
    prepared = query_v16.prepare_query(question).model_dump()
    old = query_v16.describe_requirements(question, prepared)
    new = describe_requirements(question, prepared, baseline=old)
    assert len(new["required_knowledge"]) == 1
    assert len(old["required_knowledge"]) == 2
    assert old["version"] == "question_requirements_v4"


def test_overflow_keeps_every_request_in_the_bounded_last_requirement():
    question = "? ".join("Explain concept " + str(index) for index in range(12)) + "?"
    result = extract(question)
    assert len(result["required_knowledge"]) == 8
    overflow = result["required_knowledge"][-1]
    assert len(overflow["retained_subrequests"]) == 5
    assert "Explain concept 11" in overflow["request"]
    span = overflow["request_span"]
    assert (
        result["requirement_source_text"][span["start"] : span["end"]]
        == overflow["verbatim_request"]
    )
    assert "? " in overflow["verbatim_request"]
    for subrequest in overflow["retained_subrequests"]:
        subspan = subrequest["request_span"]
        assert (
            result["requirement_source_text"][subspan["start"] : subspan["end"]]
            == subrequest["verbatim_request"]
        )
    assert result["original_message"] == question
