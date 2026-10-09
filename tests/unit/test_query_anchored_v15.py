"""V15 distinguishes an explicit content clause from a missing discourse anchor."""

import pytest

from conversation import query, query_v14, query_v15, requirements_v4

ENZYME = (
    "Does an enzyme alter a reaction’s free-energy change, or only its activation-energy barrier? "
    "Explain the distinction without treating the two energies as equal."
)
SEQUENCE = (
    "Follow the sequence from light absorption to sugar production, then distinguish the source "
    "and storage forms described for transport through a growing plant."
)


@pytest.mark.parametrize(
    "question",
    [
        ENZYME,
        SEQUENCE,
        "Does a magnet change a compass’s bearing, or only its stability?",
        "Can a researcher change a sample's mass, or only its volume?",
        "Trace carbon through an ecosystem, then distinguish the source and sink compartments.",
        "Follow a voltage across a circuit, then describe the source and load terminals.",
        "Explain the process of diffusion, then identify the source and destination regions.",
        "Describe light absorption, then distinguish the source and storage forms.",
    ],
)
def test_explicit_scientific_objects_preserve_full_question_and_constraints(question):
    old = query.prepare_query(question)
    current = query_v15.prepare_query(question)
    assert old.needs_clarification and old.fallback_reason == "missing_referent"
    assert not current.needs_clarification
    assert current.original_message == current.standalone_query == question
    assert current.preparation_version == query_v15.VERSION
    assert current.referenced_message_ids == []
    requirements = query_v15.describe_requirements(question, current.model_dump())
    assert requirements["standalone_query"] == question
    assert requirements["rewrite_audit"]["missing"] == []
    if question == ENZYME:
        assert "without" in requirements["preserved_constraints"]["negation"][0]["text"]
        assert requirements["required_knowledge"][1]["request"] == (
            "Explain the distinction without treating the two energies as equal"
        )


@pytest.mark.parametrize(
    "question",
    [
        "Explain the previously mentioned source.",
        "Can the previous source be used?",
        "Does the original source still exist?",
        "Explain the above source.",
        "Compare the prior source with the earlier one.",
        "Explain the earlier process, then distinguish source and storage forms.",
        "Describe the previously mentioned mechanism, then identify the source.",
        "Explain the above topic, then compare source and storage forms.",
        "Describe the previously discussed transfer, then identify the source.",
        "Trace the preceding mechanism, then distinguish source and destination compartments.",
        "Explain the mentioned concept, then identify its source.",
        "Explain the complex process, then distinguish source and storage forms.",
        "Describe the unusual mechanism, then identify the source.",
        "Explain the interesting topic, then compare source and storage forms.",
        "Follow the sequence, then distinguish source and storage forms.",
        "Follow the sequence from a process to a mechanism, then identify the source.",
    ],
)
def test_missing_primary_content_stays_on_exact_historical_clarification_path(question):
    old = query.prepare_query(question).model_dump()
    current = query_v15.prepare_query(question).model_dump()
    assert old["needs_clarification"]
    assert current["needs_clarification"] and current["standalone_query"] is None
    current["preparation_version"] = query.VERSION
    assert current == old


@pytest.mark.parametrize(
    "question",
    [
        "Does a researcher compare a sample’s purity with a control’s purity, or only its stability?",
        "Can it alter a sample’s composition, or only its colour?",
        "Explain the cited source.",
        "How do I verify the source?",
        "Where can I read the source?",
        "Explain it without changing the condition.",
        "Does a reaction change its rate?",
        "Show the source and storage forms of this process.",
    ],
)
def test_ambiguous_possessors_pronouns_and_source_presentation_keep_v14_behavior(question):
    old = query_v14.prepare_query(question).model_dump()
    current = query_v15.prepare_query(question).model_dump()
    assert current["needs_clarification"]
    current["preparation_version"] = query_v14.VERSION
    assert current == old


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
        (
            "Explain the above source.",
            [{"role": "user", "message_id": "owned", "content": "What is diffusion?"}],
        ),
        ("Why does it happen?", [{"role": "assistant", "content": "Diffusion occurs."}]),
        ("What is gravity?", []),
        ("What is rag?", []),
        ("Hello.", []),
        ("Explain this selected passage.", []),
    ],
)
def test_legitimate_history_existing_answers_and_reader_context_are_pinned(question, history):
    old = query_v14.prepare_query(question, history).model_dump()
    current = query_v15.prepare_query(question, history).model_dump()
    current["preparation_version"] = query_v14.VERSION
    assert current == old


@pytest.mark.parametrize(
    "question",
    [
        ENZYME,
        SEQUENCE,
        "Explain osmosis. Also describe membrane transport at 2.5 kPa without heating.",
        "Compare gas A and gas B. Explain this comparison under constant temperature.",
    ],
)
def test_requirements_preserve_original_constraints_and_v15_v14_v13_dependency(question):
    prepared = query_v15.prepare_query(question).model_dump()
    original_prepared = dict(prepared)
    current = query_v15.describe_requirements(question, prepared)
    old = requirements_v4.describe_requirements(
        question, {**prepared, "preparation_version": query.VERSION}
    )
    dependency = current.pop("preparation_dependency")
    assert current == old
    assert prepared == original_prepared
    assert dependency == {
        "version": "query_v15_requirement_dependency_v1",
        "frozen_preparation_version": query_v15.VERSION,
        "anchor_preparation_version": query_v14.VERSION,
        "syntax_preparation_version": query.VERSION,
        "requirements_version": requirements_v4.VERSION,
    }
    assert current["rewrite_audit"]["missing"] == []


@pytest.mark.parametrize(
    "question", ["Explain this selected passage.", "According to this passage, explain diffusion."]
)
def test_requirements_keep_verified_selected_reading_query_separate(question):
    prepared = {
        "original_message": question,
        "standalone_query": "Diffusion section. " + question,
        "preparation_version": query_v15.VERSION,
        "intent": "factual",
        "topic_relation": "new_topic",
        "needs_clarification": False,
        "fallback_reason": "verified_reading_selection",
    }
    current = query_v15.describe_requirements(question, prepared)
    current.pop("preparation_dependency")
    assert current == requirements_v4.describe_requirements(
        question, {**prepared, "preparation_version": query.VERSION}
    )
    assert current["reader_reference_resolution"]["retrieval_query_kept_separate"]
    assert prepared["preparation_version"] == query_v15.VERSION


def test_version_rejection_keeps_universal_v13_and_saved_v14_contracts():
    assert query.VERSION == "conversation_preparer_v13"
    assert query_v14.VERSION == "conversation_preparer_v14"
    assert query_v14.prepare_query("Explain the above source.").needs_clarification is False
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v15.prepare_query("What is gravity?", version=query_v14.VERSION)
    with pytest.raises(ValueError, match="Unsupported frozen"):
        query_v15.describe_requirements(
            "What is gravity?", query_v14.prepare_query("What is gravity?").model_dump()
        )
