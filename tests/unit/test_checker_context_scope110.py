"""Authored contract controls, not measurements of model scientific accuracy."""

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
        "Explain the equilibrium state.",
        "At dynamic equilibrium, the system undergoes no change.",
        "At dynamic equilibrium, concentrations remain unchanged overall while opposing reactions continue at equal rates.",
        "At dynamic equilibrium, concentrations remain unchanged overall while opposing reactions continue at equal rates [ev_001] [ev_002].",
        "At dynamic equilibrium, the system undergoes no change [ev_001].",
        "Overall unchanged concentrations do not mean every intermediate is unchanged.",
    ),
    (
        "Define heat and distinguish a transfer route.",
        "Heat is energy transferred through particle contact. Conduction transfers energy through particle interactions.",
        "Heat is energy transferred because of a temperature difference; radiation is another transfer route without contact.",
        "Heat is energy transferred because of a temperature difference [ev_002]. Conduction is one transfer route [ev_001].",
        "Heat is energy transferred through particle contact [ev_001].",
        "A particular transfer route was promoted into the entire definition.",
    ),
    (
        "Describe the studied population's growth during the observed period.",
        "The studied algal population grew slowly during the observed period.",
        "The observed population was nitrogen-limited during that period; no result for other populations or periods is supplied.",
        "The studied nitrogen-limited algal population grew slowly during the observed period [ev_001] [ev_002].",
        "All populations always grow slowly [ev_001].",
        "The subject, nitrogen condition and observed period were broadened.",
    ),
]


def request_pair(question, summary, detail, **changes):
    request = request_fixture(question=question, source_relation_policy=VERSION, **changes)
    evidence_template = deepcopy(request.evidence[0])
    map_template = deepcopy(request.source_map["c1"])
    request.evidence = []
    request.source_map = {}
    for number, text in enumerate((summary, detail), 1):
        chunk = f"c{number}"
        evidence = deepcopy(evidence_template)
        evidence.update(
            evidence_id=f"ev_{number:03d}",
            chunk_id=chunk,
            text=text,
            text_hash=text_hash(text),
            context_order=number,
        )
        source = deepcopy(map_template)
        source.update(chunk_text=text, chunk_hash=text_hash(text))
        source["units"][0].update(id=f"u{number}", cleaned_text=text, text_hash=text_hash(text))
        source["spans"][0].update(unit_id=f"u{number}", end=len(text), chunk_end=len(text))
        request.evidence.append(evidence)
        request.source_map[chunk] = source
    return request


def response(text):
    citations = [identity for identity in ("ev_001", "ev_002") if f"[{identity}]" in text]
    value = answer(text)
    value["citations"] = citations
    return value


def authored_check(messages, defect=None):
    assert messages[0]["content"].count("FULL CONTEXT COMPATIBILITY AUDIT:") == 1
    data = check_input(messages)
    assert {f["evidence_id"] for f in data["SOURCE_FRAGMENTS"]} == {"ev_001", "ev_002"}
    value = unit_checker(messages)
    bindings = {row["claim_id"]: row["citations"] for row in data["ACTUAL_CITATION_BINDINGS"]}
    context = next(f for f in data["SOURCE_FRAGMENTS"] if f["evidence_id"] == "ev_002")
    for index, claim in enumerate(value["claims"]):
        own = bindings[claim["claim_id"]]
        claim["citations"] = [
            {
                "evidence_id": row["evidence_id"],
                "fragment_ids": row["allowed_fragment_ids"],
                "relation": "supporting",
            }
            for row in own
        ]
        ids = [fid for row in own for fid in row["allowed_fragment_ids"]]
        for unit in claim["units"]:
            unit["fragment_ids"] = ids
        if defect and index == 0:
            reason = f"{context['fragment_id']}: {defect}"
            claim.update(status="partial", reason=reason)
            for unit in claim["units"]:
                unit.update(status="partial", conditions_preserved=False, reason=reason)
    if defect:
        value.update(body_ok=False, repair_fragment_ids=[context["fragment_id"]])
    return value


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=["net_vs_transient", "definition_vs_route", "subject_condition_time"],
)
@pytest.mark.parametrize("accepted", [True, False], ids=["qualified", "authored_defect"])
def test_full_context_present_with_immutable_actual_positive_binding(case, accepted):
    request = request_pair(*case[:3])
    original = deepcopy(request)
    text = case[3] if accepted else case[4]
    adapter = Script(
        [
            response(text),
            lambda messages: authored_check(messages, None if accepted else case[5]),
        ]
    )
    result = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert request == original and len(adapter.calls) == result.budget["consumed_calls"] == 2
    assert result.succeeded is accepted
    if not accepted:
        assert result.response is None and result.delivered_projection == {}
        check = result.checks[0]
        assert check["judgment"]["coverage"] == "full" and check["judgment"]["missing_facets"] == []
        raw = check["typed_judgment_raw_aliases"]["claims"][0]
        assert {row["evidence_id"] for row in raw["citations"]} == {"ev_001"}
        assert raw["status"] == "partial" and raw["citations"][0]["relation"] == "supporting"


