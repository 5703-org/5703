"""Authored orchestration tests; fake checks are not model-quality acceptance."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget
from generation.repair_patch_v1 import POLICY, VERSION
from test_enhancement_generation import Script
from test_selection_task_pipeline import annotate
from test_teaching_plan_v9 import CASES, data, hint, judgment
from test_teaching_plan_v10 import request


GIVEN = CASES[0]["given"]
OLD_QUESTION = "Which part must you consider before applying anything?"
NEW_QUESTION = (
    "Would the supplied candidate fit the stated conditions, what supports your judgment, "
    "and why check before use?"
)


def failed_question(messages):
    value = judgment(CASES[0])(messages)
    value.update(
        specific_help=True,
        tutor_question_ok=False,
        non_repetitive_next_action=False,
        complete_answer=False,
        reason="Authored bounded question defect, not an independent quality vote.",
    )
    return value


def patch_from_feedback(messages, replacement=NEW_QUESTION):
    feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    plan = feedback["bound_repair_plan"]
    assert plan["requires_full_check"] is True
    assert plan["publication_override"] is False
    assert len(plan["targets"]) == 1
    assert plan["targets"][0]["original_text"] == OLD_QUESTION
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
        "edits": [{"target_id": plan["targets"][0]["target_id"], "replacement_text": replacement}],
    }


def run(final_check=judgment(CASES[0]), proposal=patch_from_feedback, calls=4):
    values = [hint(GIVEN, OLD_QUESTION), failed_question]
    if calls == 4:
        values += [proposal, final_check]
    script = Script(values)
    outcome = GenerationService(script, checker_adapter=script).generate(
        annotate(request(), "supplied"), RequestBudget(max_calls=calls)
    )
    return outcome, script


def test_bound_patch_compiles_then_checks_full_draft_and_preserves_raw_proposal():
    outcome, script = run()
    assert outcome.succeeded, outcome.error
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert script.calls[2][1]["response_schema_name"] == POLICY
    assert outcome.response["answer_text"] == GIVEN + " " + NEW_QUESTION
    assert outcome.response["citations"] == []
    assert outcome.drafts[1]["tutor_question"]["question"] == NEW_QUESTION
    proposed = json.loads(outcome.drafts[1]["raw_model_output"])
    assert proposed == patch_from_feedback(script.calls[2][0])
    assert "answer_text" not in proposed
    transformation = outcome.drafts[1]["precheck_transformations"][-1]
    assert transformation["requires_full_check"] is True
    assert transformation["publication_override"] is False
    assert [row["accepted"] for row in outcome.checks] == [False, True]
    fresh_input = data(script.calls[3][0])
    assert fresh_input["PROPOSED_DELIVERY"]["response"] == outcome.response
    assert GIVEN in fresh_input["PROPOSED_DELIVERY"]["response"]["answer_text"]
    assert fresh_input["TUTOR_QUESTION"]["question"] == NEW_QUESTION
    assert all("bound_repair" not in key for key in outcome.timing)
    assert "precheck_transformations" not in outcome.delivered_projection


@pytest.mark.parametrize(
    "gate",
    ["body_ok", "specific_help", "scope_ok", "tutor_question_ok", "non_repetitive_next_action"],
)
def test_compiled_patch_cannot_override_any_failed_fresh_gate(gate):
    def rejected(messages):
        value = judgment(CASES[0])(messages)
        value[gate] = False
        return value

    outcome, script = run(final_check=rejected)
    assert not outcome.succeeded and outcome.response is None
    assert outcome.delivered_projection == {}
    assert [row["accepted"] for row in outcome.checks] == [False, False]
    assert len(script.calls) == outcome.budget["consumed_calls"] == 4
    assert all(not draft["published"] for draft in outcome.drafts)


def test_invalid_fresh_verdict_is_retained_and_cannot_publish_or_retry_past_budget():
    outcome, script = run(final_check={"claims": []})
    assert not outcome.succeeded and outcome.response is None
    assert outcome.delivered_projection == {}
    assert len(script.calls) == outcome.budget["consumed_calls"] == 4
    assert all(not draft["published"] for draft in outcome.drafts)
    assert outcome.checks[-1]["accepted"] is False
    assert outcome.checks[-1]["validation_state"] == "checker_inconsistent"
    assert outcome.checks[-1]["checker_inconsistencies"]
    assert outcome.error["code"] == "CHECKER_INCONSISTENT"


@pytest.mark.parametrize(
    "attack", ["full_rewrite", "append", "stale", "protected", "unknown", "metadata", "noop"]
)
def test_invalid_patch_does_not_trigger_whole_rewrite_or_skip_reserved_recheck(attack):
    def malicious(messages):
        proposal = patch_from_feedback(messages)
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        if attack == "full_rewrite":
            return hint("Changed original given.", NEW_QUESTION)
        if attack == "append":
            proposal["append"] = "A new unbounded assertion."
        elif attack == "stale":
            proposal["base_sha256"] = "0" * 64
        elif attack == "protected":
            proposal["edits"][0]["target_id"] = feedback["protected_exact_claims"][0]["claim_id"]
        elif attack == "unknown":
            proposal["edits"][0]["target_id"] = "invented_target"
        elif attack == "metadata":
            proposal["tutor_question"] = {"question": NEW_QUESTION}
        elif attack == "noop":
            proposal["edits"][0]["replacement_text"] = OLD_QUESTION
        return proposal

    outcome, script = run(proposal=malicious)
    assert not outcome.succeeded and outcome.response is None
    assert outcome.delivered_projection == {}
    assert len(script.calls) == outcome.budget["consumed_calls"] == 3
    assert outcome.budget["format_repairs"] == 0
    assert len(outcome.checks) == 1 and outcome.checks[0]["accepted"] is False
    assert all(not draft["published"] for draft in outcome.drafts)
    assert outcome.error["code"].startswith("BOUND_REPAIR_")


def test_repair_does_not_start_without_budget_for_the_full_fresh_checker():
    outcome, script = run(calls=3)
    assert not outcome.succeeded and outcome.response is None
    assert len(script.calls) == outcome.budget["consumed_calls"] == 2
    assert len(outcome.drafts) == 1 and not outcome.drafts[0]["published"]
    assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert outcome.error["details"]["publication_block"]["stop_reason"] == (
        "insufficient_calls_for_repair_and_recheck"
    )


def test_unlocated_global_defect_stops_without_authorizing_all_claims():
    def unknown_location(messages):
        value = failed_question(messages)
        value["scope_ok"] = False
        return value

    script = Script([hint(GIVEN, OLD_QUESTION), unknown_location])
    outcome = GenerationService(script, checker_adapter=script).generate(
        annotate(deepcopy(request()), "supplied"), RequestBudget(max_calls=4)
    )
    assert not outcome.succeeded and outcome.response is None
    assert outcome.delivered_projection == {}
    assert len(script.calls) == outcome.budget["consumed_calls"] == 2
    assert outcome.error["code"] == "BOUND_REPAIR_UNMAPPABLE"
    assert outcome.checks[0]["accepted"] is False
