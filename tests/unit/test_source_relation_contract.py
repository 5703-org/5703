"""Exact-binding and pipeline contracts, using explicitly authored judgments.

These tests do not measure the semantic accuracy of a real online checker.
"""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation.checker_encoding import decode
from generation.local_repair import VERSION as REPAIR_VERSION
from generation.reliability_v5 import ReliableCheckV5
from generation.source_relations import VERSION, ReliableRelationCheck, assess_source_relations
from generation.teaching_plan_v6 import freeze_generation_policy
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer, request


def check_input(messages):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data["SOURCE_FRAGMENT_TABLE"]
        data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
    return data


def relation_checker(messages, **updates):
    data = check_input(messages)
    value = checker(messages, **updates)
    actual = {row["claim_id"]: row for row in data["CLAIMS"]}
    fragments = {row["fragment_id"]: row for row in data["SOURCE_FRAGMENTS"]}
    for row in value["claims"]:
        if row["basis"] != "textbook":
            continue
        source_quotes = [
            {
                "evidence_id": citation["evidence_id"],
                "fragment_id": fid,
                "quote": fragments[fid]["exact_text"],
            }
            for citation in row["citations"]
            for fid in citation["fragment_ids"]
        ]
        row.update(
            obligations_complete=True,
            obligations=[
                {
                    "claim_quote": actual[row["claim_id"]]["text"],
                    "status": "supported",
                    "source_quotes": source_quotes,
                    "relation_preserved": True,
                    "conditions_preserved": True,
                    "reason": "Explicitly authored transport judgment; not a semantic rating.",
                }
            ],
        )
    return value


def fixture(text="Under condition A, a liquid does not move from X to Y [ev_001]."):
    obligation = {
        "claim_quote": text,
        "status": "supported",
        "source_quotes": [
            {"evidence_id": "ev_001", "fragment_id": "F001", "quote": "liquid does not move"}
        ],
        "relation_preserved": True,
        "conditions_preserved": True,
        "reason": "Authored contract receipt.",
    }
    typed = {
        "claims": [
            {
                "claim_id": "c1",
                "basis": "textbook",
                "status": "supported",
                "citations": [
                    {"evidence_id": "ev_001", "fragment_ids": ["F001"], "relation": "supporting"}
                ],
                "obligations": [obligation],
                "obligations_complete": True,
            }
        ]
    }
    claims = [{"claim_id": "c1", "text": text}]
    bindings = [
        {
            "claim_id": "c1",
            "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F001"]}],
        }
    ]
    fragments = [
        {
            "fragment_id": "F001",
            "evidence_id": "ev_001",
            "complete_block": True,
            "exact_text": "Under condition A, a liquid does not move from X to Y.",
        }
    ]
    return typed, claims, bindings, fragments


def test_exact_relation_quotes_bind_actual_complete_sources_without_certifying_entailment():
    contract, defects, assessment = assess_source_relations(*fixture())
    assert contract == defects == []
    assert assessment["accepted"]
    assert not assessment["independent_evaluation"]
    assert assessment["human_rating"] is None
    assert not assessment["source_entailment_locally_certified"]
    unit = assessment["claims"][0]["obligations"][0]
    assert unit["claim_start"] == 0 and unit["claim_end"] == len(unit["claim_quote"])


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_negative_atomic_relation_blocks_optimistic_aggregate_without_rewriting_it(status):
    values = fixture()
    values[0]["claims"][0]["obligations"][0]["status"] = status
    contract, defects, assessment = assess_source_relations(*values)
    assert not contract
    assert defects[0]["code"] == "SOURCE_RELATION_" + status.upper()
    assert assessment["claims"][0]["checker_claim_status"] == "supported"
    assert not assessment["accepted"]


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("relation_preserved", "SOURCE_RELATION_CHANGED"),
        ("conditions_preserved", "SOURCE_CONDITION_CHANGED"),
    ],
)
def test_reversed_relation_or_missing_conditions_are_semantic_failures(field, code):
    values = fixture()
    values[0]["claims"][0]["obligations"][0][field] = False
    contract, defects, _ = assess_source_relations(*values)
    assert not contract and defects == [{"code": code, "claim_id": "c1", "unit": 1}]


@pytest.mark.parametrize("missing", ["Under condition A, ", "not ", " from X to Y"])
def test_omitted_condition_negation_or_predicate_words_cannot_escape_assessment(missing):
    values = fixture()
    text = values[1][0]["text"]
    start = text.index(missing)
    pieces = [text[:start], text[start + len(missing) :]]
    base = values[0]["claims"][0]["obligations"][0]
    values[0]["claims"][0]["obligations"] = [
        {**deepcopy(base), "claim_quote": piece} for piece in pieces if piece
    ]
    contract, _, _ = assess_source_relations(*values)
    assert {row["code"] for row in contract} == {"RELATION_CLAIM_CONTENT_OMITTED"}


