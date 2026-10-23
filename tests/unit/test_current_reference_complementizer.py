"""Cross-domain bounded complementizer controls, no model or retrieval calls."""

import pytest
from conversation.current_reference import audit, apply, POLICY
from conversation.query import prepare_query


@pytest.mark.parametrize(
    "question",
    [
        "Compare photosynthesis with the claim that light is unnecessary.",
        "Explain the statement that copper is conductive.",
        "Explain the hypothesis that planets are moving.",
        "Show that the solution is acidic.",
        "Assume that a circuit is disconnected.",
        "Explain the fact that water can expand.",
        "Suppose that metal is not magnetic.",
        "Compare the claims that copper is conductive and that water is clear.",
    ],
)
def test_complete_reporting_clause_has_no_history_reference(question):
    result = audit(question)
    # The coordinated second clause remains conservatively unsupported.
    if question.startswith("Compare the claims"):
        assert not result["eligible"] and result["unresolved"]
        return
    assert result["eligible"] and not result["history_consulted"]
    assert all(b["kind"] == "nonreferential_complement_clause" for b in result["bindings"])
    base = prepare_query(question).model_dump()
    assert base["needs_clarification"]  # Records the pre-existing query limitation.
    same, record = apply(base, None)
    assert same == base and record is None
    improved, record = apply(base, POLICY)
    assert not improved["needs_clarification"]
    assert improved["standalone_query"] == question and improved["referenced_message_ids"] == []


@pytest.mark.parametrize(
    "question",
    [
        "Explain that.",
        "Compare that pressure.",
        "Explain the claim that is wrong.",
        "Explain the claim that copper.",
        "Explain the claim that it is conductive.",
        "Explain the claim that its temperature is low.",
        "Explain the claim that copper is conductive. Why is it useful?",
        "Explain the previous claim that copper is conductive.",
        'Explain the claim "that copper is conductive".',
        "Explain the claim that copper is conductive and compare that.",
    ],
)
def test_missing_or_ambiguous_references_stay_unlicensed(question):
    result = audit(question)
    assert result is None or not result["eligible"]


@pytest.mark.parametrize("fault", [None, "hash", "query", "missing_hash", "explicit_wrong_text"])
def test_legacy_requirements_need_both_exact_original_hash_and_query(fault):
    from conversation.requirements import describe_requirements
    from conversation.current_reference import attach_requirements

    question = "Explain the claim that copper is conductive."
    prepared, record = apply(prepare_query(question).model_dump(), POLICY)
    requirements = describe_requirements(question, prepared, [])
    assert "requirement_source_text" not in requirements
    if fault == "hash":
        requirements["original_question_hash"] = "0" * 64
    elif fault == "query":
        requirements["standalone_query"] = "unrelated"
    elif fault == "missing_hash":
        requirements.pop("original_question_hash")
    elif fault == "explicit_wrong_text":
        requirements["requirement_source_text"] = "unrelated"
    if fault:
        with pytest.raises(ValueError, match="verbatim"):
            attach_requirements(requirements, prepared, record)
    else:
        result = attach_requirements(requirements, prepared, record)
        assert result["current_message_reference_audit"] == record
        assert all(result[key] == value for key, value in requirements.items())
