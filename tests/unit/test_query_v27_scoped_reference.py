"""Generic scoped eligibility; not semantic reference resolution or gold support."""

import hashlib

import pytest

from conversation import query_v26, query_v27


POSITIVE = [
    "For a confined gas kept at constant temperature, what happens to its volume if pressure rises?",
    "For an elastic spring held at constant temperature, how does its length change under a larger force?",
    "For the sealed container, what happens to its pressure during heating?",
    "For a fixed amount of confined gas kept at constant temperature, what happens to its volume if the pressure is tripled? Give the final-to-initial volume ratio, the direction of change, and the conditions needed for this comparison.",
    "Compare the listed molar volume of an ideal gas at 0 degrees Celsius under 1 atmosphere and under 1 bar. Give each pressure-value pairing with its per-mole volume unit, identify the larger value, and keep the ideal-gas and temperature conditions explicit.",
    "Compare density measurements at two temperatures. Give each density measurement with its unit.",
    "Compare reaction times at two temperatures. Give each reaction-time estimate with its uncertainty.",
]


@pytest.mark.parametrize("message", POSITIVE)
@pytest.mark.parametrize(
    "history", [[], [{"role": "user", "content": "Explain photosynthesis.", "message_id": "prior"}]]
)
def test_complete_current_request_remains_verbatim_and_has_audited_local_scopes(message, history):
    result = query_v27.prepare_query(message, history)
    assert not result.needs_clarification
    assert result.standalone_query == message
    assert result.referenced_message_ids == []
    audit = query_v27.scoped_reference_audit(message)
    assert audit and audit["eligibility_only"] and audit["coreference_resolution"] is None
    assert audit["source_sha256"] == hashlib.sha256(message.encode()).hexdigest()
    for row in audit["referent_spans"]:
        assert message[row["start"] : row["end"]] == row["text"]
        assert message[row["owner_start"] : row["owner_end"]] == row["owner_text"]
    requirements = query_v27.describe_requirements(message, result.model_dump(), history)
    assert requirements["preparation_dependency"]["frozen_preparation_version"] == query_v27.VERSION


NEGATIVE = [
    "Why does it do that?",
    "For a gas and a liquid, what happens to its volume?",
    "For a gas, what happens to a liquid and its volume?",
    "For a gas, what happens to temperature and its variance?",
    "For a gas, what happens to its volume if a liquid changes its pressure?",
    "For a rotor beside a shaft, how does its speed change?",
    "For a sample containing a solute, what happens to its concentration?",
    "For no gas, what happens to its volume?",
    "For a cell not a nucleus, what happens to its volume?",
    "For the earlier example, what happens to its pressure?",
    "For the selected paragraph, what happens to its meaning?",
    "For a gas, what happens to its volume? Explain this comparison.",
    "For a gas, what happens to its volume? Explain that result.",
    "For a gas, what happens to its volume and their temperatures?",
    "For a gas, what happens to its volume? Do not compare outcomes. Explain this comparison.",
    "Give each result with its unit.",
    "Compare that with the other one. Give each measurement with its unit.",
    '"For a gas, what happens to its volume?" Explain its meaning.',
    "For a gas, what happens to its volume? Explain the previous answer.",
    "For a gas, what happens to its volume? Explain it.",
]


@pytest.mark.parametrize("message", NEGATIVE)
def test_unbound_competing_external_negated_or_quoted_references_keep_previous_policy(message):
    assert query_v27.scoped_reference_audit(message) is None
    old = query_v26.prepare_query(message).model_dump()
    new = query_v27.prepare_query(message).model_dump()
    new["preparation_version"] = old["preparation_version"]
    assert old == new


def test_frozen_versions_and_plain_questions_remain_compatible():
    for message in ["Explain osmosis.", "Hello", "Diffusion is passive. Explain why it occurs."]:
        old = query_v26.prepare_query(message).model_dump()
        new = query_v27.prepare_query(message).model_dump()
        new["preparation_version"] = old["preparation_version"]
        assert new == old
    with pytest.raises(ValueError):
        query_v27.prepare_query(POSITIVE[0], version=query_v26.VERSION)
