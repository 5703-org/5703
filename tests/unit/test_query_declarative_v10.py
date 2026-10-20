"""Versioned local antecedents: source problem text is preserved, not solved."""

import pytest

from conversation.query import prepare_query, VERSION
from conversation.understanding import describe_question


PROBLEMS = [
    "A compound light microscope has a 10x eyepiece and a 40x objective. What is its total magnification? Show the relationship.",
    "A population has N=200 individuals and a per-capita growth rate r=0.10 per year under exponential growth. What is dN/dt at this population size?",
    "A fixed amount of gas occupies 2.0 L at 1.0 atm. At constant temperature it is compressed to 0.50 L. Assuming ideal behavior, find the final pressure.",
]


@pytest.mark.parametrize("question", PROBLEMS)
def test_actual_dev_complete_problem_retains_local_reference_and_all_conditions(question):
    old = prepare_query(question, version="conversation_preparer_v9")
    assert old.needs_clarification and old.fallback_reason == "missing_referent"
    current = prepare_query(question, version="conversation_preparer_v10")
    assert current.preparation_version == "conversation_preparer_v10"
    assert VERSION == "conversation_preparer_v11"
    assert not current.needs_clarification
    assert current.standalone_query == question
    assert current.referenced_message_ids == []
    structured = describe_question(question, current.model_dump(), [])
    assert structured["version"] == "question_understanding_v2"


@pytest.mark.parametrize(
    "question",
    [
        "A sample weighs 5 grams. What is its mass in kilograms?",
        "The train travels 30 kilometers in half an hour. What is its average speed?",
        "One seed contains stored food. Why does it need that reserve?",
    ],
)
def test_declarative_reference_is_general_not_a_named_dev_question_rule(question):
    prepared = prepare_query(question)
    assert not prepared.needs_clarification and prepared.standalone_query == question


@pytest.mark.parametrize(
    "question",
    [
        "A gas and a liquid are heated. Why does it expand?",
        "A gas occupies a vessel. A liquid occupies a beaker. Why does it expand?",
        "A gas occupies a vessel. How does this enzyme work?",
        "Compare DNA and RNA. Why does it work?",
        "What is its total magnification?",
    ],
)
def test_unclear_or_foreign_references_still_clarify(question):
    assert prepare_query(question).needs_clarification


def test_old_topic_is_not_imported_into_a_complete_new_problem():
    prepared = prepare_query(
        PROBLEMS[0], [{"message_id": "old", "role": "user", "content": "Explain osmosis."}]
    )
    assert prepared.standalone_query == PROBLEMS[0] and prepared.referenced_message_ids == []