@pytest.mark.parametrize(
    "sources,text",
    [
        (
            (
                "Population A grows slowly under nitrogen limitation.",
                "Population B grows quickly when nitrogen is abundant.",
            ),
            "Population A grows slowly under nitrogen limitation [ev_001].",
        ),
        (
            (
                "Particles collide more frequently in this described system.",
                "This supplied source describes another energy-transfer route.",
            ),
            "Particles collide more frequently in this described system [ev_001].",
        ),
    ],
    ids=["different_conditions_not_conflict", "no_explicit_counterexample_no_veto"],
)
def test_authored_compatible_context_does_not_reject_correct_limited_statement(sources, text):
    request = request_pair("Explain the stated system.", *sources)
    result = GenerationService(Script([response(text), authored_check])).generate(
        request, RequestBudget(max_calls=2)
    )
    assert result.succeeded and result.response["answer_text"] == text


def test_context_cannot_be_added_to_positive_proof_without_actual_citation():
    case = CASES[0]
    request = request_pair(*case[:3])

    def invalid(messages):
        value = authored_check(messages)
        data = check_input(messages)
        foreign = next(
            f["fragment_id"] for f in data["SOURCE_FRAGMENTS"] if f["evidence_id"] == "ev_002"
        )
        value["claims"][0]["units"][0]["fragment_ids"] = [foreign]
        return value

    adapter = Script([response(case[4]), invalid])
    result = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert not result.succeeded and result.response is None and len(adapter.calls) == 2


def repair_request():
    case = CASES[0]
    return request_pair(
        *case[:3],
        repair_policy=REPAIR,
        joint_checker_policy="typed_joint_v5",
        teaching_context={
            "turn_role": "user_question",
            "teaching_mode": "direct",
            "help_level": 0,
        },
    )


def test_local_patch_retains_compatible_claim_and_requires_fresh_full_check():
    case = CASES[0]
    protected = "At dynamic equilibrium, concentrations remain unchanged overall [ev_002]."
    original = case[4] + " " + protected

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        assert [c["text"] for c in data["protected_exact_claims"]] == [protected]
        first = data["original_claims"][0]
        return {
            "edits": [{"claim_id": first["claim_id"], "replacement_text": case[3]}],
            "append_answer_text": "",
        }

    adapter = Script(
        [
            response(original),
            lambda messages: authored_check(messages, case[5]),
            patch,
            authored_check,
        ]
    )
    result = GenerationService(adapter).generate(repair_request(), RequestBudget(max_calls=4))
    assert result.succeeded, result.error
    assert protected in result.response["answer_text"] and case[3] in result.response["answer_text"]
    assert [a["stage"] for a in result.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"


def test_three_call_cap_stops_before_patch_when_fresh_recheck_cannot_fit():
    case = CASES[0]
    adapter = Script([response(case[4]), lambda messages: authored_check(messages, case[5])])
    result = GenerationService(adapter).generate(repair_request(), RequestBudget(max_calls=3))
    assert not result.succeeded and result.response is None and len(adapter.calls) == 2
    block = result.checks[0]["publication_block"]
    assert block["stop_reason"] == "insufficient_calls_for_repair_and_recheck"
    assert block["required_calls_for_repair_and_recheck"] == 2


def test_default_policy_does_not_receive_the_opt_in_context_audit():
    from test_answer_core_v5 import checker

    def default_check(messages):
        assert "FULL CONTEXT COMPATIBILITY AUDIT:" not in messages[0]["content"]
        return checker(messages)

    result = GenerationService(Script([answer(), default_check])).generate(
        request_fixture(), RequestBudget(max_calls=2)
    )
    assert result.succeeded
