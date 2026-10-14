"""Factorial isolation and source-preserving display selection on synthetic fixtures."""

from copy import deepcopy
import hashlib

import pytest

from generation.teaching_plan import (
    build_teaching_plan,
    freeze_generation_policy,
    select_display_fragments,
    select_evidence_for_progress,
    validate_generation_policy,
)


def context(**changes):
    return {
        "teaching_mode": "hint",
        "task_type": "simple_calculation",
        "help_level": 1,
        "current_step": 2,
        "current_problem": "Calculate volume at constant temperature without changing the amount of gas.",
        "delivered_turns": [],
        "disclosure_events": [],
        **changes,
    }


def fragment(identity, text, start=0, **changes):
    return {
        "fragment_id": identity,
        "evidence_id": "ev_001",
        "chunk_id": "chunk-1",
        "chunk_start": start,
        "chunk_end": start + len(text),
        "exact_text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "complete_block": True,
        **changes,
    }


@pytest.mark.parametrize(
    "arm,content,display",
    [("A", False, False), ("B", True, False), ("C", False, True), ("D", True, True)],
)
def test_independent_factors_share_the_common_budget(arm, content, display):
    policy = freeze_generation_policy(arm)
    assert policy["content_plan"] is content
    assert policy["display_selection"] is display
    assert policy["max_targeted_retrievals"] == 1
    assert policy["provider_planning_calls"] == 0
    assert validate_generation_policy(policy) == policy


def test_policy_tampering_and_unknown_arms_fail():
    with pytest.raises(ValueError):
        freeze_generation_policy("E")
    with pytest.raises(ValueError):
        validate_generation_policy({**freeze_generation_policy("A"), "display_selection": True})


def test_direct_questions_keep_complete_answer_behavior_for_every_arm():
    for arm in "ABCD":
        plan = build_teaching_plan("Explain osmosis.", {}, policy=freeze_generation_policy(arm))
        assert plan["enabled"] is False
        assert plan["action"] == "complete_explanation"
        assert plan["allowed_disclosure"]["complete_answer_allowed"] is True
        selected, audit = select_display_fragments([], [], plan)
        assert selected is None and audit["applied"] is False


def test_attempt_retains_original_conditions_and_step_without_mastery_judgment():
    state = context(
        turn_role="learner_attempt",
        pending_tutor_question="Which quantity stays fixed?",
        expected_response_kind="concept",
    )
    before = deepcopy(state)
    plan = build_teaching_plan("The temperature?", state)
    assert state == before
    assert plan["original_problem"] == state["current_problem"]
    assert plan["current_step"] == 2
    assert plan["action"] == "check_understanding"
    assert plan["expected_learner_reply"]["kind"] == "concept"
    assert plan["mastery_inference"] is None
    assert plan["allowed_disclosure"]["complete_answer_allowed"] is False


@pytest.mark.parametrize(
    "level,action", [(1, "recall_concept"), (2, "split_step"), (3, "check_understanding")]
)
def test_next_action_follows_frozen_help_level(level, action):
    plan = build_teaching_plan("Another hint.", context(help_level=level))
    assert plan["action"] == action
    assert plan["allowed_disclosure"]["help_level"] == level


def test_error_location_requires_explicit_request_and_remains_conditional():
    plan = build_teaching_plan("Please locate my mistake.", context())
    assert plan["action"] == "locate_error"
    assert "only when the evidence establishes" in plan["action_instruction"]


def test_exposure_identity_tracks_previous_source_display_without_copying_it():
    state = context(
        delivered_turns=[
            {"citation_views": [{"fragment_ids": ["shown"], "preview": "Already disclosed."}]}
        ]
    )
    plan = build_teaching_plan("Another hint.", state)
    changed = deepcopy(state)
    changed["disclosure_events"].append(
        {"kind": "full_source", "payload": {"text": "A longer source."}}
    )
    assert plan["previously_exposed_fragment_ids"] == ["shown"]
    assert (
        plan["exposure_snapshot_hash"]
        != build_teaching_plan("Another hint.", changed)["exposure_snapshot_hash"]
    )
    assert "Already disclosed." not in str(plan)


def test_display_selection_changes_only_visible_whole_blocks_and_retains_qualification():
    blocks = [
        fragment("f1", "Pressure is a useful quantity."),
        fragment("f2", "Temperature stays constant.", 40),
        fragment("f3", "However, the amount of gas must stay fixed.", 80),
    ]
    claim = {
        "claim_id": "c1",
        "text": "Consider the constant temperature.",
        "evidence_ids": ["ev_001"],
    }
    before = deepcopy(blocks)
    for arm in "AB":
        selected, audit = select_display_fragments(
            blocks,
            [claim],
            build_teaching_plan("Hint", context(), policy=freeze_generation_policy(arm)),
        )
        assert selected is None and not audit["applied"]
    for arm in "CD":
        selected, audit = select_display_fragments(
            blocks,
            [claim],
            build_teaching_plan("Hint", context(), policy=freeze_generation_policy(arm)),
        )
        assert selected == {"c1": ["f2", "f3"]}
        assert audit["decisions"][0]["qualification_fragment_ids"] == ["f3"]
        assert audit["disclosure_verified"] is None
    assert blocks == before
    evidence = [{"text": "Exact original text.", "chunk_id": "immutable"}]
    assert select_evidence_for_progress(evidence, {})[0] == evidence


def test_required_claim_bindings_and_actual_citation_identity_are_preserved():
    blocks = [
        fragment("required", "First valid support."),
        fragment("preferred", "Temperature stays constant.", 50),
    ]
    claim = {"claim_id": "c1", "text": "Temperature stays constant.", "evidence_ids": ["ev_001"]}
    plan = build_teaching_plan("Hint", context())
    selected, _ = select_display_fragments(blocks, [claim], plan, {"c1": ["required"]})
    assert selected == {"c1": ["required"]}
    with pytest.raises(ValueError, match="BINDING_UNAVAILABLE"):
        select_display_fragments(
            blocks, [{**claim, "evidence_ids": ["ev_002"]}], plan, {"c1": ["required"]}
        )


def test_incomplete_blocks_cannot_be_added_to_controlled_display():
    blocks = [fragment("partial", "Only if", complete_block=False)]
    selected, _ = select_display_fragments(
        blocks,
        [{"claim_id": "c1", "text": "Only if", "evidence_ids": ["ev_001"]}],
        build_teaching_plan("Hint", context()),
    )
    assert selected == {"c1": []}