@pytest.mark.parametrize("operator", ["−", "≤", "→"])
def test_omitted_mathematical_sign_is_a_missing_condition_even_when_words_match(operator):
    text = f"The quantity follows A {operator} B [ev_001]."
    values = fixture(text)
    base = values[0]["claims"][0]["obligations"][0]
    left, right = text.split(operator)
    values[0]["claims"][0]["obligations"] = [
        {**deepcopy(base), "claim_quote": left},
        {**deepcopy(base), "claim_quote": right},
    ]
    contract, _, assessment = assess_source_relations(*values)
    assert {row["code"] for row in contract} == {"RELATION_CLAIM_CONTENT_OMITTED"}
    assert not assessment["accepted"]


@pytest.mark.parametrize(
    "defect", ["foreign_evidence", "foreign_fragment", "invented_quote", "incomplete", "duplicate"]
)
def test_foreign_invented_incomplete_or_duplicate_source_bindings_fail_closed(defect):
    values = fixture()
    obligation = values[0]["claims"][0]["obligations"][0]
    quote = obligation["source_quotes"][0]
    if defect == "foreign_evidence":
        quote["evidence_id"] = "ev_999"
    elif defect == "foreign_fragment":
        quote["fragment_id"] = "F999"
    elif defect == "invented_quote":
        quote["quote"] = "Invented source wording."
    elif defect == "incomplete":
        values[3][0]["complete_block"] = False
    else:
        obligation["source_quotes"].append(deepcopy(quote))
    contract, _, _ = assess_source_relations(*values)
    assert "RELATION_SOURCE_QUOTE_INVALID" in {row["code"] for row in contract}


def test_allowed_but_unassessed_source_fragment_cannot_certify_the_displayed_fragment():
    values = fixture()
    values[2][0]["citations"][0]["allowed_fragment_ids"].append("F002")
    values[3].append({**values[3][0], "fragment_id": "F002"})
    values[0]["claims"][0]["obligations"][0]["source_quotes"][0]["fragment_id"] = "F002"
    contract, _, assessment = assess_source_relations(*values)
    assert {row["code"] for row in contract} == {"RELATION_ASSESSED_FRAGMENT_MISMATCH"}
    assert not assessment["accepted"]


@pytest.mark.parametrize("relation", ["irrelevant", "contradictory"])
def test_supported_obligation_cannot_conflict_with_its_citation_assessment(relation):
    values = fixture()
    values[0]["claims"][0]["citations"][0]["relation"] = relation
    contract, _, _ = assess_source_relations(*values)
    assert {row["code"] for row in contract} == {"RELATION_SUPPORT_CITATION_CONFLICT"}


def test_negative_obligation_keeps_actual_contradictory_source_and_remains_rejected():
    values = fixture()
    values[0]["claims"][0]["citations"][0]["relation"] = "contradictory"
    values[0]["claims"][0]["obligations"][0].update(status="unsupported", relation_preserved=False)
    contract, defects, assessment = assess_source_relations(*values)
    assert not contract and defects and not assessment["accepted"]


@pytest.mark.parametrize(
    "defect", ["unknown_claim", "ambiguous_quote", "missing_quote", "duplicate_unit", "unassessed"]
)
def test_unknown_ambiguous_or_unassessed_claims_never_certify_support(defect):
    values = fixture()
    claim = values[0]["claims"][0]
    if defect == "unknown_claim":
        claim["claim_id"] = "unknown"
    elif defect == "ambiguous_quote":
        claim["obligations"][0]["claim_quote"] = "a"
    elif defect == "missing_quote":
        claim["obligations"][0]["source_quotes"] = []
    elif defect == "duplicate_unit":
        claim["obligations"].append(deepcopy(claim["obligations"][0]))
    else:
        claim["obligations_complete"] = False
    contract, defects, assessment = assess_source_relations(*values)
    assert contract or defects
    assert not assessment["accepted"]


def test_complementary_sources_do_not_override_an_unsupported_disjunct():
    text = "A liquid moves from X to Y and returns from Y to X [ev_001]."
    values = fixture(text)
    base = values[0]["claims"][0]["obligations"][0]
    left, right = text.split(" and ")
    values[0]["claims"][0]["obligations"] = [
        {**deepcopy(base), "claim_quote": left},
        {
            **deepcopy(base),
            "claim_quote": " and " + right,
            "status": "unsupported",
            "relation_preserved": False,
        },
    ]
    contract, defects, assessment = assess_source_relations(*values)
    assert not contract
    assert {row["code"] for row in defects} == {
        "SOURCE_RELATION_UNSUPPORTED",
        "SOURCE_RELATION_CHANGED",
    }
    assert assessment["claims"][0]["exact_claim_content_covered"]


