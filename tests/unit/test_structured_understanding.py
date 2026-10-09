"""Bounded intent preservation and finite evidence admission; no provider calls."""

from copy import deepcopy
import pytest
from conversation.query import prepare_query, VERSION, LEGACY_VERSION, PREVIOUS_VERSION
from conversation.understanding import describe_question
from retrieval.relevance import freeze_selection, merge_candidates


def prior(question):
    return [{"role": "user", "message_id": "u1", "content": question}]


def test_comparison_correction_preserves_both_operands_or_clarifies():
    original = "I mean RNA, not DNA."
    good = prepare_query(original, prior("Compare DNA and proteins."))
    assert good.intent == "comparison" and not good.needs_clarification
    assert "ribonucleic acid (RNA)" in good.standalone_query
    assert "proteins" in good.standalone_query and "DNA" not in good.standalone_query
    ambiguous = prepare_query(original, prior("Compare DNA and RNA."))
    assert ambiguous.needs_clarification and ambiguous.standalone_query is None
    assert ambiguous.fallback_reason == "ambiguous_comparison_correction"
    assert prepare_query("I mean RNA", prior("Compare DNA and proteins")).needs_clarification


def test_correction_preserves_relationship_conditions_and_resolves_one_pronoun():
    question = "Why does DNA not remain stable at 90 degrees if heated?"
    prepared = prepare_query("I mean RNA, not DNA.", prior(question))
    assert (
        prepared.standalone_query
        == "Why does ribonucleic acid (RNA) not remain stable at 90 degrees if heated?"
    )
    resolved = prepare_query("I mean photosynthesis.", prior("Why does it need light?"))
    assert resolved.standalone_query == "Why does photosynthesis need light?"
    unresolved = prepare_query("I mean photosynthesis.", prior("Why does it do that?"))
    assert unresolved.needs_clarification
    constrained = prepare_query(
        "I mean photosynthesis.", prior("Explain respiration without oxygen at 20 C")
    )
    assert constrained.needs_clarification


def test_structured_requirements_keep_negation_numbers_conditions_and_parts():
    question = "Why does water not boil at 80 C if pressure stays fixed; and how does pressure change boiling?"
    prepared = prepare_query(question).model_dump()
    before = deepcopy(prepared)
    record = describe_question(question, prepared)
    assert prepared == before and record["original_message"] == question
    assert len(record["requested_facets"]) == 2
    assert "not" in record["requested_facets"][0]["terms"]
    assert "80" in record["requested_facets"][0]["terms"]
    assert record["constraints"]["negation"] == ["not"]
    assert "80 C" in record["constraints"]["numbers"]
    assert any("if pressure" in value for value in record["constraints"]["conditions"])
    assert record["method"] == "bounded_deterministic" and record["limitations"]


def test_structured_correction_retains_provenance_and_no_clause_drops():
    history = prior("Compare DNA and proteins")
    message = "I mean RNA, not DNA"
    record = describe_question(message, prepare_query(message, history).model_dump(), history)
    assert record["correction"] == {
        "replacement": "RNA",
        "excluded": "DNA",
        "prior_question": history[0]["content"],
    }
    assert len(record["comparison_targets"]) == 2
    assert len(record["requested_facets"]) == 2
    question = "; ".join(f"Explain concept {i}" for i in range(12))
    record = describe_question(question, prepare_query(question).model_dump())
    assert len(record["requested_facets"]) == 8
    assert all(
        f"concept {i}" in " ".join(row["request"] for row in record["requested_facets"])
        for i in range(12)
    )
    assert "More than eight" in record["limitations"][-1]


def test_legacy_v6_is_explicit_and_unsupported_versions_fail_closed():
    history = prior("Compare DNA and RNA")
    old = prepare_query("I mean RNA, not DNA", history, version=LEGACY_VERSION)
    new = prepare_query("I mean RNA, not DNA", history)
    assert old.preparation_version == LEGACY_VERSION and not old.needs_clarification
    assert new.preparation_version == VERSION and new.needs_clarification
    with pytest.raises(ValueError, match="frozen query"):
        prepare_query("Hello", version="made_up")


@pytest.mark.parametrize(
    "question",
    [
        "What is photosynthesis? Also explain how to configure a server for this topic.",
        "Explain osmosis. How does it change if the concentration rises?",
    ],
)
def test_same_message_question_supplies_named_subject_without_dropping_other_clause(question):
    result = prepare_query(question)
    assert not result.needs_clarification
    assert result.standalone_query == question and result.referenced_message_ids == []
    assert prepare_query(question, version=PREVIOUS_VERSION).needs_clarification
    record = describe_question(question, result.model_dump())
    assert record["original_message"] == question


@pytest.mark.parametrize(
    "question",
    [
        "What is that? How does it work?",
        "Compare osmosis and diffusion. How does it work?",
        "What is osmosis? What is diffusion? How does it work?",
    ],
)
def test_same_message_missing_or_multiple_subjects_still_clarify(question):
    assert prepare_query(question).needs_clarification
    if question.startswith(("Compare", "What is osmosis")):
        assert prepare_query(question, prior("What is photosynthesis?")).needs_clarification


def test_union_is_bounded_deduplicated_and_does_not_compare_stale_scores():
    fresh = [{"chunk_id": str(i), "text": str(i), "score": i} for i in range(20)]
    inherited = [
        {
            "chunk_id": "old",
            "text": "prior",
            "score": 10000,
            "inherited_from": {"request_id": "prior", "evidence_id": "ev_001"},
        },
        {
            **fresh[0],
            "score": 9999,
            "inherited_from": {"request_id": "prior", "evidence_id": "ev_002"},
        },
    ]
    before = deepcopy((fresh, inherited))
    merged, trace = merge_candidates(fresh, inherited, freeze_selection({"candidate_count": 20}))
    assert len(merged) == 20 and len({row["chunk_id"] for row in merged}) == 20
    assert [row["chunk_id"] for row in merged[:2]] == ["0", "old"]
    assert merged[0]["score"] == 0 and merged[0]["inherited_from"]["evidence_id"] == "ev_002"
    assert trace["excluded"] == [{"chunk_id": "19", "reason": "candidate_limit"}]
    assert (fresh, inherited) == before
    with pytest.raises(ValueError, match="frozen evidence"):
        merge_candidates(fresh, inherited, {**freeze_selection(None), "candidate_limit": 21})
