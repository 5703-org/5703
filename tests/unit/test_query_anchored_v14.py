"""Opt-in preparer pairs retain whole questions and unresolved-reference guards."""

import pytest

from conversation import query, query_v14, requirements_v4

ENZYME = (
    "Does an enzyme alter a reaction’s free-energy change, or only its activation-energy barrier? "
    "Explain the distinction without treating the two energies as equal."
)
SEQUENCE = (
    "Follow the sequence from light absorption to sugar production, then distinguish the source "
    "and storage forms described for transport through a growing plant."
)


@pytest.mark.parametrize("question", [ENZYME, SEQUENCE])
def test_exposed_current_questions_retain_exact_actions_and_conditions(question):
    before = query.prepare_query(question, version=query.VERSION)
    current = query_v14.prepare_query(question)
    assert before.needs_clarification and before.fallback_reason == "missing_referent"
    assert current.standalone_query == current.original_message == question
    assert current.preparation_version == query_v14.VERSION
    assert not current.needs_clarification and current.referenced_message_ids == []
    assert current.topic_relation == "new_topic" and current.intent == "comparison"
    requirements = query_v14.describe_requirements(question, current.model_dump())
    assert requirements["standalone_query"] == question
    assert requirements["rewrite_audit"]["missing"] == []
    if question == ENZYME:
        assert "without" in requirements["preserved_constraints"]["negation"][0]["text"]
        assert len(requirements["required_knowledge"]) == 2
        assert requirements["required_knowledge"][1]["request"] == (
            "Explain the distinction without treating the two energies as equal"
        )


@pytest.mark.parametrize(
    "question",
    [
        "Does a spring change a mass's speed, or only its direction?",
        "Does a catalyst change a reaction's products or only its rate?",
        "Trace ions across a membrane, then distinguish the source and destination compartments.",
        "Follow a packet through a network, then explain the source and destination addresses.",
    ],
)
def test_generic_current_anchors_are_not_tied_to_a_particular_subject(question):
    old = query.prepare_query(question)
    current = query_v14.prepare_query(question)
    assert old.needs_clarification and old.fallback_reason == "missing_referent"
    assert not current.needs_clarification
    assert current.standalone_query == question
    assert current.referenced_message_ids == []


@pytest.mark.parametrize(
    "question",
    [
        "Does a teacher compare a student's score with a parent's opinion, or only its value?",
        "Does a model compare an atom's radius with an ion's radius, or only its charge?",
        "Does it change a reaction's rate?",
        "Does a reaction change its rate?",
        "Compare diffusion and osmosis. Explain it.",
        "Explain the source.",
        "Follow the sequence, then distinguish source and storage forms.",
        "Show me the source.",
        "How do I verify the source?",
        "Where did the source come from?",
        "Explain it without changing the condition.",
        "Give the source and storage forms of this process.",
    ],
)
def test_missing_or_ambiguous_subject_still_requires_clarification(question):
    current = query_v14.prepare_query(question)
    assert current.needs_clarification
    assert current.standalone_query is None


@pytest.mark.parametrize(
    "question,history",
    [
        (
            "Explain it more simply.",
            [{"role": "user", "message_id": "owned", "content": "What is osmosis?"}],
        ),
        (
            "Show the source.",
            [{"role": "user", "message_id": "owned", "content": "What is diffusion?"}],
        ),
        ("Can a tutor assess a student's work and its reasoning without changing the task?", []),
        ("Explain this selected passage.", []),
        ("What is gravity?", []),
        ("Hello.", []),
        ("What is rag?", []),
    ],
)
def test_existing_named_history_selected_passage_and_clarification_contracts_are_pinned(
    question, history
):
    old = query.prepare_query(question, history).model_dump()
    current = query_v14.prepare_query(question, history).model_dump()
    current["preparation_version"] = query.VERSION
    assert current == old


def test_unclear_current_question_never_uses_an_assistant_as_an_anchor():
    current = query_v14.prepare_query(
        "Why does it happen?", [{"role": "assistant", "content": "Osmosis occurs."}]
    )
    assert current.needs_clarification and current.referenced_message_ids == []


def test_unknown_version_is_rejected_and_universal_default_remains_v13():
    assert query.VERSION == "conversation_preparer_v13"
    assert query.prepare_query("What is gravity?").preparation_version == query.VERSION
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v14.prepare_query("What is gravity?", version=query.VERSION)


@pytest.mark.parametrize(
    "question",
    [
        "What is diffusion? Explain why it occurs.",
        "Explain osmosis. Also describe membrane transport at 2.5 kPa without heating.",
        "Compare gas A and gas B. Explain this comparison under constant temperature.",
    ],
)
def test_requirement_wrapper_preserves_current_multi_sentence_facets_and_conditions(question):
    prepared = query_v14.prepare_query(question).model_dump()
    assert not prepared["needs_clarification"]
    original_prepared = dict(prepared)
    old = requirements_v4.describe_requirements(
        question, {**prepared, "preparation_version": query_v14.BASE_VERSION}
    )
    current = query_v14.describe_requirements(question, prepared)
    dependency = current.pop("preparation_dependency")
    assert current == old
    assert prepared == original_prepared and prepared["preparation_version"] == query_v14.VERSION
    assert dependency["frozen_preparation_version"] == query_v14.VERSION
    assert dependency["syntax_preparation_version"] == query.VERSION
    assert current["explicit_clause_count"] == 2
    assert current["facet_origin"] == "explicit_clauses"


@pytest.mark.parametrize(
    "question", ["Explain this selected passage.", "According to this passage, explain diffusion."]
)
def test_requirement_wrapper_keeps_verified_reading_reference_semantics(question):
    prepared = {
        "original_message": question,
        "standalone_query": "Diffusion section. " + question,
        "preparation_version": query_v14.VERSION,
        "intent": "factual",
        "topic_relation": "new_topic",
        "needs_clarification": False,
        "fallback_reason": "verified_reading_selection",
    }
    old = requirements_v4.describe_requirements(
        question, {**prepared, "preparation_version": query.VERSION}
    )
    current = query_v14.describe_requirements(question, prepared)
    current.pop("preparation_dependency")
    assert current == old
    assert prepared["preparation_version"] == query_v14.VERSION
    assert current["reader_reference_resolution"]["retrieval_query_kept_separate"]


def test_requirement_wrapper_rejects_unknown_preparation_identity():
    prepared = query.prepare_query("What is diffusion?").model_dump()
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v14.describe_requirements("What is diffusion?", prepared)