def test_new_pipeline_uses_pinned_schema_and_actual_fragment_ids_in_private_receipt():
    adapter = Script([answer(), relation_checker])
    out = GenerationService(adapter).generate(req(source_relation_policy=VERSION))
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_source_relations_v1"
    assert "SOURCE RELATION CONTRACT V1" in adapter.calls[1][0][0]["content"]
    assert "QUESTION GRANULARITY" in adapter.calls[1][0][0]["content"]
    check_data = check_input(adapter.calls[1][0])
    assert check_data["SOURCE_RELATION_POLICY"] == VERSION
    assert not check_data["REQUESTED_KNOWLEDGE_SCOPE"]["style_preferences_add_required_facts"]
    assessment = out.checks[0]["source_relation_assessment"]
    source = assessment["claims"][0]["obligations"][0]["source_quotes"][0]
    assert source["fragment_id"] != "F001"
    report = out.token_budget["source_relation_support"]
    assert report["accepted"] and report["human_rating"] is None
    assert "claims" not in report


def mismatched_quote(messages):
    data = check_input(messages)
    value = relation_checker(messages)
    first_claim = value["claims"][0]
    evidence_id = first_claim["citations"][0]["evidence_id"]
    assessed = set(first_claim["citations"][0]["fragment_ids"])
    alternate = next(
        f
        for f in data["SOURCE_FRAGMENTS"]
        if f["evidence_id"] == evidence_id and f["fragment_id"] not in assessed
    )
    first_claim["obligations"][0]["source_quotes"] = [
        {
            "evidence_id": evidence_id,
            "fragment_id": alternate["fragment_id"],
            "quote": alternate["exact_text"],
        }
    ]
    return value


