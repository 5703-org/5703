"""A named in-question possessor keeps its dependent clause on the same topic."""

import pytest

from conversation.query import POSSESSIVE_VERSION, VERSION, prepare_query


@pytest.mark.parametrize(
    "question",
    [
        "How does a sea star's water vascular system help its tube feet move and grip?",
        "How can a plant's vascular tissue move its water through the stem?",
        "Why does a dog's endocrine system affect its growth?",
    ],
)
def test_named_in_clause_possessor_is_not_a_missing_referent(question):
    assert POSSESSIVE_VERSION == "conversation_preparer_v12"
    old = prepare_query(question, version="conversation_preparer_v11")
    assert old.needs_clarification and old.fallback_reason == "missing_referent"
    current = prepare_query(question)
    retained = prepare_query(question, version=POSSESSIVE_VERSION)
    assert not retained.needs_clarification and retained.standalone_query == question
    assert current.preparation_version == VERSION
    assert not current.needs_clarification
    assert current.standalone_query == question
    assert current.topic_relation == "new_topic"
    assert current.referenced_message_ids == []


@pytest.mark.parametrize(
    "question",
    [
        "How does its water vascular system help tube feet move?",
        "What is its role in movement?",
        "How does a sea star's movement and a clam's defense affect its survival?",
        "Compare a sea star and a clam. How does its movement work?",
    ],
)
def test_missing_or_competing_possessors_remain_clarifications(question):
    assert prepare_query(question).needs_clarification
