"""Offline permissions replay; compilation is never a teaching-quality verdict."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from generation.parser import ResponseValidationError
from generation.reliability_v4 import unchanged_claims
from generation.repair_patch_v1 import (
    VERSION,
    build_bound_repair_plan,
    compile_bound_repair_patch,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "structured_repair"
S11_TARGET = "claim_fa5278fe54c87f6f68faca7b_1"
G01_TARGET = "claim_bc41123b60c7a9ab968ce8f1_1"
G01_QUESTION = "claim_66efad041dd4004c4c8a1b44_1"
S11_REPLACEMENT = "Consider the stated process: constant temperature and fixed amount of gas."
G01_REPLACEMENT = "The stated goal is to isolate x while preserving equality."


def saved_case(name="g01_actual18"):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def concrete_plan(case):
    """Select recorded claim defects only, retaining the full original in the fixture.

    A permission replay does not remove failed flags from a checker judgment or
    declare the unresolved global issues fixed.
    """
    value = deepcopy(case["repair_plan"])
    value["actions"] = [row for row in value["actions"] if row.get("claim_id")]
    return value


def build(case, actions=None):
    return build_bound_repair_plan(
        case["draft"],
        case["claims"],
        case["protected"],
        concrete_plan(case) if actions is None else actions,
        request_binding=case["request_binding"],
        selection_contract=case["selection_contract"],
        projection=case["projection"],
    )


def proposal(plan, target=G01_TARGET, replacement=G01_REPLACEMENT):
    return {
        "version": VERSION,
        **{
            key: plan[key]
            for key in (
                "plan_sha256",
                "base_sha256",
                "request_sha256",
                "selection_sha256",
                "projection_sha256",
            )
        },
        "edits": [{"target_id": target, "replacement_text": replacement}],
    }


def compile_patch(case, patch, plan, actions=None):
    return compile_bound_repair_patch(
        case["draft"],
        case["claims"],
        case["protected"],
        patch,
        case["evidence_ids"],
        plan=plan,
        request_binding=case["request_binding"],
        selection_contract=case["selection_contract"],
        projection=case["projection"],
        repair_plan=concrete_plan(case) if actions is None else actions,
    )


def rejects(operation, expected=None):
    with pytest.raises(ResponseValidationError) as caught:
        operation()
    if expected is not None:
        assert caught.value.code == expected
    return caught.value.code


@pytest.mark.parametrize(
    ("name", "source_sha", "protected_text"),
    [
        (
            "s11_actual17",
            "f71242b43193872673046dcbd86c6c2ef73f7daec4375dbbc5e2c8aa270a4a17",
            "Would the supplied candidate fit this problem, what in those two conditions "
            "supports your judgment, and why should you establish that fit before "
            "deciding whether to use it?",
        ),
        (
            "g01_actual18",
            "57a0a62755cf331383f96dcc4e2f678a0b890c582e5bd554065b42101d129b4c",
            "The equation is 5x - 4 = 21.",
        ),
    ],
)
def test_saved_cases_bind_original_sources_and_keep_failed_outcomes(
    name, source_sha, protected_text
):
    case = saved_case(name)
    assert case["source_artifacts"][0]["sha256"] == source_sha
    assert "/drafts/0/response" in case["source_artifacts"][0]["json_pointers"]
    assert case["protected"][0]["text"] == protected_text
    assert case["saved_error"]["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert not unchanged_claims(case["protected"], case["saved_full_repair"])
    assert case["recorded_acceptance_unchanged"]["native_response"] is None
    assert case["recorded_acceptance_unchanged"]["human_rating"] is None
    assert not case["recorded_acceptance_unchanged"]["native_published"]
    assert all(row["role"] == "user" for row in case["request_binding"]["user_messages"])


@pytest.mark.parametrize(
    ("name", "target", "replacement"),
    [
        ("s11_actual17", S11_TARGET, S11_REPLACEMENT),
        ("g01_actual18", G01_TARGET, G01_REPLACEMENT),
    ],
)
def test_saved_defect_splice_retains_all_other_text_and_protected_content(
    name, target, replacement
):
    case = saved_case(name)
    original = deepcopy(case)
    plan = build(case)
    compiled, receipt = compile_patch(case, proposal(plan, target, replacement), plan)
    span = next(row for row in case["claims"] if row["claim_id"] == target)
    text = case["draft"]["answer_text"]
    assert compiled["answer_text"] == text[: span["start"]] + replacement + text[span["end"] :]
    assert unchanged_claims(case["protected"], compiled)
    assert compiled["answer_text"].count(case["protected"][0]["text"]) == 1
    assert compiled["citations"] == []
    assert receipt["requires_full_check"] is True
    assert receipt["source_entailment_certified"] is False
    assert case == original
    if name == "s11_actual17":
        assert compiled["tutor_question"]["question"] == compiled["answer_text"]
        assert (
            "constant temperature and fixed amount of gas"
            in case["request_binding"]["teaching_context"]["current_problem"]
        )
    else:
        assert compiled["tutor_question"] == case["draft"]["tutor_question"]
    assert compiled["learner_attempt_evaluation"] == case["draft"]["learner_attempt_evaluation"]


@pytest.mark.parametrize(
    ("target", "error"),
    [
        ("not-an-original-claim", "BOUND_REPAIR_UNKNOWN_TARGET"),
        ("claim_94fdda7a415771f7782931c6_1", "BOUND_REPAIR_UNKNOWN_TARGET"),
        ("claim_1963131a69208ae6a8cc3a6a_1", "BOUND_REPAIR_PROTECTED_EDIT"),
    ],
)
def test_model_cannot_select_unknown_unlisted_or_protected_claims(target, error):
    case = saved_case()
    plan = build(case)
    rejects(lambda: compile_patch(case, proposal(plan, target), plan), error)


@pytest.mark.parametrize(
    "key",
    ["base_sha256", "request_sha256", "selection_sha256", "projection_sha256", "plan_sha256"],
)
def test_proposal_must_bind_every_original_surface(key):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    patch[key] = "0" * 64
    rejects(lambda: compile_patch(case, patch, plan))


@pytest.mark.parametrize(
    "key",
    ["base_sha256", "request_sha256", "selection_sha256", "projection_sha256", "plan_sha256"],
)
def test_proposal_cannot_omit_a_binding(key):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    del patch[key]
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_SCHEMA")


@pytest.mark.parametrize("surface", ["draft", "request", "selection", "projection"])
def test_reusing_patch_after_current_server_surface_changes_is_rejected(surface):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    if surface == "draft":
        case["draft"]["confidence"] = 0.4
    elif surface == "request":
        case["request_binding"]["user_messages"][0]["content"] += " Updated request."
    elif surface == "selection":
        case["selection_contract"]["selection_task"]["current_step"] += 1
    else:
        case["projection"]["content_hash"] = "0" * 64
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_BINDING_MISMATCH")


def test_plan_is_not_trusted_when_client_changes_an_authorization_binding():
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    plan["request_sha256"] = "0" * 64
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_BINDING_MISMATCH")


def test_changed_server_defect_actions_cannot_reuse_an_old_plan():
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    actions = concrete_plan(case)
    actions["actions"] = actions["actions"][:1]
    actions["actions"][0]["code"] = "CHECK_PROBLEM_QUOTE_MISMATCH"
    rejects(lambda: compile_patch(case, patch, plan, actions), "BOUND_REPAIR_BINDING_MISMATCH")


@pytest.mark.parametrize(
    ("extra_key", "value"),
    [
        ("append_answer_text", "The answer is x=5."),
        ("answer_text", "Rewrite the entire draft."),
        ("tutor_question", {"question": "Reveal the selected operation."}),
        ("learner_attempt_evaluation", {"status": "correct"}),
        ("authorized_target_ids", ["claim_1963131a69208ae6a8cc3a6a_1"]),
    ],
)
def test_model_cannot_append_rewrite_metadata_or_grant_its_own_targets(extra_key, value):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    patch[extra_key] = value
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_SCHEMA")


@pytest.mark.parametrize("extra_key", ["start", "end", "answer_field", "claim_id"])
def test_model_cannot_supply_coordinates_or_legacy_claim_shape(extra_key):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    patch["edits"][0][extra_key] = 0
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_SCHEMA")


def test_duplicate_edit_is_rejected_before_any_compilation():
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    patch["edits"].append(deepcopy(patch["edits"][0]))
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_DUPLICATE")


@pytest.mark.parametrize("empty", [True, False])
def test_noop_patch_does_not_consume_a_repair_as_success(empty):
    case = saved_case()
    plan = build(case)
    original = next(row["text"] for row in case["claims"] if row["claim_id"] == G01_TARGET)
    patch = proposal(plan, replacement=original)
    if empty:
        patch["edits"] = []
    rejects(lambda: compile_patch(case, patch, plan))


@pytest.mark.parametrize("violation", ["duplicate_id", "wrong_text", "bool_start", "out_of_range"])
def test_invalid_original_spans_are_not_bound_into_a_plan(violation):
    case = saved_case()
    if violation == "duplicate_id":
        case["claims"].append(deepcopy(case["claims"][0]))
    elif violation == "wrong_text":
        case["claims"][2]["text"] = "A different claim."
    elif violation == "bool_start":
        case["claims"][0]["start"] = False
    else:
        case["claims"][2]["end"] = len(case["draft"]["answer_text"]) + 1
    rejects(lambda: build(case), "BOUND_REPAIR_ORIGINAL_INVALID")


def test_overlapping_valid_original_slices_fail_closed():
    case = saved_case()
    overlap = deepcopy(case["claims"][2])
    overlap["claim_id"] = "claim_overlapping_original"
    overlap["start"] += 1
    overlap["text"] = case["draft"]["answer_text"][overlap["start"] : overlap["end"]]
    case["claims"].append(overlap)
    rejects(lambda: build(case), "BOUND_REPAIR_SPAN_OVERLAP")


def test_a_changed_protected_record_cannot_relax_approval():
    case = saved_case()
    case["protected"][0]["text"] = "The equation is 5x - 4 = 20."
    rejects(lambda: build(case), "BOUND_REPAIR_PROTECTED_INVALID")


@pytest.mark.parametrize("actions", [[], [{"origin": "answer", "code": "INCOMPLETE_REQUEST"}]])
def test_unlocatable_global_defect_never_grants_the_whole_draft(actions):
    case = saved_case()
    plan = deepcopy(case["repair_plan"])
    plan["actions"] = actions
    rejects(lambda: build(case, plan), "BOUND_REPAIR_UNMAPPABLE")


def test_specific_patch_derives_known_citation_list_without_certifying_entailment():
    case = saved_case()
    plan = build(case)
    compiled, receipt = compile_patch(
        case, proposal(plan, replacement=G01_REPLACEMENT + " [ev_001]"), plan
    )
    assert compiled["citations"] == ["ev_001"]
    assert unchanged_claims(case["protected"], compiled)
    assert receipt["requires_full_check"] is True
    assert receipt["source_entailment_certified"] is False


def test_unknown_citation_is_rejected_by_reused_claim_compiler():
    case = saved_case()
    plan = build(case)
    rejects(
        lambda: compile_patch(
            case, proposal(plan, replacement=G01_REPLACEMENT + " [ev_999]"), plan
        ),
        "CLAIM_PATCH_SOURCE_UNKNOWN",
    )


def test_explicit_recorded_question_defect_synchronizes_visible_text_and_metadata():
    case = saved_case()
    actions = deepcopy(case["repair_plan"])
    actions["actions"] = [
        row for row in actions["actions"] if row["code"] == "TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER"
    ]
    plan = build(case, actions)
    replacement = "Does that hypothesis fit the visible structure before a first step?"
    compiled, receipt = compile_patch(
        case, proposal(plan, G01_QUESTION, replacement), plan, actions
    )
    old = case["draft"]["tutor_question"]["question"]
    old_claim = next(row for row in case["claims"] if row["claim_id"] == G01_QUESTION)
    assert compiled["tutor_question"]["question"] == old.replace(old_claim["text"], replacement)
    assert compiled["tutor_question"]["question"] in compiled["answer_text"]
    assert compiled["tutor_question"]["expected_response_kind"] == "explanation"
    assert compiled["citations"] == []
    assert unchanged_claims(case["protected"], compiled)
    assert receipt["requires_full_check"] is True


def test_invisible_teaching_question_cannot_receive_a_silent_append_or_sync():
    case = saved_case()
    case["draft"]["tutor_question"]["question"] = "An invisible unrelated question?"
    rejects(lambda: build(case), "BOUND_REPAIR_METADATA_BINDING")


def test_ambiguous_visible_question_is_rejected_instead_of_guessing_a_span():
    case = saved_case()
    case["draft"]["answer_text"] += " " + case["draft"]["tutor_question"]["question"]
    case["projection"]["response"]["answer_text"] = case["draft"]["answer_text"]
    rejects(lambda: build(case), "BOUND_REPAIR_METADATA_AMBIGUOUS")


def test_partial_question_claim_cannot_grant_a_cross_boundary_replacement():
    case = saved_case()
    case["draft"]["tutor_question"]["question"] = case["draft"]["answer_text"][310:513]
    actions = deepcopy(case["repair_plan"])
    actions["actions"] = [
        row for row in actions["actions"] if row["code"] == "TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER"
    ]
    rejects(lambda: build(case, actions), "BOUND_REPAIR_UNMAPPABLE")


@pytest.mark.parametrize("key", ["start", "end", "original_text", "original_sha256"])
def test_server_target_span_cannot_be_modified_even_with_matching_proposal_hashes(key):
    case = saved_case()
    plan = build(case)
    patch = proposal(plan)
    target = next(row for row in plan["targets"] if row["target_id"] == G01_TARGET)
    if key == "start":
        target[key] += 1
    elif key == "end":
        target[key] -= 1
    elif key == "original_text":
        target[key] = "A forged original."
    else:
        target[key] = "0" * 64
    rejects(lambda: compile_patch(case, patch, plan), "BOUND_REPAIR_PLAN_INVALID")


def test_claim_edit_also_synchronizes_bound_attempt_feedback_without_changing_status():
    case = saved_case()
    text = next(row["text"] for row in case["claims"] if row["claim_id"] == G01_TARGET)
    case["draft"]["learner_attempt_evaluation"] = {"status": "incorrect", "feedback": text}
    plan = build(case)
    compiled, receipt = compile_patch(case, proposal(plan), plan)
    assert compiled["learner_attempt_evaluation"] == {
        "status": "incorrect",
        "feedback": G01_REPLACEMENT,
    }
    assert compiled["tutor_question"] == case["draft"]["tutor_question"]
    assert receipt["metadata_updates"][0]["surface"] == "learner_attempt_evaluation"
    assert unchanged_claims(case["protected"], compiled)


def test_overlapping_question_and_feedback_bindings_are_rejected():
    case = saved_case()
    case["draft"]["learner_attempt_evaluation"] = {
        "status": "incorrect",
        "feedback": case["draft"]["tutor_question"]["question"],
    }
    rejects(lambda: build(case), "BOUND_REPAIR_METADATA_OVERLAP")


def test_concrete_claim_cannot_cross_an_existing_metadata_boundary():
    case = saved_case()
    text = next(row["text"] for row in case["claims"] if row["claim_id"] == G01_TARGET)
    case["draft"]["learner_attempt_evaluation"] = {"status": "incorrect", "feedback": text[4:]}
    rejects(lambda: build(case), "BOUND_REPAIR_METADATA_CROSS_BOUNDARY")


def test_global_question_defect_cannot_unlock_a_protected_part_of_the_surface():
    case = saved_case("s11_actual17")
    # This actual complete-hint completion action would include the protected
    # second sentence. It cannot authorize a full question replacement.
    rejects(lambda: build(case, case["repair_plan"]), "BOUND_REPAIR_UNMAPPABLE")


def test_deferred_global_source_action_remains_unresolved_without_expanding_targets():
    case = saved_case()
    actions = concrete_plan(case)
    global_source = next(
        row
        for row in case["repair_plan"]["actions"]
        if row["code"] == "REQUIREMENT_LIMITATION_MISSING"
    )
    actions["actions"].append(deepcopy(global_source))
    plan = build(case, actions)
    assert [row["target_id"] for row in plan["targets"]] == [G01_TARGET]
    compiled, receipt = compile_patch(case, proposal(plan), plan, actions)
    assert receipt["deferred_source_actions"] == [
        {key: global_source[key] for key in ("origin", "code", "action")}
    ]
    assert receipt["requires_full_check"] is True
    assert receipt["publication_override"] is False
    assert unchanged_claims(case["protected"], compiled)


def test_summary_source_cannot_be_detached_from_the_compiled_body():
    case = saved_case()
    short = "Given equation. [ev_001]"
    case["draft"]["short_answer"] = short
    case["claims"].append(
        {
            "claim_id": "claim_test_summary_binding",
            "answer_field": "short_answer",
            "start": 0,
            "end": len(short),
            "text": short,
            "evidence_ids": ["ev_001"],
            "fragment_ids": [],
        }
    )
    case["projection"]["response"]["short_answer"] = short
    plan = build(case)
    rejects(lambda: compile_patch(case, proposal(plan), plan), "CLAIM_PATCH_SUMMARY_BINDING")


@pytest.mark.parametrize("surface", ["request_binding", "projection"])
@pytest.mark.parametrize("missing", [None, {}])
def test_absent_trusted_request_or_projection_cannot_be_replaced_by_a_hash_of_null(
    surface, missing
):
    case = saved_case()
    case[surface] = missing
    rejects(lambda: build(case), "BOUND_REPAIR_BINDING_INVALID")


def test_projection_response_must_be_the_frozen_draft_including_citation_fields():
    case = saved_case()
    case["projection"]["response"]["citations"] = ["ev_001"]
    rejects(lambda: build(case), "BOUND_REPAIR_BINDING_INVALID")


def test_patch_cannot_create_a_second_copy_of_the_bound_visible_question():
    case = saved_case()
    plan = build(case)
    duplicate = G01_REPLACEMENT + " " + case["draft"]["tutor_question"]["question"]
    rejects(
        lambda: compile_patch(case, proposal(plan, replacement=duplicate), plan),
        "BOUND_REPAIR_METADATA_AMBIGUOUS",
    )


@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf")])
def test_trusted_binding_hash_cannot_accept_nonfinite_public_data(number):
    case = saved_case()
    case["request_binding"]["invalid_numeric_marker"] = number
    rejects(lambda: build(case), "BOUND_REPAIR_BINDING_INVALID")


def test_invalid_unicode_patch_cannot_be_hashed_or_compiled():
    case = saved_case()
    plan = build(case)
    rejects(
        lambda: compile_patch(case, proposal(plan, replacement="\ud800"), plan),
        "BOUND_REPAIR_SCHEMA",
    )


def test_duplicate_json_key_in_raw_patch_is_rejected():
    case = saved_case()
    plan = build(case)
    raw = json.dumps(proposal(plan))
    raw = raw[:-1] + ', "base_sha256": "' + plan["base_sha256"] + '"}'
    rejects(lambda: compile_patch(case, raw, plan), "DUPLICATE_JSON_KEY")


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e400"])
def test_nonfinite_raw_patch_is_rejected(number):
    case = saved_case()
    plan = build(case)
    raw = json.dumps(proposal(plan))
    raw = raw.replace(
        '"replacement_text": "' + G01_REPLACEMENT + '"', '"replacement_text": ' + number
    )
    rejects(lambda: compile_patch(case, raw, plan))


def test_valid_raw_patch_uses_the_same_bound_compiler():
    case = saved_case("s11_actual17")
    plan = build(case)
    compiled, receipt = compile_patch(
        case, json.dumps(proposal(plan, S11_TARGET, S11_REPLACEMENT)), plan
    )
    assert unchanged_claims(case["protected"], compiled)
    assert compiled["tutor_question"]["question"] == compiled["answer_text"]
    assert receipt["requires_full_check"] is True
