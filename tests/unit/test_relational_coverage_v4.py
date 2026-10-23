"""Authored planning regressions; no fixture supplies a semantic truth label."""

from copy import deepcopy

import pytest

from conversation.requirements import describe_requirements
from generation import coverage_v3, coverage_v4, teaching_plan_v6


def evidence(identity, text):
    return {"evidence_id": "ev_" + identity, "chunk_id": identity, "text": text}


def understanding(question):
    return describe_requirements(
        question,
        {
            "standalone_query": question,
            "intent": "factual",
            "topic_relation": "new_topic",
            "needs_clarification": False,
            "preparation_version": "conversation_preparer_v13",
        },
    )


@pytest.mark.parametrize(
    "question,source",
    [
        (
            "Explain photosynthesis and the role of sunlight.",
            "Photosynthesis converts sunlight into chemical energy.",
        ),
        (
            "Explain the role of a catalyst.",
            "A catalyst speeds a reaction and is regenerated after the reaction.",
        ),
        (
            "Describe the roles of ions in conduction.",
            "Ions carry charge during conduction.",
        ),
        (
            "Explain the role played by a catalyst.",
            "A catalyst speeds a reaction.",
        ),
    ],
)
def test_generic_relation_word_is_not_a_mandatory_literal_source_word(question, source):
    rows = [evidence("source", source)]
    supplied = understanding(question)
    before = deepcopy(supplied)
    old = coverage_v3.assess_evidence_coverage(question, rows, supplied)
    current = coverage_v4.assess_evidence_coverage(question, rows, supplied)
    assert old["targeted_query"] is not None
    assert current["targeted_query"] is None
    assert current["context_sufficiency_estimate"] == "lexically_complete"
    assert current["semantic_sufficiency"] is None and current["draft_support"] is None
    point = current["candidate_coverage"]["requirements"][0]
    original = supplied["required_knowledge"][0]
    assert point["request"] == original["request"]
    assert point["intent"] == original["intent"] and point["relation"] == original["relation"]
    assert point["conditions"] == original["conditions"] and point["objects"] == original["objects"]
    assert "role" not in point["terms"]
    assert point["lexical_projection"]["relation_cues"]
    assert point["lexical_projection"]["semantic_relation_verified"] is None
    assert supplied == before


def test_supported_relation_paraphrase_does_not_trigger_an_extra_local_pass():
    question = "Explain the role of a catalyst."
    rows = [evidence("catalyst", "A catalyst speeds a reaction.")]
    calls = []
    policy = teaching_plan_v6.freeze_generation_policy()
    original_policy = deepcopy(policy)
    final, report, trace = coverage_v4.supplement_once(
        question,
        rows,
        None,
        policy,
        retrieve=lambda *_: calls.append("retrieve") or [],
        rerank=lambda _, values: values,
        screen=lambda _, values: (values, {}),
        checkpoint=lambda *_: calls.append("checkpoint"),
    )
    assert calls == [] and trace["retrieval_passes"] == 0
    assert final == rows and report["semantic_sufficiency"] is None
    assert policy == original_policy and policy["coverage_version"] == coverage_v3.VERSION


def test_out_of_topic_sources_do_not_become_covered_after_relation_projection():
    question = "Explain the role of gravity in orbital motion."
    report = coverage_v4.assess_evidence_coverage(
        question, [evidence("unrelated", "A catalyst speeds a chemical reaction.")]
    )
    assert report["context_sufficiency_estimate"] == "none"
    assert report["candidate_coverage"]["missing_requirement_ids"] == ["requirement_01"]
    assert report["targeted_query"].startswith(question)
    assert "gravity" in report["candidate_coverage"]["requirements"][0]["terms"]
    assert report["semantic_sufficiency"] is None


def test_named_role_subject_and_bare_role_definition_keep_their_literal_anchor():
    for question in (
        "Define role.",
        "Explain role conflict.",
        "Explain the role of role conflict.",
    ):
        point = coverage_v4.requirements(question)[0]
        assert "role" in point["terms"]
        assert point["request"] == coverage_v3.requirements(question)[0]["request"]


def test_original_negation_condition_quantities_formula_and_units_are_preserved():
    question = (
        "Explain the role of pressure in PV = nRT without changing volume, "
        "only if temperature remains at 300 K and pressure is not 2.5 kPa."
    )
    supplied = understanding(question)
    point = coverage_v4.requirements(question, supplied)[0]
    original = supplied["required_knowledge"][0]
    assert point["request"] == original["request"]
    assert point["conditions"] == original["conditions"]
    assert {"without", "only", "if", "not", "300", "k", "2.5", "kpa", "pv", "nrt"} <= set(
        point["terms"]
    )
    report = coverage_v4.assess_evidence_coverage(
        question,
        [evidence("generic", "Pressure changes when volume and temperature change.")],
        supplied,
    )
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["targeted_query"] is not None
    assert report["semantic_sufficiency"] is None


def test_comparison_objects_and_relation_survive_distributed_cues():
    question = "Compare the role of diffusion and osmosis without a membrane."
    supplied = understanding(question)
    report = coverage_v4.assess_evidence_coverage(
        question,
        [
            evidence("diffusion", "Diffusion can occur without a membrane."),
            evidence("osmosis", "Osmosis requires a membrane."),
        ],
        supplied,
    )
    point = report["candidate_coverage"]["requirements"][0]
    assert point["objects"] == supplied["required_knowledge"][0]["objects"]
    assert point["relation"] == "compare_both_objects_on_requested_axes"
    assert "without" in point["terms"] and "membrane" in point["terms"]
    assert point["distributed_across_passages"] is True
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["semantic_sufficiency"] is None


