"""Portable actual-service control for a negative body-to-short binding recheck."""

import json
from copy import deepcopy
from dataclasses import replace

from generation import GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v5 import protected_claims
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script


SOURCE = "The system uses ALFB to transfer energy."
BODY = "The system uses ALFA to transfer energy [ev_001]."
SHORT = "Energy is carried by ALFA [ev_001]."


def test_actual_v5_service_routes_cross_surface_binding_without_promoting_judgment():
    value = req(
        question="Explain the system's energy transfer.",
        answer_mode="textbook",
        teaching_context={"teaching_mode": "direct", "help_level": 0},
        joint_checker_policy="typed_joint_v5",
        repair_policy=CLAIM_PATCH_POLICY,
        config=ModelConfig(tokenizer_provider="estimate"),
    )
    evidence = deepcopy(value.evidence)
    evidence[0].update(text=SOURCE, text_hash=text_hash(SOURCE), section="Authored transfer")
    mapping = deepcopy(value.source_map)
    mapping["c1"].update(chunk_text=SOURCE, chunk_hash=text_hash(SOURCE))
    mapping["c1"]["units"][0].update(cleaned_text=SOURCE, text_hash=text_hash(SOURCE))
    mapping["c1"]["spans"][0].update(end=len(SOURCE), chunk_end=len(SOURCE))
    value = replace(value, evidence=evidence, source_map=mapping)

    submitted_checks = []

    def select_actual_support(messages):
        packet = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
        if "CHECKER_INPUT_ENCODING" in packet:
            from generation.checker_encoding import decode

            packet = decode(packet)
        bound = {row["claim_id"]: row for row in packet["ACTUAL_CITATION_BINDINGS"]}
        judgment = checker(messages)
        for row in judgment["claims"]:
            row["citations"] = [
                {
                    "evidence_id": citation["evidence_id"],
                    "fragment_ids": list(citation["allowed_fragment_ids"]),
                    "relation": "supporting",
                }
                for citation in bound[row["claim_id"]]["citations"]
            ]
        submitted_checks.append(deepcopy(judgment))
        return judgment

    draft = chat_value("answer", BODY, citations=["ev_001"], short_answer=SHORT)
    adapter = Script([draft, select_actual_support])
    outcome = GenerationService(adapter).generate(value, RequestBudget(max_calls=2))

    assert len(adapter.calls) == outcome.budget["consumed_calls"] == 2
    assert [attempt["stage"] for attempt in outcome.attempts] == ["generation", "joint_check"]
    assert outcome.response is None and outcome.error
    assert not outcome.succeeded
    assert len(outcome.checks) == 1
    current = outcome.checks[0]
    assert current["accepted"] is False
    assert outcome.token_budget["claim_support"]["accepted"] is False
    raw = current["typed_judgment_raw_aliases"]
    assert raw["body_ok"] is True
    assert raw["claims"] == submitted_checks[0]["claims"]
    assert all(row["basis"] == "textbook" and row["status"] == "supported" for row in raw["claims"])

    claims = outcome.attribution["claims"]
    by_surface = {row["answer_field"]: row for row in claims}
    assert set(by_surface) == {"answer_text", "short_answer"}
    body_id, short_id = by_surface["answer_text"]["claim_id"], by_surface["short_answer"]["claim_id"]
    issues = current["technical_entity_binding_issues_raw_aliases"]
    by_claim = {issue["claim_id"]: issue for issue in issues}
    assert len(issues) == len(by_claim) == 2
    assert set(by_claim) == {body_id, short_id}
    short_issue = by_claim[short_id]
    assert short_issue["binding_diagnostic_origin"] == "cross_surface_copy_witness_v1"
    assert short_issue["anchor_claim_id"] == body_id
    assert short_issue["claimed_identifier"] == "ALFA"
    assert short_issue["source_identifiers"] == ["ALFB"]
    assert short_issue["selected_fragment_ids"] == by_claim[body_id]["selected_fragment_ids"]
    assert short_issue["binding_recheck_required"] is True
    assert short_issue["claim_relation_assessed"] is False
    for issue in issues:
        assert issue["source_entailment_certified"] is False
        assert issue["publication_override"] is False
        assert issue in current["structural_issues"]

    actions = current["repair_plan"]["actions"]
    assert {action["claim_id"] for action in actions if action["code"] == "UNRESOLVED_TECHNICAL_ENTITY_COLLISION"} == {body_id, short_id}
    # The two-call budget stops before patch generation. Verify its actual
    # protection helper against the retained production judgment/issues.
    direct_only = [issue for issue in current["structural_issues"] if issue.get("claim_id") != short_id]
    previously_protected = protected_claims(claims, current["judgment"], direct_only)
    assert short_id in {row["claim_id"] for row in previously_protected}
    now_protected = protected_claims(claims, current["judgment"], current["structural_issues"])
    assert short_id not in {row["claim_id"] for row in now_protected}
    assert body_id not in {row["claim_id"] for row in now_protected}