def test_exact_two_call_counterexample_no_longer_publishes_wrong_highlight():
    out = GenerationService(
        Script([answer("Carbon dioxide supplies carbon for sugar. [ev_001]"), mismatched_quote])
    ).generate(req(source_relation_policy=VERSION), RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 2
    assert "RELATION_ASSESSED_FRAGMENT_MISMATCH" in json.dumps(out.checks)
    assert out.checks[0]["accepted"] is False


def test_explicit_checker_correction_rechecks_and_publishes_only_its_actual_assessed_fragment():
    def corrected(messages):
        value = mismatched_quote(messages)
        claim = value["claims"][0]
        claim["citations"][0]["fragment_ids"] = [
            claim["obligations"][0]["source_quotes"][0]["fragment_id"]
        ]
        return value

    out = GenerationService(
        Script(
            [
                answer("Carbon dioxide supplies carbon for sugar. [ev_001]"),
                mismatched_quote,
                corrected,
            ]
        )
    ).generate(req(source_relation_policy=VERSION), RequestBudget(max_calls=3))
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 3
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    support = out.checks[-1]["source_relation_assessment"]["claims"][0]["obligations"][0][
        "source_quotes"
    ][0]["fragment_id"]
    highlights = {
        fid
        for view in out.delivered_projection["citation_views"]
        for segment in view["segments"]
        if segment["highlight"]
        for fid in segment["fragment_ids"]
    }
    assert highlights == {support}


def test_missing_new_fields_cannot_be_accepted_as_the_old_schema():
    def old_shape(messages):
        return checker(messages)

    adapter = Script([answer(), old_shape])
    out = GenerationService(adapter).generate(
        req(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    typed = checker(adapter.calls[1][0])
    ReliableCheckV5.model_validate(typed)
    with pytest.raises(ValidationError):
        ReliableRelationCheck.model_validate(typed)


@pytest.mark.parametrize(
    "policy,reliability,code",
    [
        ("unknown", "evidence_reliability_v5", "UNKNOWN_SOURCE_RELATION_POLICY"),
        (VERSION, "evidence_reliability_v4", "SOURCE_RELATION_POLICY_INCOMPATIBLE"),
    ],
)
def test_unknown_or_incompatible_policy_fails_before_any_call(policy, reliability, code):
    adapter = Script([])
    out = GenerationService(adapter).generate(
        request(source_relation_policy=policy, reliability_policy=reliability)
    )
    assert out.response is None and out.error["code"] == code and not adapter.calls


def negative_second(messages):
    value = relation_checker(messages)
    value["claims"][1]["obligations"][0].update(status="unsupported", relation_preserved=False)
    return value


def relation_patch(messages):
    assert "SOURCE RELATION REPAIR V1" in messages[-1]["content"]
    data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
    assert data["source_relation_assessment"]["semantic_defect_codes"]
    protected = {row["claim_id"] for row in data["protected_exact_claims"]}
    return {
        "edits": [
            {
                "claim_id": row["claim_id"],
                "replacement_text": "Carbon dioxide supplies carbon for sugar. [ev_001]",
            }
            for row in data["original_claims"]
            if row["claim_id"] not in protected
        ],
        "append_answer_text": "",
    }


def compound_answer():
    return answer(
        "Photosynthesis uses light energy. [ev_001] Carbon dioxide supplies carbon for sugar and that sugar is stored as a gas. [ev_001]"
    )


def test_negative_atomic_unit_routes_directly_to_local_repair_and_full_final_recheck():
    adapter = Script([compound_answer(), negative_second, relation_patch, relation_checker])
    out = GenerationService(adapter).generate(
        req(source_relation_policy=VERSION, repair_policy=REPAIR_VERSION)
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert (
        out.response["answer_text"]
        == "Photosynthesis uses light energy. [ev_001] Carbon dioxide supplies carbon for sugar. [ev_001]"
    )
    assert not out.checks[0]["checker_inconsistencies"]
    assert out.checks[0]["typed_judgment_raw_aliases"]["claims"][1]["status"] == "supported"
    assert not out.checks[0]["source_relation_assessment"]["accepted"]
    assert out.checks[1]["source_relation_assessment"]["accepted"]


def test_persistent_negative_atomic_unit_cannot_publish_after_repair():
    out = GenerationService(
        Script([compound_answer(), negative_second, relation_patch, negative_second])
    ).generate(req(source_relation_policy=VERSION, repair_policy=REPAIR_VERSION))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4


@pytest.mark.parametrize("field", ["answer_text", "short_answer"])
def test_body_and_summary_both_receive_relation_support_checks(field):
    response = answer(short_answer="Photosynthesis uses light energy. [ev_001]")

    def negative(messages):
        data = check_input(messages)
        value = relation_checker(messages)
        ids = {row["claim_id"] for row in data["CLAIMS"] if row["answer_field"] == field}
        for row in value["claims"]:
            if row["claim_id"] in ids:
                row["obligations"][0]["conditions_preserved"] = False
        return value

    out = GenerationService(Script([response, negative])).generate(
        req(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert (
        "SOURCE_CONDITION_CHANGED"
        in out.token_budget["source_relation_support"]["semantic_defect_codes"]
    )


def test_named_partial_context_can_publish_supported_portions_without_full_coverage_override():
    def partial(messages):
        value = relation_checker(
            messages,
            coverage="supported_partial",
            missing_facets=["direction"],
            limitations_explicit=True,
        )
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="partial",
            missing_information="The requested direction is absent.",
        )
        return value

    out = GenerationService(Script([answer(), partial])).generate(
        req(source_relation_policy=VERSION)
    )
    assert out.succeeded, out.error
    assert out.token_budget["context_coverage"]["semantic_sufficiency"]["status"] == "partial"
    assert out.token_budget["answer_completeness"]["status"] == "partial"
    assert out.token_budget["source_relation_support"]["accepted"]


def test_partial_context_claiming_complete_coverage_still_fails():
    def contradictory(messages):
        value = relation_checker(
            messages, coverage="supported_partial", missing_facets=["direction"]
        )
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="covered",
            missing_information="The requested direction is absent.",
        )
        return value

    out = GenerationService(Script([answer(), contradictory])).generate(
        req(source_relation_policy=VERSION), RequestBudget(max_calls=2)
    )
    assert out.response is None
    assert "INSUFFICIENT_CONTEXT_FULL_COVERAGE" in json.dumps(out.checks)


def test_legacy_schema_and_prompt_do_not_change_when_marker_is_absent():
    adapter = Script([answer(), checker])
    out = GenerationService(adapter).generate(req())
    assert out.succeeded
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v5"
    assert "SOURCE RELATION CONTRACT V1" not in adapter.calls[1][0][0]["content"]
    assert "SOURCE_RELATION_POLICY" not in check_input(adapter.calls[1][0])
    assert "source_relation_support" not in out.token_budget


@pytest.mark.parametrize(
    "policy,expected", [(None, "context_coverage_v3"), (VERSION, "context_coverage_v4")]
)
def test_relational_coverage_is_selected_only_for_new_opt_in_current_commands(policy, expected):
    adapter = Script([answer(), relation_checker if policy else checker])
    out = GenerationService(adapter).generate(
        req(source_relation_policy=policy, generation_policy=freeze_generation_policy())
    )
    assert out.succeeded, out.error
    assert out.token_budget["context_coverage"]["version"] == expected


def test_plain_mock_stays_explicitly_unverified_under_opt_in_contract():
    out = GenerationService().generate(req(source_relation_policy=VERSION))
    assert out.succeeded
    assert "source_relation_support" not in out.token_budget
    assert out.attribution["check_state"] == "unverified_mock_direct"