def test_conflicting_single_passage_words_are_only_a_lexical_estimate():
    report = coverage_v4.assess_evidence_coverage(
        "Explain the role of gravity in orbital motion.",
        [evidence("false", "Gravity does not affect orbital motion.")],
    )
    assert report["context_sufficiency_estimate"] == "lexically_complete"
    assert report["semantic_sufficiency"] is None and report["human_rating"] is None
    assert "verbatim requirement" in report["response_guidance"]


def test_budget_loss_of_an_actual_object_stays_visible():
    question = "Explain the role of charge in current and resistance."
    rows = [
        evidence("a", "Charge flows in a current."),
        evidence("b", "Resistance limits current."),
    ]
    report = coverage_v4.assess_evidence_coverage(question, rows, selected_evidence=rows[:1])
    assert report["candidate_coverage"]["requirements"][0]["lexically_covered"] is True
    assert report["budget_lost_requirement_ids"] == ["requirement_01"]
    assert report["semantic_sufficiency"] is None


def test_actual_missing_object_still_receives_one_bounded_pass():
    question = "Explain the role of gravity in orbital motion."
    original = [evidence("gravity", "Gravity attracts masses.")]
    new = evidence("orbit", "Orbital motion follows a curved path.")
    calls = []
    final, report, trace = coverage_v4.supplement_once(
        question,
        original,
        None,
        teaching_plan_v6.freeze_generation_policy(),
        retrieve=lambda query, limit: calls.append((query, limit)) or [new],
        rerank=lambda _, values: values,
        screen=lambda _, values: (values, {}),
        checkpoint=lambda *_: None,
    )
    assert len(calls) == trace["retrieval_passes"] == 1
    assert calls[0][1] == 10 and calls[0][0].startswith(question)
    assert final == original + [new] and trace["added_chunk_ids"] == ["orbit"]
    assert report["targeted_query"] is None and report["semantic_sufficiency"] is None


def test_cancel_checkpoint_and_source_identity_fence_are_kept():
    original = evidence("gravity", "Gravity attracts masses.")
    calls = []

    def cancel(*_):
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        coverage_v4.supplement_once(
            "Explain the role of gravity in orbital motion.",
            [original],
            None,
            teaching_plan_v6.freeze_generation_policy(),
            retrieve=lambda *_: calls.append("retrieve") or [],
            rerank=lambda _, rows: rows,
            screen=lambda _, rows: (rows, {}),
            checkpoint=cancel,
        )
    assert calls == []
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        coverage_v4.supplement_once(
            "Explain the role of gravity in orbital motion.",
            [original],
            None,
            teaching_plan_v6.freeze_generation_policy(),
            retrieve=lambda *_: [evidence("gravity", "Orbital motion changed.")],
            rerank=lambda _, rows: rows,
            screen=lambda _, rows: (rows, {}),
            checkpoint=lambda *_: None,
        )


def test_verified_selected_passage_remains_source_bound_without_invented_terms():
    supplied = {
        "required_knowledge": [
            {
                "id": "requirement_01",
                "request": "Explain this selected passage.",
                "origin": "verified_selected_source_referent_v1",
                "relation": "explain_verified_source",
                "conditions": [],
            }
        ]
    }
    report = coverage_v4.assess_evidence_coverage("Explain this.", [], supplied)
    assert report["source_bound_requirement_ids"] == ["requirement_01"]
    assert report["candidate_coverage"]["requirements"][0]["terms"] == []
    assert report["targeted_query"] is None and report["semantic_sufficiency"] is None


@pytest.mark.parametrize("fault", ["over_limit", "rerank_membership", "screen_membership"])
def test_supplement_preserves_candidate_and_membership_bounds(fault):
    original = [evidence("gravity", "Gravity attracts masses.")]
    incoming = [evidence("orbit", "Orbital motion follows a curved path.")]
    if fault == "over_limit":
        incoming = [evidence(str(i), "Orbital motion.") for i in range(11)]
    with pytest.raises(ValueError, match="COVERAGE_SUPPLEMENT_"):
        coverage_v4.supplement_once(
            "Explain the role of gravity in orbital motion.",
            original,
            None,
            teaching_plan_v6.freeze_generation_policy(),
            retrieve=lambda *_: incoming,
            rerank=lambda _, rows: [] if fault == "rerank_membership" else rows,
            screen=lambda _, rows: (
                [evidence("alien", "Unrelated data.")] if fault == "screen_membership" else rows,
                {},
            ),
            checkpoint=lambda *_: None,
        )


def test_unsatisfied_supplement_remains_partial_after_exactly_one_pass():
    calls = []
    _, report, trace = coverage_v4.supplement_once(
        "Explain the role of gravity in orbital motion.",
        [evidence("gravity", "Gravity attracts masses.")],
        None,
        teaching_plan_v6.freeze_generation_policy(),
        retrieve=lambda *_: calls.append("retrieve") or [],
        rerank=lambda _, rows: rows,
        screen=lambda _, rows: (rows, {}),
        checkpoint=lambda *_: None,
    )
    assert calls == ["retrieve"] and trace["retrieval_passes"] == 1
    assert report["targeted_query"] is not None
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["semantic_sufficiency"] is None


def test_citation_prefix_projection_does_not_erase_subject_source():
    question = "Show sources for the role of energy sources in metabolism."
    point = coverage_v4.requirements(question)[0]
    assert "source" in point["terms"]
    assert {"energy", "metabolism"} <= set(point["terms"])
    assert "role" not in point["terms"]
    assert point["request"] == "Show sources for the role of energy sources in metabolism"
