"""Authored provenance controls, not measurements of semantic model quality."""

import json
from copy import deepcopy

import pytest

from generation import GenerationService, RequestBudget
from generation.parser import strict_json
from generation.reliability_v5 import assess_requirements
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer
from test_example_source_entailment_v5 import (
    COMPOUND,
    PARAPHRASE,
    checker_data,
    draft,
    judgment,
    source_request,
)


def _case():
    fragments = [
        {
            "fragment_id": "F001",
            "evidence_id": "ev_001",
            "exact_text": "Alpha sentence.",
            "complete_block": True,
        },
        {
            "fragment_id": "F002",
            "evidence_id": "ev_001",
            "exact_text": "Beta sentence.",
            "complete_block": True,
        },
    ]
    value = {
        "requirements": [
            {
                "requirement_id": "R1",
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {
                        "evidence_id": "ev_001",
                        "fragment_id": "F001",
                        "quote": "Alpha sentence.",
                    }
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored provenance fixture only.",
            }
        ],
        "limitations_explicit": True,
        "non_repetitive_next_action": True,
        "coverage": "full",
    }
    return value, {"requirements": [{"id": "R1"}]}, fragments


def _assess(value, coverage, fragments):
    before = deepcopy((value, coverage, fragments))
    result = assess_requirements(
        value, coverage, fragments, answer_mode="textbook", teaching_mode="direct"
    )
    assert (value, coverage, fragments) == before
    return result


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("unknown", ["UNKNOWN_FRAGMENT"]),
        ("evidence", ["EVIDENCE_ID_MISMATCH"]),
        ("quote", ["QUOTE_NOT_EXACT_SUBSTRING"]),
        ("block", ["INCOMPLETE_BLOCK"]),
        (
            "combined",
            ["EVIDENCE_ID_MISMATCH", "QUOTE_NOT_EXACT_SUBSTRING", "INCOMPLETE_BLOCK"],
        ),
    ],
)
def test_fixed_reason_codes_preserve_contract_failure_without_source_text(fault, expected):
    value, coverage, fragments = _case()
    support = value["requirements"][0]["evidence"][0]
    if fault == "unknown":
        support["fragment_id"] = "FOREIGN_PRIVATE_FRAGMENT"
    if fault in {"evidence", "combined"}:
        support["evidence_id"] = "FOREIGN_PRIVATE_EVIDENCE"
    if fault in {"quote", "combined"}:
        support["quote"] = "PRIVATE_INVENTED_QUOTE"
    if fault in {"block", "combined"}:
        fragments[0]["complete_block"] = False
    contract, defects, assessment = _assess(value, coverage, fragments)
    assert contract == [
        {
            "code": "REQUIREMENT_SOURCE_QUOTE_INVALID",
            "requirement_id": "R1",
            "evidence_index": 0,
            "reason_codes": expected,
        }
    ]
    assert defects == []
    assert assessment["status"] == "sufficient"
    assert assessment["independent_evaluation"] is False
    serialized = json.dumps(contract)
    assert "PRIVATE" not in serialized and "Alpha sentence." not in serialized


def test_cross_fragment_quote_is_rejected_and_separate_objects_pass_provenance_only():
    value, coverage, fragments = _case()
    row = value["requirements"][0]
    row["evidence"][0]["quote"] = "Alpha sentence. Beta sentence."
    contract, _, _ = _assess(value, coverage, fragments)
    assert contract[0]["reason_codes"] == ["QUOTE_NOT_EXACT_SUBSTRING"]
    row["evidence"] = [
        {
            "evidence_id": fragment["evidence_id"],
            "fragment_id": fragment["fragment_id"],
            "quote": fragment["exact_text"],
        }
        for fragment in fragments
    ]
    contract, defects, assessment = _assess(value, coverage, fragments)
    assert contract == defects == []
    assert assessment["requirements"][0]["sufficiency"] == "sufficient"
    assert assessment["human_rating"] is None
    assert assessment["independent_evaluation"] is False


def test_exact_quotes_survive_json_escaping_roundtrip():
    value, coverage, fragments = _case()
    source = 'The "label" uses C:\\source.\nA\tsecond line says caf\u00e9.'
    fragments[0]["exact_text"] = source
    value["requirements"][0]["evidence"][0]["quote"] = source
    parsed = strict_json(json.dumps({"value": value, "fragments": fragments}, ensure_ascii=True))
    contract, defects, _ = _assess(parsed["value"], coverage, parsed["fragments"])
    assert contract == defects == []
    assert parsed["fragments"][0]["exact_text"] == source


@pytest.mark.parametrize(
    "source,altered",
    [("Alpha  sentence.", "Alpha sentence."), ("caf\u00e9", "cafe\u0301")],
)
def test_whitespace_and_unicode_variants_are_not_normalized_into_support(source, altered):
    value, coverage, fragments = _case()
    fragments[0]["exact_text"] = source
    value["requirements"][0]["evidence"][0]["quote"] = altered
    contract, _, _ = _assess(value, coverage, fragments)
    assert contract[0]["reason_codes"] == ["QUOTE_NOT_EXACT_SUBSTRING"]


