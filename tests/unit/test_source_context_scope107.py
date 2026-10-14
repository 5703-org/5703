"""Authored adjacent science controls; not live semantic-accuracy evidence."""

import json
from copy import deepcopy

import pytest
from generation import GenerationService, RequestBudget
from generation.local_repair import VERSION as REPAIR
from generation.source_relations_v2 import VERSION
from retrieval.source_spans import text_hash
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input
from test_source_relation_units_v2 import request_fixture, unit_checker

CASES = [
    (
        "Explain whether reactions continue at dynamic equilibrium.",
        "At dynamic equilibrium, opposing reactions continue at equal rates and concentrations remain unchanged overall.",
        "At dynamic equilibrium, opposing reactions continue at equal rates while concentrations remain unchanged overall [ev_001].",
        "At dynamic equilibrium, no reactions occur and every molecule stays unchanged [ev_001].",
        "Intermediate reactions were confused with the unchanged overall concentrations.",
    ),
    (
        "Describe growth of the studied algal population under nitrogen limitation.",
        "Under nitrogen limitation, the studied algal population grows slowly; no result for other populations or conditions is supplied.",
        "Under nitrogen limitation, the studied algal population grows slowly [ev_001].",
        "All organisms always grow slowly [ev_001].",
        "The stated population and nitrogen-limitation condition were broadened.",
    ),
    (
        "Define heat and distinguish the definition from one transfer route.",
        "Heat is energy transferred because of a temperature difference. Conduction is one transfer route through particle interactions; radiation can transfer energy without contact.",
        "Heat is energy transferred because of a temperature difference; conduction is one transfer route [ev_001].",
        "Heat is only the collision of particles [ev_001].",
        "One illustrative transfer route was promoted into the general definition.",
    ),
]


def scientific_request(case, **changes):
    question, source, _, _, _ = case
    value = request_fixture(
        question=question, source_relation_policy=VERSION, **changes
    )
    evidence = value.evidence[0]
    evidence.update(
        text=source, text_hash=text_hash(source), section="Authored adjacent science"
    )
    mapping = value.source_map["c1"]
    mapping.update(chunk_text=source, chunk_hash=text_hash(source))
    mapping["units"][0].update(cleaned_text=source, text_hash=text_hash(source))
    mapping["spans"][0].update(end=len(source), chunk_end=len(source))
    return value


def authored_support(messages, *, rejected_reason=None, final_conditions=True):
    data = check_input(messages)
    value = unit_checker(messages)
    bindings = {
        row["claim_id"]: row["citations"] for row in data["ACTUAL_CITATION_BINDINGS"]
    }
    for claim in value["claims"]:
        if claim["basis"] != "textbook":
            continue
        selected = bindings[claim["claim_id"]]
        claim["citations"] = [
            {
                "evidence_id": row["evidence_id"],
                "fragment_ids": row["allowed_fragment_ids"],
                "relation": "supporting",
            }
            for row in selected
        ]
        ids = [identity for row in selected for identity in row["allowed_fragment_ids"]]
        for unit in claim["units"]:
            unit.update(fragment_ids=ids, conditions_preserved=final_conditions)
        if rejected_reason:
            claim.update(status="partial", reason=rejected_reason)
            for unit in claim["units"]:
                unit.update(
                    status="partial", relation_preserved=False, reason=rejected_reason
                )
    if rejected_reason:
        value["body_ok"] = False
    return value


def drafted(text):
    def callback(messages):
        policy = messages[0]["content"]
        assert policy.count("CONTEXTUAL SCOPE AND CHANGE:") == 1
        assert "every intermediate state" in policy and "general definition" in policy
        assert "answer the supported remainder" in policy
        return answer(text)

    return callback


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=["net_vs_intermediate", "subject_and_condition", "definition_vs_route"],
)
@pytest.mark.parametrize(
    "accepted", [True, False], ids=["qualified_supported", "authored_scope_defect"]
)
def test_adjacent_science_sentence_support_and_negative_gates(case, accepted):
    request = scientific_request(case)
    original = deepcopy(request)
    text = case[2] if accepted else case[3]

    def checked(messages):
        return authored_support(messages, rejected_reason=None if accepted else case[4])

    adapter = Script([drafted(text), checked])
    outcome = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert request == original
    assert outcome.budget["consumed_calls"] == len(adapter.calls) == 2
    assert outcome.succeeded is accepted
    assert not outcome.checks[0]["source_relation_assessment"][
        "source_entailment_locally_certified"
    ]
    if accepted:
        assert outcome.response["answer_text"] == text
        assert outcome.response["citations"] == ["ev_001"]
    else:
        assert outcome.response is None and outcome.delivered_projection == {}
        assert outcome.checks[0]["judgment"]["coverage"] == "full"
        assert outcome.checks[0]["judgment"]["missing_facets"] == []


@pytest.mark.parametrize(
    "final_conditions",
    [True, False],
    ids=["full_recheck_pass", "remaining_condition_blocks"],
)
def test_same_generic_policy_reaches_local_patch_and_fresh_full_check(final_conditions):
    case = CASES[0]
    request = scientific_request(
        case,
        repair_policy=REPAIR,
        joint_checker_policy="typed_joint_v5",
        answer_mode="textbook",
        teaching_context={
            "turn_role": "user_question",
            "teaching_mode": "direct",
            "help_level": 0,
        },
    )

    def rejected(messages):
        return authored_support(messages, rejected_reason=case[4])

    def patched(messages):
        policy = messages[0]["content"]
        assert policy.count("CONTEXTUAL SCOPE AND CHANGE:") == 1
        assert "every intermediate state" in policy
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        assert (
            data["protected_exact_claims"] == [] and len(data["original_claims"]) == 1
        )
        return {
            "edits": [
                {
                    "claim_id": data["original_claims"][0]["claim_id"],
                    "replacement_text": case[2],
                }
            ],
            "append_answer_text": "",
        }

    def final_check(messages):
        return authored_support(messages, final_conditions=final_conditions)

    adapter = Script([drafted(case[3]), rejected, patched, final_check])
    outcome = GenerationService(adapter).generate(request)
    assert outcome.budget["consumed_calls"] == 4
    assert [attempt["stage"] for attempt in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert outcome.succeeded is final_conditions
    if final_conditions:
        assert outcome.response["answer_text"] == case[2]
    else:
        assert outcome.response is None and outcome.delivered_projection == {}


def test_default_request_does_not_adopt_the_v2_context_policy():
    from test_answer_core_v5 import checker

    def default_draft(messages):
        assert "CONTEXTUAL SCOPE AND CHANGE:" not in messages[0]["content"]
        return answer()

    outcome = GenerationService(Script([default_draft, checker])).generate(
        request_fixture(), RequestBudget(max_calls=2)
    )
    assert outcome.succeeded and outcome.budget["consumed_calls"] == 2
