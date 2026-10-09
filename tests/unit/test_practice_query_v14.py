"""New query policy preserves public practice context and private-key boundaries."""

import json

import pytest

from conversation import query_v14, query_v15, query_v16
from conversation.practice_context import VERSION, resolve


@pytest.mark.parametrize("preparer", [query_v14, query_v15, query_v16])
def test_versioned_practice_hint_uses_public_conditions_and_keeps_private_rubric_out(preparer):
    literal = "Help me with the current practice step without giving the answer."
    teaching = {
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "item_id": "owned-step",
            "progress_version": 2,
            "current_step": 1,
            "prompt": "Describe the energy source used by photosynthetic organisms.",
            "current_step_prompt": "Identify the energy input under the stated conditions.",
            "conditions": ["Assume 25 C and no added artificial illumination."],
            "concepts": ["photosynthesis"],
            "source": {"source_unit_id": "authorized-source"},
            "private_rubric": {"answer_key": "PRIVATE_RUBRIC_CANARY"},
        },
        "turn_role": "user_question",
    }
    prepared, requirements = resolve(
        literal,
        preparer.prepare_query(literal).model_dump(),
        teaching,
        policy=VERSION,
        preparation_version=preparer.VERSION,
    )
    assert prepared["preparation_version"] == preparer.VERSION
    assert prepared["needs_clarification"] is False
    assert prepared["original_message"] == literal
    assert "25 C and no added artificial illumination" in prepared["standalone_query"]
    assert "PRIVATE_RUBRIC_CANARY" not in json.dumps((prepared, requirements))
    assert requirements["practice_reference_resolution"]["request_role"] == "teaching_instruction"
    assert requirements["preparation_dependency"]["syntax_preparation_version"] == (
        query_v14.BASE_VERSION
    )
    assert all("Help me" not in point["request"] for point in requirements["required_knowledge"])
