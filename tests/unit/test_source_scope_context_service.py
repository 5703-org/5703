"""Portable service controls for a literal scope-context binding recheck."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v5 import protected_claims
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script


STORAGE = "Light energy is converted into chemical energy and temporarily stored in ALFA."
CONTEXT = "The heat-dependent reactions produce ALFA."
SOURCE = STORAGE + " " + CONTEXT
BODY = "The heat-dependent reactions store chemical energy in ALFA [ev_001]."


@pytest.mark.parametrize("select_context", [False, True], ids=["missing_scope", "selected_scope"])
def test_actual_v5_service_keeps_scope_recheck_separate_from_semantic_support(select_context):
    value = req(
        question="Explain the system's energy storage.",
        answer_mode="textbook",
        teaching_context={"teaching_mode": "direct", "help_level": 0},
        joint_checker_policy="typed_joint_v5",
        repair_policy=CLAIM_PATCH_POLICY,
        config=ModelConfig(tokenizer_provider="estimate"),
    )
    evidence = deepcopy(value.evidence)
    evidence[0].update(text=SOURCE, text_hash=text_hash(SOURCE), section="Authored storage")
    mapping = deepcopy(value.source_map)
    mapping["c1"].update(chunk_text=SOURCE, chunk_hash=text_hash(SOURCE))
    mapping["c1"]["units"][0].update(cleaned_text=SOURCE, text_hash=text_hash(SOURCE))
    mapping["c1"]["spans"][0].update(end=len(SOURCE), chunk_end=len(SOURCE))
    value = replace(value, evidence=evidence, source_map=mapping)

    submitted_checks = []
    actual_fragments = []

    def select_actual_support(messages):
        packet = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
        if "CHECKER_INPUT_ENCODING" in packet:
            from generation.checker_encoding import decode

            packet = decode(packet)
        if "SOURCE_FRAGMENT_TABLE" in packet:
            table = packet["SOURCE_FRAGMENT_TABLE"]
            packet["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
        fragments = packet["SOURCE_FRAGMENTS"]
        assert len(fragments) == 2
        by_text = {fragment["exact_text"].strip(): fragment for fragment in fragments}
        assert set(by_text) == {STORAGE, CONTEXT}
        assert all(fragment["complete_block"] for fragment in fragments)
        actual_fragments.append(deepcopy(by_text))
        selected = [by_text[STORAGE]["fragment_id"]]
        if select_context:
            selected.append(by_text[CONTEXT]["fragment_id"])
        bound = {row["claim_id"]: row for row in packet["ACTUAL_CITATION_BINDINGS"]}
        judgment = checker(messages)
        assert len(judgment["claims"]) == 1
        for row in judgment["claims"]:
            citations = bound[row["claim_id"]]["citations"]
            assert len(citations) == 1 and citations[0]["evidence_id"] == "ev_001"
            assert set(selected) <= set(citations[0]["allowed_fragment_ids"])
            row["citations"] = [
                {
                    "evidence_id": "ev_001",
                    "relation": "supporting",
                    "fragment_ids": selected,
                }
            ]
        submitted_checks.append(deepcopy(judgment))
        return judgment

    adapter = Script([chat_value("answer", BODY, citations=["ev_001"]), select_actual_support])
    outcome = GenerationService(adapter).generate(value, RequestBudget(max_calls=2))
    assert len(adapter.calls) == outcome.budget["consumed_calls"] == 2
    assert [attempt["stage"] for attempt in outcome.attempts] == ["generation", "joint_check"]
    assert len(outcome.checks) == 1
    current = outcome.checks[0]
    raw = current["typed_judgment_raw_aliases"]
    assert raw["body_ok"] is True
    assert raw["claims"] == submitted_checks[0]["claims"]
    assert raw["claims"][0]["basis"] == "textbook"
    assert raw["claims"][0]["status"] == "supported"
    assert outcome.token_budget["claim_support"]["independent_evaluation"] is False
    issues = current["technical_entity_binding_issues_raw_aliases"]
    scope_issues = [
        issue for issue in issues if issue["code"] == "SOURCE_SCOPE_CONTEXT_NOT_SELECTED"
    ]

    if select_context:
        # Selecting the literal context removes only this narrow diagnostic.
        # The scripted supported judgment is not a scientific measurement.
        assert scope_issues == []
        return

    assert len(scope_issues) == len(issues) == 1
    issue = scope_issues[0]
    claims = outcome.attribution["claims"]
    assert len(claims) == 1
    claim = claims[0]
    assert claim["answer_field"] == "answer_text" and claim["text"] == BODY
    assert issue["claim_id"] == claim["claim_id"]
    assert issue["leading_scope"] == "heat-dependent reactions"
    assert claim["text"][issue["scope_start"] : issue["scope_end"]] == issue["leading_scope"]
    source_fragments = actual_fragments[0]
    assert issue["selected_fragment_ids"] == [source_fragments[STORAGE]["fragment_id"]]
    candidates = issue["context_candidate_fragments"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["evidence_id"] == "ev_001"
    assert candidate["fragment_id"] == source_fragments[CONTEXT]["fragment_id"]
    context_text = source_fragments[CONTEXT]["exact_text"]
    assert context_text[candidate["scope_start"] : candidate["scope_end"]] == issue["leading_scope"]
    assert candidate["fragment_id"] not in issue["selected_fragment_ids"]
    assert issue["binding_recheck_required"] is True
    assert issue["claim_relation_assessed"] is False
    assert issue["source_entailment_certified"] is False
    assert issue["publication_override"] is False
    assert issue in current["structural_issues"]
    assert current["accepted"] is False
    assert outcome.token_budget["claim_support"]["accepted"] is False
    assert outcome.response is None and outcome.error
    assert not outcome.succeeded
    assert any(
        action["claim_id"] == claim["claim_id"] and action["code"] == issue["code"]
        for action in current["repair_plan"]["actions"]
    )

    without_scope = [item for item in current["structural_issues"] if item["code"] != issue["code"]]
    previously_protected = protected_claims(claims, current["judgment"], without_scope)
    assert claim["claim_id"] in {row["claim_id"] for row in previously_protected}
    now_protected = protected_claims(claims, current["judgment"], current["structural_issues"])
    assert claim["claim_id"] not in {row["claim_id"] for row in now_protected}