@pytest.mark.parametrize("index,expected_index", [(7, 7), (8, None)])
def test_evidence_index_is_bounded_without_mislabeling_oversized_direct_input(
    index, expected_index
):
    value, coverage, fragments = _case()
    row = value["requirements"][0]
    row["evidence"] = [deepcopy(row["evidence"][0]) for _ in range(index + 1)]
    row["evidence"][-1]["quote"] = "Invented quote."
    contract, _, _ = _assess(value, coverage, fragments)
    assert len(contract) == 1
    assert contract[0]["evidence_index"] == expected_index
    assert contract[0]["reason_codes"] == ["QUOTE_NOT_EXACT_SUBSTRING"]


def test_valid_provenance_does_not_promote_authored_partial_requirement():
    value, coverage, fragments = _case()
    value["coverage"] = "supported_partial"
    value["requirements"][0].update(
        sufficiency="partial", response_coverage="partial", missing_information="Mechanism absent."
    )
    contract, defects, assessment = _assess(value, coverage, fragments)
    assert contract == defects == []
    assert assessment["status"] == "partial"
    assert assessment["requirements"][0]["sufficiency"] == "partial"
    assert assessment["requirements"][0]["missing_information"] == "Mechanism absent."


def _invalid_quote(messages):
    value = checker(messages)
    value["requirements"][0]["evidence"][0]["quote"] = "PRIVATE_INVENTED_QUOTE"
    return value


def test_correction_feedback_requires_separate_objects_and_keeps_draft_unchanged():
    request = req()
    before = deepcopy((request.question, request.evidence, request.source_map))
    script = Script([answer(), _invalid_quote, checker])
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=3, max_active_seconds=180)
    )
    assert outcome.succeeded, outcome.error
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    feedback = script.calls[2][0][-1]["content"]
    assert "return separate evidence objects" in feedback
    assert "including fragments sharing one evidence_id" in feedback
    assert "exact contiguous substring of that fragment" in feedback
    assert "same unchanged draft" in feedback
    assert "does not establish semantic sufficiency or support" in feedback
    assert outcome.checks[0]["projection_hash"] == outcome.checks[1]["projection_hash"]
    assert outcome.budget["consumed_calls"] == outcome.budget["max_calls"] == 3
    assert (request.question, request.evidence, request.source_map) == before


def test_terminal_quote_failure_remains_unpublished_and_public_error_excludes_raw_text():
    script = Script([answer(), _invalid_quote])
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        req(), RequestBudget(max_calls=2, max_active_seconds=180)
    )
    assert outcome.response is None and not outcome.delivered_projection
    assert outcome.error["code"] == "CHECKER_INCONSISTENT"
    assert outcome.error["details"]["issue_codes"] == ["REQUIREMENT_SOURCE_QUOTE_INVALID"]
    assert "PRIVATE_INVENTED_QUOTE" not in json.dumps(outcome.error)
    assert outcome.checks[-1]["accepted"] is False
    assert outcome.checks[-1]["checker_inconsistencies"][0]["reason_codes"] == [
        "QUOTE_NOT_EXACT_SUBSTRING"
    ]
    assert outcome.budget["consumed_calls"] == 2


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_exact_source_quotes_do_not_override_negative_claim_semantics(status):
    request = source_request()
    before = deepcopy((request.question, request.evidence, request.source_map))
    script = Script([draft(COMPOUND), judgment(status=status)])
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=2, max_active_seconds=180)
    )
    assert not outcome.succeeded and outcome.response is None and not outcome.delivered_projection
    assert outcome.checks[0]["accepted"] is False
    assert outcome.checks[0]["typed_judgment_raw_aliases"]["claims"][0]["status"] == status
    assert (request.question, request.evidence, request.source_map) == before
    assert outcome.budget["consumed_calls"] == 2


def test_fragment_rule_reaches_initial_check_and_final_recheck_with_same_schema_and_budget():
    request = source_request()
    before = deepcopy((request.question, request.evidence, request.source_map))
    script = Script([draft(COMPOUND), judgment(status="partial"), draft(PARAPHRASE), judgment()])
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=4, max_active_seconds=180)
    )
    assert outcome.succeeded, outcome.error
    checks = [
        (messages, kwargs)
        for messages, kwargs in script.calls
        if kwargs["request_context"]["purpose"] in {"joint_check", "joint_recheck"}
    ]
    assert [kwargs["request_context"]["purpose"] for _, kwargs in checks] == [
        "joint_check",
        "joint_recheck",
    ]
    for messages, kwargs in checks:
        assert (
            "For each contributing fragment, return a separate requirement evidence object"
            in messages[0]["content"]
        )
        assert "never assign the combined sentence to one fragment" in messages[0]["content"]
        assert (
            "SOURCE_FRAGMENTS and ACTUAL_CITATION_BINDINGS are immutable" in messages[0]["content"]
        )
        for fragment in checker_data(messages)["SOURCE_FRAGMENTS"]:
            assert fragment["exact_text"] in request.evidence[0]["text"]
        assert kwargs["response_schema_name"] == "joint_check_v5"
    assert checks[0][1]["response_schema"] == checks[1][1]["response_schema"]
    assert outcome.budget["consumed_calls"] == outcome.budget["max_calls"] == 4
    assert outcome.checks[0]["accepted"] is False
    assert outcome.checks[0]["typed_judgment_raw_aliases"]["claims"][0]["status"] == "partial"
    assert (request.question, request.evidence, request.source_map) == before
