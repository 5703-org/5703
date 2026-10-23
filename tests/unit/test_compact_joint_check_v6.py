"""Authored contract probes and real offline token counts, not semantic ratings."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import ReliableCheckV5
from generation.reliability_v6 import (
    CompactJointCheckV6,
    compact_check_context,
    expand_compact_judgment,
)
from generation.reliability_v3 import validate_derivation
from generation.source_relations_v2 import syntactic_units
from generation.token_counting import TokenCounter
from generation.types import ModelConfig


def fixture():
    text = "Under condition A, X does not increase and Y remains at −2.5 °C [ev_001]."
    data = {
        "question": "Compare X and Y under condition A.",
        "current_problem": "Compare X and Y under condition A.",
        "CLAIMS": [{"claim_id": "c1", "text": text, "answer_field": "answer_text"}],
        "ACTUAL_CITATION_BINDINGS": [
            {
                "claim_id": "c1",
                "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F001", "F002"]}],
            }
        ],
        "SOURCE_FRAGMENTS": [
            {
                "fragment_id": "F001",
                "evidence_id": "ev_001",
                "exact_text": text,
                "complete_block": True,
                "block_kind": "paragraph",
            },
            {
                "fragment_id": "F002",
                "evidence_id": "ev_001",
                "exact_text": "Other content.",
                "complete_block": True,
                "block_kind": "paragraph",
            },
        ],
        "CONTEXT_COVERAGE": {"requirements": [{"id": "r1"}]},
    }
    context = compact_check_context(data)
    row = {
        "claim_id": "c1",
        "basis": "textbook",
        "status": "supported",
        "reason": "Authored fixture only.",
        "citations": [
            {"evidence_id": "ev_001", "fragment_ids": ["F001"], "relation": "supporting"}
        ],
        "units": [
            {
                "unit_id": unit["unit_id"],
                "status": "supported",
                "fragment_ids": ["F001"],
                "relation_preserved": True,
                "conditions_preserved": True,
                "reason": "Authored fixture only.",
            }
            for unit in context["COMPACT_CLAIM_UNITS"][0]["units"]
        ],
    }
    output = {
        "claims": [row],
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "reason": "Authored fixture only.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        "non_repetitive_next_action": True,
        "requirements": [
            {
                "requirement_id": "r1",
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {"evidence_id": "ev_001", "fragment_id": "F001", "quote_ref": "F001:Q01"}
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored fixture only.",
            }
        ],
        "request_target": {
            "target_id": context["REQUEST_TARGET"]["target_id"],
            "status": "not_applicable",
            "fragment_ids": [],
        },
    }
    return data, output


def expand(data, output, **options):
    return expand_compact_judgment(
        output,
        data,
        answer_mode=options.get("answer_mode", "textbook"),
        teaching_mode=options.get("teaching_mode", "direct"),
    )


def codes(result):
    return {row["code"] for row in result[1] + result[2]}


def test_expansion_uses_immutable_exact_text_and_remains_v5_compatible():
    data, output = fixture()
    before = deepcopy((data, output))
    typed, contract, defects, report = expand(data, output)
    assert not contract and not defects
    assert ReliableCheckV5.model_validate(typed)
    normalized, issues = normalize_judgment(typed, data["ACTUAL_CITATION_BINDINGS"])
    assert not issues and normalized["claims"][0]["fragment_ids"] == ["F001"]
    assert (
        typed["requirements"][0]["evidence"][0]["quote"]
        == data["SOURCE_FRAGMENTS"][0]["exact_text"]
    )
    assert "units" not in typed["claims"][0]
    assert "request_target" not in typed
    assert report["claims"][0]["full_claim"] == data["CLAIMS"][0]["text"]
    restored = report["claims"][0]["units"]
    assert "".join(unit["claim_quote"] for unit in restored) == data["CLAIMS"][0]["text"]
    assert restored[0]["source_quotes"][0]["quote"] == data["SOURCE_FRAGMENTS"][0]["exact_text"]
    assert report["human_rating"] is None and not report["source_entailment_locally_certified"]
    assert (data, output) == before


@pytest.mark.parametrize("field", list(fixture()[1]))
def test_every_top_level_field_is_required_without_fabricated_defaults(field):
    _, output = fixture()
    del output[field]
    with pytest.raises(ValidationError):
        CompactJointCheckV6.model_validate(output)


@pytest.mark.parametrize(
    "field",
    [
        "body_ok",
        "specific_help",
        "scope_ok",
        "suggestions_ok",
        "evidence_display_ok",
        "cumulative_ok",
        "complete_answer",
        "limitations_explicit",
        "attempt_evaluation_ok",
        "tutor_question_ok",
        "non_repetitive_next_action",
    ],
)
def test_negative_legacy_gate_is_never_replaced_with_true(field):
    data, output = fixture()
    output[field] = False
    typed, _, _, _ = expand(data, output)
    assert typed[field] is False


@pytest.mark.parametrize(
    "defect,expected",
    [
        ("missing_claim", "COMPACT_CLAIM_IDENTITY_MISMATCH"),
        ("duplicate_claim", "COMPACT_CLAIM_IDENTITY_MISMATCH"),
        ("unknown_claim", "COMPACT_CLAIM_UNKNOWN"),
        ("missing_unit", "COMPACT_UNIT_IDENTITY_MISMATCH"),
        ("duplicate_unit", "COMPACT_UNIT_IDENTITY_MISMATCH"),
        ("unknown_unit", "COMPACT_UNIT_IDENTITY_MISMATCH"),
        ("duplicate_fid", "COMPACT_UNIT_FRAGMENT_DUPLICATE"),
        ("unknown_fid", "COMPACT_UNIT_SOURCE_INVALID"),
        ("unassessed_fid", "COMPACT_UNIT_ASSESSED_FRAGMENT_MISMATCH"),
        ("contradictory_fid", "COMPACT_UNIT_CITATION_CONFLICT"),
        ("incomplete_fragment", "COMPACT_UNIT_SOURCE_INVALID"),
        ("empty_support", "COMPACT_UNIT_SUPPORT_MISSING"),
        ("foreign_eid", "COMPACT_REQUIREMENT_FRAGMENT_INVALID"),
        ("duplicate_requirement_evidence", "COMPACT_REQUIREMENT_EVIDENCE_DUPLICATE"),
        ("missing_requirement", "REQUIREMENT_IDENTITY_MISMATCH"),
        ("duplicate_requirement", "REQUIREMENT_IDENTITY_MISMATCH"),
        ("unknown_requirement", "REQUIREMENT_IDENTITY_MISMATCH"),
        ("unknown_repair_fid", "COMPACT_REPAIR_FRAGMENT_INVALID"),
    ],
)
def test_invalid_ids_bindings_and_uncovered_units_fail_closed(defect, expected):
    data, output = fixture()
    claim, unit = output["claims"][0], output["claims"][0]["units"][0]
    if defect == "missing_claim":
        output["claims"] = []
    elif defect == "duplicate_claim":
        output["claims"].append(deepcopy(claim))
    elif defect == "unknown_claim":
        claim["claim_id"] = "foreign"
    elif defect == "missing_unit":
        claim["units"].pop()
    elif defect == "duplicate_unit":
        claim["units"].append(deepcopy(unit))
    elif defect == "unknown_unit":
        unit["unit_id"] = "U999"
    elif defect == "duplicate_fid":
        unit["fragment_ids"] = ["F001", "F001"]
    elif defect == "unknown_fid":
        unit["fragment_ids"] = ["F999"]
    elif defect == "unassessed_fid":
        unit["fragment_ids"] = ["F002"]
    elif defect == "contradictory_fid":
        claim["citations"][0]["relation"] = "contradictory"
    elif defect == "incomplete_fragment":
        data["SOURCE_FRAGMENTS"][0]["complete_block"] = False
    elif defect == "empty_support":
        unit["fragment_ids"] = []
    elif defect == "foreign_eid":
        output["requirements"][0]["evidence"][0]["evidence_id"] = "ev_999"
    elif defect == "duplicate_requirement_evidence":
        evidence = output["requirements"][0]["evidence"]
        evidence.append(deepcopy(evidence[0]))
    elif defect == "missing_requirement":
        output["requirements"] = []
    elif defect == "duplicate_requirement":
        output["requirements"].append(deepcopy(output["requirements"][0]))
    elif defect == "unknown_requirement":
        output["requirements"][0]["requirement_id"] = "r999"
    else:
        output["repair_fragment_ids"] = ["F999"]
    result = expand(data, output)
    assert expected in codes(result)
    assert not result[3]["accepted"]


@pytest.mark.parametrize(
    "status,relation,condition",
    [
        ("partial", True, True),
        ("unsupported", True, True),
        ("supported", False, True),
        ("supported", True, False),
    ],
)
def test_one_negative_clause_cannot_be_hidden_by_optimistic_compound_and_body(
    status, relation, condition
):
    data, output = fixture()
    unit = output["claims"][0]["units"][-1]
    unit.update(status=status, relation_preserved=relation, conditions_preserved=condition)
    typed, contract, defects, report = expand(data, output)
    assert not contract
    assert {"COMPACT_CLAIM_OPTIMISTIC_AGGREGATE", "COMPACT_BODY_OPTIMISTIC_AGGREGATE"} <= {
        item["code"] for item in defects
    }
    assert defects and not report["accepted"]
    assert typed["claims"][0]["status"] == "supported"  # Raw verdict, not silently rewritten.
    assert report["claims"][0]["units"][-1]["status"] == status


def test_honest_partial_units_and_requirements_remain_partial_and_need_repair():
    data, output = fixture()
    output.update(
        body_ok=False,
        complete_answer=False,
        coverage="supported_partial",
        missing_facets=["Condition A effect"],
    )
    claim = output["claims"][0]
    claim["status"] = claim["units"][-1]["status"] = "partial"
    output["requirements"][0].update(
        sufficiency="partial",
        response_coverage="limitation",
        missing_information="Condition A is absent.",
    )
    typed, contract, defects, report = expand(data, output)
    assert not contract
    assert typed["claims"][0]["status"] == "partial"
    assert typed["requirements"][0]["sufficiency"] == "partial"
    assert "COMPACT_UNIT_PARTIAL" in {item["code"] for item in defects}
    assert not report["accepted"]


@pytest.mark.parametrize("ref", ["UNKNOWN", "F002:Q01", "P01:Q01", "C001:Q01"])
def test_requirement_quotes_cannot_be_invented_or_redirected_to_another_source_kind(ref):
    data, output = fixture()
    output["requirements"][0]["evidence"][0]["quote_ref"] = ref
    typed, contract, _, report = expand(data, output)
    assert typed is None and "COMPACT_QUOTE_REFERENCE_INVALID" in {r["code"] for r in contract}
    assert not report["accepted"]


def test_model_cannot_copy_or_modify_quoted_text_in_compact_output():
    data, output = fixture()
    output["requirements"][0]["evidence"][0]["quote"] = "Invented quotation."
    with pytest.raises(ValidationError):
        expand(data, output)


def test_complete_long_fragment_is_preserved_and_quote_spans_reconstruct_losslessly():
    data, output = fixture()
    text = ("Condition A holds only if x <= −2.5 °C; exceptions remain relevant. " * 45) + "END"
    data["SOURCE_FRAGMENTS"][0]["exact_text"] = text
    context = compact_check_context(data)
    spans = [ref for ref in context["QUOTE_REFERENCES"] if ref.get("fragment_id") == "F001"]
    assert len(spans) > 1 and "".join(text[s["start"] : s["end"]] for s in spans) == text
    assert all(s["end"] - s["start"] <= 1200 for s in spans)
    assert context["SOURCE_FRAGMENTS"][0]["exact_text"] == text
    output["requirements"][0]["evidence"][0]["quote_ref"] = spans[-1]["quote_ref"]
    typed, contract, _, report = expand(data, output)
    assert not contract
    assert (
        typed["requirements"][0]["evidence"][0]["quote"]
        == text[spans[-1]["start"] : spans[-1]["end"]]
    )
    assert report["claims"][0]["units"][0]["source_quotes"][0]["quote"] == text


@pytest.mark.parametrize(
    "text",
    [
        "Water does not move unless condition A holds and x <= −2.5 °C.",
        "ΔG = −RT ln(K); x ≥ 3 and y → z without heating.",
        "X and Y differ in two conditions, which apply only at 3 m s⁻¹.",
    ],
)
def test_entire_signed_condition_and_negation_text_survives_unit_ids(text):
    data, _ = fixture()
    data["CLAIMS"][0]["text"] = text
    units = compact_check_context(data)["COMPACT_CLAIM_UNITS"][0]["units"]
    assert "".join(unit["text"] for unit in units) == text
    assert units == syntactic_units(data["CLAIMS"])[0]["units"]


def test_given_variant_resolves_actual_problem_quote_without_textbook_fields():
    data, output = fixture()
    data["question"] = data["current_problem"] = "Given x=3 J."
    data["CLAIMS"][0]["text"] = "x=3 J."
    data["ACTUAL_CITATION_BINDINGS"][0]["citations"] = []
    output["claims"] = [
        {
            "claim_id": "c1",
            "basis": "problem_input",
            "status": "supported",
            "problem_quote_ref": "P01:Q01",
            "reason": "Authored given.",
            "units": [
                {
                    "unit_id": "U01",
                    "status": "supported",
                    "relation_preserved": True,
                    "conditions_preserved": True,
                    "reason": "Authored given.",
                }
            ],
        }
    ]
    typed, contract, _, _ = expand(data, output)
    assert not contract and typed["claims"][0]["problem_quote"] == "Given x=3 J."
    assert "citations" not in typed["claims"][0]


def test_general_variant_and_requirement_have_no_textbook_certification():
    data, output = fixture()
    row = output["claims"][0]
    row["basis"] = "general_knowledge"
    row.pop("citations")
    for unit in row["units"]:
        unit.pop("fragment_ids")
    data["ACTUAL_CITATION_BINDINGS"][0]["citations"] = []
    output["requirements"][0].update(sufficiency="not_applicable", evidence=[])
    typed, contract, _, _ = expand(data, output, answer_mode="general_knowledge")
    assert not contract and typed["claims"][0]["basis"] == "general_knowledge"
    assert "citations" not in typed["claims"][0]


@pytest.mark.parametrize("basis", ["nonfactual", "evidence_limitation"])
def test_procedural_and_limitation_variants_have_only_applicable_fields(basis):
    data, output = fixture()
    output["claims"] = [{"claim_id": "c1", "basis": basis, "reason": "Authored classification."}]
    data["ACTUAL_CITATION_BINDINGS"][0]["citations"] = []
    typed, _, _, _ = expand(data, output)
    assert set(typed["claims"][0]) == {"claim_id", "basis", "reason"}
    output["claims"][0]["status"] = "supported"
    with pytest.raises(ValidationError):
        CompactJointCheckV6.model_validate(output)


def calculation_fixture(problem_formula=False):
    data, output = fixture()
    data["question"] = data["current_problem"] = "Given x=3 J; q=2*x."
    data["CLAIMS"][0]["text"] = "The result is 6 J."
    data["SOURCE_FRAGMENTS"][0]["exact_text"] = "The applicable formula is q=2*x."
    row = output["claims"][0]
    row["basis"] = "derived_calculation"
    row["units"] = [
        {
            "unit_id": "U01",
            "status": "supported",
            "fragment_ids": ["F001"],
            "relation_preserved": True,
            "conditions_preserved": True,
            "reason": "Authored calculation.",
        }
    ]
    row["derivation"] = {
        "formula_basis": "textbook",
        "formula_fragment_id": "F001",
        "formula_quote_ref": "F001:Q01",
        "expression": "2*x",
        "inputs": [
            {
                "name": "x",
                "value": "3",
                "unit": "J",
                "quote_ref": "P01:Q01",
                "origin": "problem_input",
                "fragment_id": None,
            }
        ],
        "result": "6",
        "result_quote_ref": "C001:N01",
        "result_unit": "J",
        "units_consistent": True,
        "formula_applicable": True,
    }
    if problem_formula:
        row["citations"] = []
        row["units"][0]["fragment_ids"] = []
        data["ACTUAL_CITATION_BINDINGS"][0]["citations"] = []
        row["derivation"].update(
            formula_basis="problem_input", formula_fragment_id=None, formula_quote_ref="P01:Q01"
        )
    return data, output


@pytest.mark.parametrize("problem_formula", [False, True])
def test_derivation_references_preserve_existing_arithmetic_given_formula_and_unit_gates(
    problem_formula,
):
    data, output = calculation_fixture(problem_formula)
    typed, contract, _, _ = expand(data, output)
    assert not contract
    proof = typed["claims"][0]["derivation"]
    fragments = {f["fragment_id"]: f for f in data["SOURCE_FRAGMENTS"]}
    checked = validate_derivation(proof, data["CLAIMS"][0]["text"], fragments, [data["question"]])
    assert checked["valid"]
    proof["units_consistent"] = False
    assert (
        validate_derivation(proof, data["CLAIMS"][0]["text"], fragments, [data["question"]])["code"]
        == "DERIVATION_MODEL_CONDITIONS_FAILED"
    )


def test_derivation_cannot_source_an_unassessed_fragment_or_foreign_claim_result():
    data, output = calculation_fixture()
    output["claims"][0]["derivation"].update(
        formula_fragment_id="F002", formula_quote_ref="F002:Q01"
    )
    assert "COMPACT_PROOF_ASSESSED_FRAGMENT_MISMATCH" in codes(expand(data, output))
    output["claims"][0]["derivation"]["result_quote_ref"] = "P01:Q01"
    assert expand(data, output)[0] is None


def test_strict_reasons_and_boolean_fields_prevent_hidden_or_coerced_judgments():
    _, output = fixture()
    output["claims"][0]["units"][0]["reason"] = "x" * 121
    with pytest.raises(ValidationError):
        CompactJointCheckV6.model_validate(output)
    output["claims"][0]["units"][0]["reason"] = "Valid."
    output["body_ok"] = "true"
    with pytest.raises(ValidationError):
        CompactJointCheckV6.model_validate(output)


def test_real_offline_tokenizer_measures_long_response_reduction_without_claiming_quality():
    data, output = fixture()
    data["SOURCE_FRAGMENTS"][0]["exact_text"] = (
        "A complete condition-qualified source paragraph. " * 23
    )
    for index in range(1, 8):
        row = deepcopy(output["requirements"][0])
        row["requirement_id"] = f"r{index}"
        if index == 1:
            output["requirements"][0] = row
        else:
            output["requirements"].append(row)
    data["CONTEXT_COVERAGE"]["requirements"] = [{"id": f"r{i}"} for i in range(1, 8)]
    typed, contract, _, _ = expand(data, output)
    assert not contract
    counter = TokenCounter(
        ModelConfig(
            provider="openai",
            model="gpt-4",
            tokenizer_provider="tiktoken",
            tokenizer_name="cl100k_base",
            token_count_fallback="error",
        )
    )
    assert counter.metadata["source"] == "tiktoken" and not counter.metadata["is_estimate"]
    compact_tokens = counter.count(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    restored_tokens = counter.count(json.dumps(typed, ensure_ascii=False, separators=(",", ":")))
    assert compact_tokens < restored_tokens * 0.7
    assert compact_tokens < 4096
    # This comparison concerns serialization, not DeepSeek token identity or accuracy.


def test_prompt_names_every_schema_gate_and_separates_literal_presence_and_semantics():
    prompt = (
        Path(__file__).resolve().parents[2] / "generation/prompts/joint_check_v6.txt"
    ).read_text()
    for field in CompactJointCheckV6.model_fields:
        assert field in prompt
    assert "NOT guaranteed atomic" in prompt and "Literal input presence is separate" in prompt


def selected_fixture():
    data, output = fixture()
    full = deepcopy(data["SOURCE_FRAGMENTS"])
    digest = lambda text: hashlib.sha256(text.encode()).hexdigest()
    for index, fragment in enumerate(full):
        fragment.update(
            asset_id="document-one",
            document_version_id="version-one",
            processing_id="processing-one",
            source_unit_id=f"unit-{index}",
            start=0,
            end=len(fragment["exact_text"]),
            text_hash=digest(fragment["exact_text"]),
            offset_basis="cleaned_source_unit_unicode",
        )
    text = full[0]["exact_text"]
    data["READING_CONTEXT"] = {
        "version": "reading_scope_v1",
        "release_id": "release-one",
        "document_id": "document-one",
        "processing_id": "processing-one",
        "source_unit_id": "unit-0",
        "scope_hash": digest("scope"),
        "selection": {
            "start": 0,
            "end": len(text),
            "text": text,
            "text_hash": digest(text),
            "unit_text_hash": digest(text),
        },
    }
    context = compact_check_context(data, full_fragments=full)
    output["request_target"] = {
        "target_id": context["REQUEST_TARGET"]["target_id"],
        "status": "present",
        "fragment_ids": ["F001"],
    }
    return data, output, full


def test_actual_selected_input_presence_remains_separate_from_semantic_gap():
    data, output, full = selected_fixture()
    output["body_ok"] = False
    output["claims"][0]["status"] = "partial"
    output["claims"][0]["units"][0]["status"] = "partial"
    typed, contract, defects, report = expand_compact_judgment(
        output,
        data,
        answer_mode="textbook",
        teaching_mode="direct",
        full_fragments=full,
    )
    assert not contract and defects
    assert typed["body_ok"] is False and not report["accepted"]
    assert report["request_target"]["input_status"] == "present"
    assert report["request_target"]["source_coverage"] == "complete"
    assert report["request_target"]["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "defect,code",
    [
        ("false_missing", "REQUEST_TARGET_LITERAL_PRESENCE_CONTRADICTION"),
        ("wrong_id", "REQUEST_TARGET_ID_MISMATCH"),
        ("duplicate_fid", "REQUEST_TARGET_DUPLICATE_ASSESSMENT_FRAGMENT"),
        ("unproven_fid", "REQUEST_TARGET_UNPROVEN_ASSESSMENT_FRAGMENT"),
    ],
)
def test_request_target_input_falsehoods_remain_contract_errors(defect, code):
    data, output, full = selected_fixture()
    assessment = output["request_target"]
    if defect == "false_missing":
        assessment.update(status="missing", fragment_ids=[])
    elif defect == "wrong_id":
        assessment["target_id"] = "rt_" + "0" * 32
    elif defect == "duplicate_fid":
        assessment["fragment_ids"] = ["F001", "F001"]
    else:
        assessment["fragment_ids"] = ["F002"]
    result = expand_compact_judgment(
        output, data, answer_mode="textbook", teaching_mode="direct", full_fragments=full
    )
    assert code in {item["code"] for item in result[1]} and not result[3]["accepted"]


@pytest.mark.parametrize("field", ["exact_text", "evidence_id", "complete_block", "fragment_id"])
def test_metadata_not_submitted_to_checker_cannot_certify_literal_target(field):
    data, output, full = selected_fixture()
    full[0][field] = False if field == "complete_block" else "other-value"
    with pytest.raises(ValueError, match="COMPACT_TARGET_FRAGMENT_INPUT_MISMATCH"):
        compact_check_context(data, full_fragments=full)
    with pytest.raises(ValueError, match="COMPACT_TARGET_FRAGMENT_INPUT_MISMATCH"):
        expand_compact_judgment(
            output, data, answer_mode="textbook", teaching_mode="direct", full_fragments=full
        )


def test_selected_target_and_whole_model_input_cannot_disagree():
    data, _, full = selected_fixture()
    other = deepcopy(data["READING_CONTEXT"])
    other["selection"]["text"] = "An unrelated passage."
    with pytest.raises(ValueError, match="COMPACT_TARGET_READING_INPUT_MISMATCH"):
        compact_check_context(data, full_fragments=full, reading_context=other)


@pytest.mark.parametrize("missing", [True, False])
def test_expansion_cannot_assert_literal_presence_from_auxiliary_hidden_context(missing):
    data, output, full = selected_fixture()
    reading = data.pop("READING_CONTEXT")
    if not missing:
        data["READING_CONTEXT"] = None
    with pytest.raises(ValueError, match="COMPACT_TARGET_READING_INPUT_MISMATCH"):
        expand_compact_judgment(
            output,
            data,
            answer_mode="textbook",
            teaching_mode="direct",
            full_fragments=full,
            reading_context=reading,
        )
    if missing:
        shown = compact_check_context(data, full_fragments=full, reading_context=reading)
        assert shown["READING_CONTEXT"] == reading
        typed, contract, _, report = expand_compact_judgment(
            output,
            shown,
            answer_mode="textbook",
            teaching_mode="direct",
            full_fragments=full,
            reading_context=reading,
        )
        assert (
            typed is not None
            and not contract
            and report["request_target"]["input_status"] == "present"
        )


def test_short_answer_every_unit_is_assessed_and_compound_support_cannot_skip_last_clause():
    data, output = fixture()
    text = "Starch is converted into sucrose and sucrose is stored as sucrose [ev_001]."
    data["CLAIMS"].append({"claim_id": "c2", "text": text, "answer_field": "short_answer"})
    binding = deepcopy(data["ACTUAL_CITATION_BINDINGS"][0])
    binding["claim_id"] = "c2"
    data["ACTUAL_CITATION_BINDINGS"].append(binding)
    claim = deepcopy(output["claims"][0])
    claim["claim_id"] = "c2"
    units = syntactic_units(data["CLAIMS"])[1]["units"]
    claim["units"] = [{**deepcopy(claim["units"][0]), "unit_id": unit["unit_id"]} for unit in units]
    claim["units"][-1]["status"] = "unsupported"
    output["claims"].append(claim)
    result = expand(data, output)
    assert not result[1] and {
        "COMPACT_UNIT_UNSUPPORTED",
        "COMPACT_BODY_OPTIMISTIC_AGGREGATE",
    } <= codes(result)
    assert not result[3]["accepted"]
    claim["units"].pop()
    assert "COMPACT_UNIT_IDENTITY_MISMATCH" in codes(expand(data, output))


def test_quote_catalogue_tampering_is_ignored_and_exact_server_original_is_restored():
    data, output = fixture()
    context = compact_check_context(data)
    context["QUOTE_REFERENCES"][0]["start"] = 999
    context["QUOTE_REFERENCES"][0]["exact_text"] = "Forged model quotation."
    context["COMPACT_CLAIM_UNITS"][0]["units"][0]["text"] = "Forged unit."
    typed, contract, _, report = expand(context, output)
    assert not contract
    assert (
        typed["requirements"][0]["evidence"][0]["quote"]
        == data["SOURCE_FRAGMENTS"][0]["exact_text"]
    )
    assert report["claims"][0]["units"][0]["claim_quote"] != "Forged unit."


@pytest.mark.parametrize(
    "defect,code",
    [
        ("duplicate", "COMPACT_ACTUAL_CITATION_IDENTITY_MISMATCH"),
        ("missing", "COMPACT_ACTUAL_CITATION_IDENTITY_MISMATCH"),
        ("foreign", "COMPACT_ACTUAL_CITATION_IDENTITY_MISMATCH"),
        ("duplicate_fid", "COMPACT_ACTUAL_CITATION_FRAGMENT_INVALID"),
        ("irrelevant", "COMPACT_CITATION_IRRELEVANT"),
    ],
)
def test_entire_actual_citation_assessment_is_preserved_without_dictionary_overwrite(defect, code):
    data, output = fixture()
    row = output["claims"][0]
    if defect == "duplicate":
        first = deepcopy(row["citations"][0])
        first["relation"] = "contradictory"
        row["citations"].insert(0, first)
    elif defect == "missing":
        row["citations"] = []
    elif defect == "foreign":
        row["citations"][0]["evidence_id"] = "ev_999"
    elif defect == "duplicate_fid":
        row["citations"][0]["fragment_ids"] = ["F001", "F001"]
    else:
        row["citations"][0]["relation"] = "irrelevant"
        row["units"][0]["status"] = "partial"
    result = expand(data, output)
    assert code in codes(result) and not result[3]["accepted"]


@pytest.mark.parametrize("defect", ["claims", "fragments", "bindings"])
def test_input_reference_duplicates_are_rejected_before_provider_submission(defect):
    data, _ = fixture()
    if defect == "claims":
        data["CLAIMS"].append(deepcopy(data["CLAIMS"][0]))
    elif defect == "fragments":
        data["SOURCE_FRAGMENTS"].append(deepcopy(data["SOURCE_FRAGMENTS"][0]))
    else:
        data["ACTUAL_CITATION_BINDINGS"] = []
    with pytest.raises(ValueError, match="COMPACT_INPUT_"):
        compact_check_context(data)


def test_general_and_procedural_labels_cannot_discard_actual_draft_citations():
    data, output = fixture()
    output["claims"] = [{"claim_id": "c1", "basis": "nonfactual", "reason": "Authored label."}]
    assert "COMPACT_UNEXPECTED_CITATION_FOR_BASIS" in codes(expand(data, output))
