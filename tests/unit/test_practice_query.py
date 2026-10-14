"""Instruction-only practice turns retrieve their actual, learner-visible problem."""

import json
import pytest
from conversation.practice_context import VERSION, freeze_policy, resolve
from conversation.query import VERSION as PREPARER, prepare_query


def context(**changes):
    practice = {
        "version": "practice_tutor_context_v1",
        "item_id": "owned-item",
        "progress_version": 2,
        "current_step": 1,
        "prompt": "What energy source do photosynthetic organisms require?",
        "conditions": ["Use the selected textbook passage."],
        "concepts": ["photosynthesis"],
        "source": {"source_unit_id": "authorized-source"},
        "private_rubric": {"correct_option_ids": ["PRIVATE_SENTINEL"]},
        **changes,
    }
    return {"practice_context": practice, "turn_role": "user_question"}


def projection(question, teaching):
    return resolve(
        question,
        prepare_query(question, [], version=PREPARER).model_dump(),
        teaching,
        policy=VERSION,
        preparation_version=PREPARER,
    )


def test_generic_hint_resolves_public_problem_retains_literal_instruction_and_no_key():
    question = "Help me with the current practice step without giving the answer."
    prepared, requirements = projection(question, context())
    assert prepared["original_message"] == requirements["original_message"] == question
    assert "photosynthetic organisms" in prepared["standalone_query"]
    assert question in prepared["standalone_query"]
    resolution = requirements["practice_reference_resolution"]
    assert resolution["request_role"] == "teaching_instruction"
    assert resolution["learner_request_constraints"]["negation"][0]["text"] == "without"
    assert all("Help me" not in point["request"] for point in requirements["required_knowledge"])
    assert "PRIVATE_SENTINEL" not in json.dumps((prepared, requirements))
    assert not prepared["needs_clarification"]


def test_current_step_and_real_given_conditions_survive_substantive_request():
    question = "Explain what happens without light at 25 C."
    teaching = context(
        current_step=2,
        current_step_prompt="Explain how energy is stored in sugars.",
        conditions=["Assume 25 C and no added energy."],
    )
    prepared, requirements = projection(question, teaching)
    assert "stored in sugars" in prepared["standalone_query"]
    assert "Assume 25 C and no added energy." in prepared["standalone_query"]
    assert question in prepared["standalone_query"]
    resolution = requirements["practice_reference_resolution"]
    assert resolution["current_step"] == 2 and resolution["request_role"] == "knowledge_request"
    assert any("without light" in p["request"] for p in requirements["required_knowledge"])


def test_old_frozen_requests_and_ordinary_questions_have_no_new_projection():
    question = "Help me with this step."
    prepared = prepare_query(question, [], version=PREPARER).model_dump()
    assert freeze_policy(None) is None and freeze_policy({"teaching_mode": "hint"}) is None
    assert freeze_policy(context()) == VERSION
    assert resolve(question, prepared, context(), policy=None, preparation_version=PREPARER) is None
    with pytest.raises(ValueError, match="unavailable"):
        resolve(question, prepared, context(), policy="unknown", preparation_version=PREPARER)


def test_learner_attempt_uses_public_step_instead_of_treating_wrong_answer_as_a_task():
    teaching = {
        **context(current_step_prompt="Identify the energy input."),
        "turn_role": "learner_attempt",
    }
    prepared, requirements = projection("Sound is the energy source.", teaching)
    assert "Sound is the energy source." in prepared["standalone_query"]
    assert requirements["practice_reference_resolution"]["request_role"] == "teaching_instruction"
    assert all("Sound" not in p["request"] for p in requirements["required_knowledge"])
