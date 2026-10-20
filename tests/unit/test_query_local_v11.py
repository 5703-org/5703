"""Retained failure mechanisms, with immutable legacy preparation controls."""

import pytest

from conversation.query import prepare_query


@pytest.mark.parametrize(
    "question",
    [
        "At a constant glomerular filtration rate of 125 mL per minute, calculate the volume of filtrate formed in 24 hours. This asks for filtrate before tubular reabsorption.",
        "Compare the radius of a neutral atom with the radius of its common cation and explain the relevant electron-shell change.",
        "At 25 degrees Celsius an ideal dilute solution has hydroxide concentration 1.0 x 10^-4 mol/L. Calculate its pOH and pH using pKw=14.00.",
    ],
)
def test_local_problem_precedes_unrelated_history_and_keeps_v10(question):
    old = prepare_query(question, version="conversation_preparer_v10")
    assert old.needs_clarification
    new = prepare_query(
        question, [{"role": "user", "content": "Explain photosynthesis", "id": "old"}]
    )
    assert not new.needs_clarification
    assert new.standalone_query == question
    assert new.referenced_message_ids == []
    assert new.preparation_version == "conversation_preparer_v11"


def test_bare_reference_after_comparison_still_needs_clarification():
    result = prepare_query("Compare DNA and RNA. Why does it do that?")
    assert result.needs_clarification


def test_unresolved_reference_still_uses_a_single_previous_subject():
    result = prepare_query(
        "Why does it happen?", [{"role": "user", "content": "Explain diffusion", "id": "one"}]
    )
    assert not result.needs_clarification
    assert result.referenced_message_ids == ["one"]
    assert "diffusion" in result.standalone_query


def test_two_declarative_subjects_do_not_create_unique_referent():
    result = prepare_query("A gas occupies 2 L. A liquid occupies 3 L. Calculate its volume.")
    assert result.needs_clarification
