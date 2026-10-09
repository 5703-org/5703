"""Authored pipeline tests; semantic fixtures are not independent quality labels."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from conversation.requirements import describe_requirements
from contracts.models import ChatMessageCreate
from generation import GenerationService, RequestBudget
from generation.adapters import chat_value
from generation.checker_contract import schema_issue
from generation.checker_encoding import decode
from generation.coverage_v2 import assess_evidence_coverage, supplement_once
from generation.reliability_v5 import ReliableCheckV5, pessimistic_body_contract_issues
from generation.repair_context import compact_source_text, restore_source_text
from generation.source_view_repair import plan_source_view_refinement
from generation.teaching_plan_v2 import build_teaching_plan, freeze_generation_policy
from retrieval.source_spans import text_hash
from test_enhancement_generation import Script, answer, request
from test_teaching_contracts_v4 import check as v4_check


def req(**values):
    return request(reliability_policy="evidence_reliability_v5", **values)


def checker(messages, **changes):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data["SOURCE_FRAGMENT_TABLE"]
        data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
    clean = [{"role": "user", "content": json.dumps(data)}]
    value = v4_check(clean)
    source = data["SOURCE_FRAGMENTS"][0] if data["SOURCE_FRAGMENTS"] else None
    value["requirements"] = [
        {
            "requirement_id": point["id"],
            "relevance": "related",
            "sufficiency": "sufficient" if source else "not_applicable",
            "evidence": [
                {
                    "evidence_id": source["evidence_id"],
                    "fragment_id": source["fragment_id"],
                    "quote": source["exact_text"],
                }
            ]
            if source
            else [],
            "conditions_preserved": True,
            "response_coverage": "covered",
            "missing_information": "",
            "reason": "Authored sufficiency receipt.",
        }
        for point in data["CONTEXT_COVERAGE"]["requirements"]
    ]
    value["non_repetitive_next_action"] = True
    return {**value, **changes}


def run(script, value=None, calls=4):
    return GenerationService(Script(script)).generate(
        value or req(), RequestBudget(max_calls=calls)
    )


def test_requirements_preserve_decimal_negative_units_condition_and_comparison_relation():
    original = "Compare gas A and gas B at 2.5 kPa without heating; explain why pressure changes."
    result = describe_requirements(
        original,
        {
            "standalone_query": "Compare gas A and gas B",
            "intent": "factual",
            "topic_relation": "new_topic",
            "needs_clarification": False,
        },
    )
    assert result["rewrite_audit"]["fallback_to_original"]
    assert result["standalone_query"] == original
    assert result["preserved_constraints"]["quantities_and_units"][0]["text"] == "2.5 kPa"
    assert result["required_knowledge"][0]["relation"] == "compare_both_objects_on_requested_axes"
    assert len(result["required_knowledge"]) == 2


def test_semantic_sufficiency_is_separate_from_lexical_miss_and_actual_claim_support():
    out = run([answer(), checker])
    assert out.succeeded, out.error
    report = out.token_budget["context_coverage"]
    assert report["semantic_sufficiency"]["status"] == "sufficient"
    assert report["semantic_sufficiency"]["independent_evaluation"] is False
    assert out.budget["consumed_calls"] == 2
    assert out.checks[0]["actual_citation_bindings"]
    assert out.token_budget["claim_support"]["version"] == "actual_claim_support_v5"
    assert out.token_budget["claim_support"]["accepted"] is True


@pytest.mark.parametrize("defect", ["quote", "missing_requirement", "wrong_source"])
def test_invalid_requirement_provenance_never_publishes(defect):
    def invalid(messages):
        value = checker(messages)
        if defect == "quote":
            value["requirements"][0]["evidence"][0]["quote"] = "Invented quotation."
        elif defect == "wrong_source":
            value["requirements"][0]["evidence"][0]["evidence_id"] = "ev_999"
        else:
            value["requirements"] = []
        return value

    out = run([answer(), invalid], calls=2)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"


def test_lexically_related_but_semantically_partial_context_requires_honest_limit():
    def partial(messages):
        value = checker(
            messages,
            coverage="supported_partial",
            missing_facets=["direction"],
            limitations_explicit=True,
        )
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="partial",
            missing_information="Transport direction is absent.",
        )
        return value

    out = run([answer(), partial])
    assert out.succeeded, out.error
    assert out.token_budget["answer_completeness"]["status"] == "partial"
    assert out.token_budget["context_coverage"]["semantic_sufficiency"]["status"] == "partial"


def test_full_aggregate_with_named_requirement_gap_rechecks_unchanged_draft():
    def conflicting(messages):
        value = checker(messages, coverage="full", limitations_explicit=True)
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="limitation",
            missing_information="A required mechanism is absent from the supplied context.",
        )
        return value

    def corrected(messages):
        value = conflicting(messages)
        value["coverage"] = "supported_partial"
        value["missing_facets"] = ["required mechanism"]
        return value

    out = run([answer(), conflicting, corrected], calls=3)
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    assert out.checks[0]["checker_inconsistencies"] == [
        {"code": "FULL_COVERAGE_WITH_REQUIREMENT_GAP"}
    ]
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert out.token_budget["answer_completeness"]["status"] == "partial"


def test_persistent_full_aggregate_with_requirement_gap_fails_closed():
    def conflicting(messages):
        value = checker(messages, coverage="full", limitations_explicit=True)
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="limitation",
            missing_information="A required mechanism is absent from the supplied context.",
        )
        return value

    out = run([answer(), conflicting, conflicting], calls=3)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 3


def test_sufficient_source_with_omitted_content_routes_to_answer_repair():
    def omitted(messages):
        value = checker(messages, coverage="full")
        value["requirements"][0]["response_coverage"] = "not_addressed"
        return value

    out = run([answer(), omitted], calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[0]["checker_inconsistencies"] == []
    assert "REQUIRED_CONTENT_OMITTED" in out.token_budget["claim_support"]["structural_issue_codes"]


def test_omitted_condition_routes_to_local_repair_with_same_final_support_gates():
    def lost(messages):
        value = checker(messages)
        value["requirements"][0]["conditions_preserved"] = False
        return value

    out = run([answer(), lost, answer(), checker])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert [r["stage"] for r in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    blocked = run([answer(), lost, answer(), lost])
    assert blocked.response is None and blocked.error["code"] == "SEMANTIC_CHECK_FAILED"


def test_repetition_of_disclosed_answer_is_rejected_even_with_all_fact_gates_true():
    hint = req(teaching_context={"teaching_mode": "hint", "help_level": 1})
    out = run(
        [
            chat_value("answer", "Identify the quantity."),
            lambda m: checker(m, non_repetitive_next_action=False),
        ],
        hint,
        calls=2,
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"


def test_general_knowledge_never_receives_textbook_sufficiency():
    out = run(
        [chat_value("answer", "General knowledge: particles move."), checker],
        req(answer_mode="general_knowledge", evidence=[], source_map={}),
    )
    assert out.succeeded, out.error
    assert (
        out.token_budget["context_coverage"]["semantic_sufficiency"]["status"] == "not_applicable"
    )


def test_teaching_plan_adapts_to_recorded_attempt_and_keeps_direct_default():
    base = {
        "teaching_mode": "hint",
        "help_level": 1,
        "current_step": 2,
        "current_problem": "Explain osmosis.",
        "last_attempt_evaluation": {"status": "partial", "feedback": "Include the direction."},
    }
    assert build_teaching_plan("More help", base)["action"] == "complete_missing_reason"
    assert (
        build_teaching_plan("Water", {**base, "turn_role": "learner_attempt"})["action"]
        == "assess_then_adapt"
    )
    assert build_teaching_plan("Explain osmosis.", None)["action"] == "complete_explanation"
    assert build_teaching_plan("More help", base)["allowed_disclosure"]["help_level"] == 1


def test_single_missing_requirement_triggers_only_one_bounded_supplement():
    calls = []
    rows = [{"chunk_id": "c1", "text": "Water crosses a membrane.", "text_hash": "h"}]

    def retrieve(query, limit):
        calls.append((query, limit))
        return deepcopy(rows)

    final, coverage, trace = supplement_once(
        "Why does osmosis occur?",
        [],
        None,
        freeze_generation_policy(),
        retrieve=retrieve,
        rerank=lambda q, r: r,
        screen=lambda q, r: (r, {}),
        checkpoint=lambda *args: None,
    )
    assert len(calls) == trace["retrieval_passes"] == 1
    assert final == rows and coverage["semantic_sufficiency"] is None


def test_source_presentation_word_does_not_trigger_redundant_subject_lookup():
    rows = [{"chunk_id": "c1", "text": "Photosynthesis captures light energy.", "text_hash": "h"}]
    calls = []
    final, coverage, trace = supplement_once(
        "Show sources for photosynthesis",
        rows,
        None,
        freeze_generation_policy(),
        retrieve=lambda q, limit: calls.append((q, limit)) or rows,
        rerank=lambda q, r: r,
        screen=lambda q, r: (r, {}),
        checkpoint=lambda *args: None,
    )
    assert calls == [] and trace["retrieval_passes"] == 0
    assert final == rows and coverage["semantic_sufficiency"] is None
    requirement = coverage["candidate_coverage"]["requirements"][0]
    assert requirement["request"] == "Show sources for photosynthesis"
    assert requirement["lexical_request"] == "photosynthesis"


def test_source_request_preserves_named_subject_and_its_conditions():
    report = assess_evidence_coverage("Show sources for energy sources without oxygen", [])
    requirement = report["candidate_coverage"]["requirements"][0]
    assert set(requirement["terms"]) == {"energy", "source", "without", "oxygen"}
    assert report["targeted_query"] and report["semantic_sufficiency"] is None
    content_question = assess_evidence_coverage("What are energy sources?", [])
    assert "source" in content_question["candidate_coverage"]["requirements"][0]["terms"]


@pytest.mark.parametrize(
    "context",
    [
        {"scope": "chapter", "document_id": "d"},
        {"scope": "all", "selection": {"start": 0, "end": 1, "text": "x"}},
        {
            "scope": "chapter",
            "document_id": "d",
            "source_unit_id": "u",
            "selection": {"start": 0, "end": 2, "text": "x"},
        },
    ],
)
def test_invalid_reading_scope_or_codepoint_length_is_rejected(context):
    with pytest.raises(ValidationError):
        ChatMessageCreate(content="Explain", reading_context=context)


def test_reading_context_is_optional_and_unicode_codepoints_are_exact():
    assert ChatMessageCreate(content="Explain osmosis.").reading_context is None
    body = ChatMessageCreate(
        content="Explain this",
        reading_context={
            "scope": "chapter",
            "document_id": "d",
            "source_unit_id": "u",
            "selection": {"start": 1, "end": 2, "text": "😀"},
        },
    )
    assert body.reading_context.selection.end == 2


def test_candidate_coverage_keeps_comparison_as_joint_requirement():
    report = assess_evidence_coverage("Compare diffusion and osmosis.", [])
    point = report["candidate_coverage"]["requirements"][0]
    assert point["objects"] == ["diffusion", "osmosis"]
    assert point["intent"] == "comparison"


def test_claim_identity_survives_neighbor_insertions_and_citation_repair():
    from generation.reliability_v5 import response_claims

    first = response_claims({"answer_text": "Water moves. [ev_001]"})[0]
    later = response_claims({"answer_text": "Select a direction. Water moves. [ev_002]"})[1]
    assert first["claim_id"] == later["claim_id"]
    assert first["evidence_ids"] != later["evidence_ids"]


def test_plain_mock_does_not_invent_semantic_sufficiency_or_claim_verification():
    out = GenerationService().generate(req())
    assert out.succeeded
    assert out.token_budget["context_coverage"]["semantic_sufficiency"] is None
    assert "claim_support" not in out.token_budget


def test_sufficient_context_cannot_publish_an_unnecessary_partial_response():
    def underuse(messages):
        value = checker(messages, coverage="supported_partial", missing_facets=["mechanism"])
        value["requirements"][0]["response_coverage"] = "partial"
        return value

    out = run([answer(), underuse], calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert (
        "SUFFICIENT_CONTEXT_UNDERUSED"
        in out.token_budget["claim_support"]["structural_issue_codes"]
    )


def test_repeated_difficulty_changes_action_without_claiming_mastery():
    plan = build_teaching_plan(
        "Another hint",
        {
            "teaching_mode": "hint",
            "help_level": 2,
            "attempt_history": [
                {"status": "incorrect", "feedback": "Revisit direction."},
                {"status": "partial", "feedback": "Include the condition."},
            ],
        },
    )
    assert plan["action"] == "reduce_step" and plan["mastery_inference"] is None
    assert plan["allowed_disclosure"]["help_level"] == 2


def test_rejected_procedural_question_can_be_repaired_with_factual_spans_protected():
    hint = req(teaching_context={"teaching_mode": "hint", "help_level": 1})
    first = chat_value("answer", "Repeat the supplied term.")
    repaired = chat_value("answer", "Choose the quantity needed for the next step.")
    out = run(
        [first, lambda m: checker(m, non_repetitive_next_action=False), repaired, checker], hint
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert out.response["answer_text"] == repaired["answer_text"]


def test_checker_contract_feedback_names_schema_paths_without_returned_values():
    def malformed(messages):
        value = checker(messages)
        value["claims"][0]["reason_detail"] = "UNTRUSTED_INSTRUCTION_DO_NOT_REPEAT"
        del value["requirements"]
        del value["non_repetitive_next_action"]
        return value

    invalid = malformed(
        [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "CLAIMS": [{"claim_id": "sample", "evidence_ids": []}],
                        "SOURCE_FRAGMENTS": [],
                        "ACTUAL_CITATION_BINDINGS": [{"claim_id": "sample", "citations": []}],
                        "CONTEXT_COVERAGE": {"requirements": []},
                        "answer_mode": "textbook",
                    }
                ),
            }
        ]
    )
    with pytest.raises(ValidationError) as error:
        ReliableCheckV5.model_validate(invalid)
    issue = schema_issue(error.value)[0]
    assert issue["code"] == "CHECKER_SCHEMA_INVALID"
    paths = [entry["path"] for entry in issue["field_errors"]]
    assert ["requirements"] in paths
    assert ["non_repetitive_next_action"] in paths
    assert any(path[-1] == "reason_detail" for path in paths)
    assert "UNTRUSTED_INSTRUCTION" not in json.dumps(issue)


def test_malformed_v5_check_gets_one_exact_contract_repair_and_full_recheck():
    def malformed(messages):
        value = checker(messages)
        value["claims"][0]["reason_detail"] = "Extra explanation must not bypass the type."
        del value["requirements"]
        del value["non_repetitive_next_action"]
        return value

    adapter = Script([answer(), malformed, checker])
    out = GenerationService(adapter).generate(req(), RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert [attempt["stage"] for attempt in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    diagnostic = out.checks[0]["checker_inconsistencies"][0]
    assert diagnostic["feedback_version"] == "checker_contract_feedback_v2"
    assert "requirements" in adapter.calls[2][0][-1]["content"]
    assert out.checks[-1]["accepted"] is True


def test_final_recheck_schema_error_stops_at_four_calls_without_publication():
    def needs_repair(messages):
        value = checker(messages)
        value["requirements"][0]["conditions_preserved"] = False
        return value

    def malformed(messages):
        value = checker(messages)
        del value["requirements"]
        return value

    out = run([answer(), needs_repair, answer(), malformed])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == len(out.attempts) == 4
    assert out.attempts[-1]["stage"] == "joint_recheck"
    assert out.checks[-1]["checker_inconsistencies"][0]["field_errors"][0]["path"] == [
        "requirements"
    ]


def test_pessimistic_body_verdict_gets_one_unchanged_draft_recheck():
    def pessimistic(messages):
        return checker(messages, body_ok=False)

    out = run([answer(), pessimistic, checker], calls=3)
    assert out.succeeded, out.error
    assert [attempt["stage"] for attempt in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    assert out.checks[0]["checker_inconsistencies"][0]["code"] == (
        "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED"
    )
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert out.checks[1]["accepted"] is True
    assert out.response == out.drafts[0]["response"]


def test_persistent_pessimistic_body_verdict_fails_closed_without_semantic_repair():
    def pessimistic(messages):
        return checker(messages, body_ok=False)

    out = run([answer(), pessimistic, pessimistic], calls=4)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert [attempt["stage"] for attempt in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    assert out.budget["consumed_calls"] == 3


def test_named_partial_claim_does_not_pay_for_body_contract_recheck():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out = run([answer(), partial], calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert [attempt["stage"] for attempt in out.attempts] == ["generation", "joint_check"]
    assert out.checks[0]["checker_inconsistencies"] == []
    assert pessimistic_body_contract_issues(out.checks[0]["judgment"]) == []


@pytest.mark.parametrize("final_approve", [True, False])
def test_same_source_complete_view_refinement_uses_last_call_for_full_recheck(final_approve):
    source = "Osteoblasts develop into osteocytes. Osteocytes are found in lacunae of bone."
    evidence = {
        "evidence_id": "ev_001",
        "chunk_id": "bone",
        "asset_id": "book",
        "processing_id": "processed",
        "source_title": "Authored bone source fixture",
        "section": "Bone",
        "pages": [7],
        "locator": "Fixture page 7",
        "text": source,
        "text_hash": text_hash(source),
        "context_order": 1,
    }
    mapping = {
        "document_version_id": "book-v1",
        "processing_id": "processed",
        "asset_id": "book",
        "chunk_text": source,
        "chunk_hash": text_hash(source),
        "units": [
            {
                "id": "u1",
                "page": 7,
                "cleaned_text": source,
                "text_hash": text_hash(source),
            }
        ],
        "spans": [
            {
                "unit_id": "u1",
                "page": 7,
                "start": 0,
                "end": len(source),
                "chunk_start": 0,
                "chunk_end": len(source),
            }
        ],
    }
    value = req(
        question="Where is an osteocyte?",
        evidence=[evidence],
        source_map={"bone": mapping},
        teaching_context={"teaching_mode": "hint", "help_level": 1},
        generation_policy=freeze_generation_policy("D"),
    )
    draft = answer("Start with the location: an osteocyte lies in a lacuna [ev_001].")

    def source_mismatch(messages):
        result = checker(messages)
        data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
        if "CHECKER_INPUT_ENCODING" in data:
            data = decode(data)
        fragments = data["SOURCE_FRAGMENTS"]
        replacement = next(f for f in fragments if "lacunae" in f["exact_text"])
        result["claims"][0]["status"] = "partial"
        result["claims"][0]["citations"][0]["relation"] = "irrelevant"
        result["repair_fragment_ids"] = [replacement["fragment_id"]]
        result["body_ok"] = False
        return result

    final_check = checker if final_approve else lambda messages: checker(messages, scope_ok=False)
    adapter = Script([draft, source_mismatch, final_check])
    out = GenerationService(adapter).generate(value, RequestBudget(max_calls=3))
    assert [attempt["stage"] for attempt in out.attempts] == [
        "generation",
        "joint_check",
        "joint_recheck",
    ]
    assert out.drafts[1]["origin"] == "deterministic_source_view"
    assert out.drafts[0]["response"] == out.drafts[1]["response"]
    assert out.checks[0]["repair_method"] == "deterministic_source_view_v1"
    if final_approve:
        assert out.succeeded, out.error
        assert out.response == out.drafts[0]["response"]
        assert "lacunae" in out.delivered_projection["citation_views"][0]["preview"]
        assert "Osteoblasts develop" not in out.delivered_projection["citation_views"][0]["preview"]
        assert out.checks[1]["accepted"] is True
        no_recheck = GenerationService(Script([draft, source_mismatch])).generate(
            value, RequestBudget(max_calls=2)
        )
        assert no_recheck.response is None and no_recheck.error["code"] == "SEMANTIC_CHECK_FAILED"
    else:
        assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert out.checks[1]["accepted"] is False


def test_source_view_refinement_rejects_cross_source_or_incomplete_suggestion():
    candidate = {
        "fragment_id": "new",
        "evidence_id": "ev_001",
        "complete_block": True,
    }
    kwargs = {
        "judgment": {
            "claims": [{"claim_id": "c1", "factual": True, "status": "partial"}],
            "repair_fragment_ids": ["new"],
        },
        "raw_claims": [
            {
                "claim_id": "c1",
                "basis": "textbook",
                "citations": [
                    {
                        "evidence_id": "ev_001",
                        "fragment_ids": ["F001"],
                        "relation": "irrelevant",
                    }
                ],
            }
        ],
        "claims": [{"claim_id": "c1", "evidence_ids": ["ev_001"]}],
        "structural_issues": [{"code": "ACTUAL_CITATION_IRRELEVANT", "claim_id": "c1"}],
        "fragments": [
            {"fragment_id": "old", "evidence_id": "ev_001", "complete_block": True},
            candidate,
        ],
        "aliases": {"F001": "old"},
        "projection": {
            "citation_views": [
                {"evidence_id": "ev_001", "claim_ids": ["c1"], "fragment_ids": ["old"]}
            ]
        },
    }
    assert plan_source_view_refinement(**kwargs)["replacement_fragment_id"] == "new"
    candidate["evidence_id"] = "ev_002"
    assert plan_source_view_refinement(**kwargs) is None
    candidate["evidence_id"] = "ev_001"
    candidate["complete_block"] = False
    assert plan_source_view_refinement(**kwargs) is None
    candidate["complete_block"] = True
    kwargs["raw_claims"][0]["citations"][0]["relation"] = "contradictory"
    assert plan_source_view_refinement(**kwargs) is None
    kwargs["raw_claims"][0]["citations"][0]["relation"] = "irrelevant"
    kwargs["judgment"]["repair_fragment_ids"] = ["new", "old"]
    assert plan_source_view_refinement(**kwargs) is None


def test_repair_source_reference_reconstructs_exact_text_and_falls_back_safely():
    passage = "Water moves only under the stated condition. " * 22 + "Δ"
    selected = [{"evidence_id": "ev_001", "text": "Prefix. " + passage + " Suffix."}]
    messages = [
        {
            "role": "system",
            "content": "CONTEXT_DATA_JSON:\n"
            + json.dumps({"CURRENT_EVIDENCE": selected}, ensure_ascii=False, sort_keys=True),
        }
    ]
    fragment = {"fragment_id": "span_001", "evidence_id": "ev_001", "exact_text": passage}
    original = {"source_repair_candidates": [dict(fragment)], "draft": {"answer_text": "A."}}
    compact, receipt = compact_source_text(original, [fragment], messages, selected)
    assert receipt["encoding"] == "current_evidence_unicode_offsets"
    assert receipt["exact_round_trip_verified"] is True
    assert "exact_text" not in compact["source_repair_candidates"][0]
    assert restore_source_text(compact, messages, selected) == original
    assert passage in messages[0]["content"]
    assert receipt["transmitted_chars"] < receipt["original_chars"]

    ambiguous = [{"evidence_id": "ev_001", "text": passage + passage}]
    ambiguous_messages = [
        {
            "role": "system",
            "content": "CONTEXT_DATA_JSON:\n"
            + json.dumps({"CURRENT_EVIDENCE": ambiguous}, ensure_ascii=False, sort_keys=True),
        }
    ]
    fallback, fallback_receipt = compact_source_text(
        original, [fragment], ambiguous_messages, ambiguous
    )
    assert fallback == original and fallback_receipt["encoding"] == "full_exact_text_v1"
