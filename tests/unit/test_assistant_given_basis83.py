"""Real publication gates with authored checker responses; no prompt-quality claim."""

import pytest

from generation import GenerationService, RequestBudget
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input
from test_source_relation_units_v2 import request_fixture, unit_checker


def _authored_given(surface, quote):
    def check(messages):
        data = check_input(messages)
        result = unit_checker(messages)
        target = next(
            claim
            for claim in data["CLAIMS"]
            if claim["answer_field"] == surface and claim["text"].startswith(quote)
        )
        index = next(
            index
            for index, claim in enumerate(result["claims"])
            if claim["claim_id"] == target["claim_id"]
        )
        result["claims"][index] = {
            "claim_id": target["claim_id"],
            "basis": "problem_input",
            "status": "supported",
            "problem_quote": target["text"],
            "reason": "Authored learner-given classification for gate testing.",
        }
        return result

    return check


def _run(surface, quote, *, cited=False, question=None, current_problem=None):
    proposed = quote + (" [ev_001]" if cited else "")
    body = "Carbon dioxide supplies carbon for sugar. [ev_001]"
    draft = answer(
        proposed + " " + body if surface == "answer_text" else body,
        short_answer=proposed if surface == "short_answer" else None,
    )
    values = {
        "joint_checker_policy": "typed_joint_v5",
        "source_relation_policy": "source_relation_contract_v2",
    }
    if question is not None:
        values["question"] = question
    if current_problem is not None:
        values["teaching_context"] = {"current_problem": current_problem}
    request = request_fixture(**values)
    script = Script([draft, _authored_given(surface, quote)])
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=2, max_active_seconds=180)
    )
    return outcome, script


@pytest.mark.parametrize("surface", ["answer_text", "short_answer"])
@pytest.mark.parametrize("cited", [False, True], ids=["uncited", "cited"])
def test_assistant_authored_text_cannot_become_learner_given(surface, cited):
    quote = "Photosynthesis uses light energy."
    outcome, script = _run(surface, quote, cited=cited)

    assert outcome.response is None and not outcome.delivered_projection
    assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert outcome.budget["consumed_calls"] == len(script.calls) == 2
    assert outcome.checks[0]["validation_state"] == "validated"
    assert outcome.checks[0]["semantic_sufficiency"]["status"] == "sufficient"
    raw = outcome.checks[0]["typed_judgment_raw_aliases"]
    assert raw["body_ok"] is True and raw["complete_answer"] is True
    given = next(claim for claim in raw["claims"] if claim["basis"] == "problem_input")
    issues = [
        issue["code"]
        for issue in outcome.checks[0]["structural_issues"]
        if issue.get("claim_id") == given["claim_id"]
    ]
    assert "CHECK_PROBLEM_QUOTE_MISMATCH" in issues
    assert ("UNEXPECTED_CITATION_FOR_BASIS" in issues) is cited
    assert not outcome.checks[0]["accepted"]


@pytest.mark.parametrize("surface", ["answer_text", "short_answer"])
@pytest.mark.parametrize("origin", ["question", "current_problem"])
def test_faithful_original_learner_given_keeps_its_basis_and_can_publish(surface, origin):
    quote = "The sample has mass 36.0 g."
    question = (
        quote + " Identify the given mass." if origin == "question" else "Identify the given mass."
    )
    outcome, script = _run(
        surface,
        quote,
        question=question,
        current_problem=quote if origin == "current_problem" else None,
    )

    assert outcome.succeeded, outcome.error
    assert outcome.budget["consumed_calls"] == len(script.calls) == 2
    given = next(
        claim
        for claim in outcome.attribution["claims"]
        if claim["answer_field"] == surface and claim["support"]["basis"] == "problem_input"
    )
    assert given["support"]["problem_quote"] == quote
    assert given["support"]["problem_input_status"] == "supported"
    assert given["support"]["status"] is None
    assert outcome.checks[0]["structural_issues"] == []
    assert outcome.checks[0]["accepted"] is True


def test_unit_cannot_borrow_another_parent_claims_selected_same_evidence_fragment():
    recorded = {}

    def borrow(messages):
        data = check_input(messages)
        result = unit_checker(messages)
        sources = {source["exact_text"]: source for source in data["SOURCE_FRAGMENTS"]}
        first = sources["Photosynthesis uses light energy."]["fragment_id"]
        second = sources["Carbon dioxide supplies carbon for sugar."]["fragment_id"]
        first_parent, second_parent = result["claims"]
        first_parent["citations"][0]["fragment_ids"] = [first]
        second_parent["citations"][0]["fragment_ids"] = [second]
        for unit in first_parent["units"]:
            unit["fragment_ids"] = [second]
        for unit in second_parent["units"]:
            unit["fragment_ids"] = [second]
        binding = next(
            row
            for row in data["ACTUAL_CITATION_BINDINGS"]
            if row["claim_id"] == first_parent["claim_id"]
        )
        assert second in binding["citations"][0]["allowed_fragment_ids"]
        assert all(
            citation["evidence_id"] == "ev_001"
            for parent in (first_parent, second_parent)
            for citation in parent["citations"]
        )
        recorded.update(
            parent=first_parent["claim_id"],
            foreign_parent=second_parent["claim_id"],
            fragment=second,
        )
        return result

    script = Script(
        [
            answer(
                "Photosynthesis uses light energy. [ev_001] "
                "Carbon dioxide supplies carbon for sugar. [ev_001]"
            ),
            borrow,
        ]
    )
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request_fixture(
            joint_checker_policy="typed_joint_v5",
            source_relation_policy="source_relation_contract_v2",
        ),
        RequestBudget(max_calls=2, max_active_seconds=180),
    )

    assert outcome.response is None and not outcome.delivered_projection
    assert outcome.error["code"] == "CHECKER_INCONSISTENT"
    assert outcome.budget["consumed_calls"] == len(script.calls) == 2
    issues = outcome.checks[0]["checker_inconsistencies"]
    assert any(
        issue["code"] == "RELATION_ASSESSED_FRAGMENT_MISMATCH"
        and issue["claim_id"] == recorded["parent"]
        and issue["fragment_id"] == recorded["fragment"]
        and issue["evidence_id"] == "ev_001"
        for issue in issues
    )
    raw = outcome.checks[0]["typed_judgment_raw_aliases"]
    parents = {claim["claim_id"]: claim for claim in raw["claims"]}
    assert recorded["fragment"] not in parents[recorded["parent"]]["citations"][0]["fragment_ids"]
    assert parents[recorded["foreign_parent"]]["citations"][0]["fragment_ids"] == [
        recorded["fragment"]
    ]
