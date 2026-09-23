"""Exact edit and recheck guards using authored scripted examples only."""

from copy import deepcopy
import json

import pytest

from generation.binding_repair import repair_bindings, table_fragments
from generation.joint_policy import response_claims
from generation import GenerationService, RequestBudget
from generation.token_counting import TokenCounter
from test_enhancement_generation import Script, answer
from test_generation_reliability_v2 import req, check, unsupported


def fixture():
    response = answer("A supported fact. A second supported fact. [ev_001]")
    claims = response_claims(response)
    evaluated = [
        {
            "claim_id": c["claim_id"],
            "factual": True,
            "status": "supported",
            "basis": "textbook",
            "fragment_ids": ["f1"],
        }
        for c in claims
    ]
    fragments = [{"fragment_id": "f1", "evidence_id": "ev_001", "complete_block": True}]
    issues = [{"claim_id": claims[0]["claim_id"], "code": "CHECK_CITATION_SOURCE_MISMATCH"}]
    return response, claims, evaluated, fragments, issues


def test_exact_binding_edit_preserves_all_nonmarker_content_and_original():
    data = fixture()
    before = deepcopy(data)
    fixed = repair_bindings(*data)
    assert data == before
    assert fixed["answer_text"] == "A supported fact. [ev_001] A second supported fact. [ev_001]"
    assert fixed["citations"] == ["ev_001"]


@pytest.mark.parametrize(
    "defect", ["unsupported", "atomic", "stale_span", "unknown_fragment", "other_issue"]
)
def test_binding_repair_never_rescues_other_defects(defect):
    response, claims, evaluated, fragments, issues = fixture()
    if defect == "unsupported":
        evaluated[0]["status"] = "partial"
    elif defect == "atomic":
        fragments[0]["complete_block"] = False
    elif defect == "stale_span":
        claims[0]["end"] -= 1
    elif defect == "unknown_fragment":
        fragments.clear()
    else:
        issues[0]["code"] = "CHECK_DERIVATION_INVALID"
    assert repair_bindings(response, claims, evaluated, fragments, issues) is None


def test_changed_projection_must_pass_full_recheck_or_publish_nothing():
    initial = answer("Photosynthesis uses light energy. It uses light energy. [ev_001]")
    adapter = Script([initial, check, unsupported])
    out = GenerationService(adapter).generate(req())
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.response is None and not out.delivered_projection
    assert out.budget["consumed_calls"] == 3 and len(out.drafts) == 2
    assert out.drafts[1]["origin"] == "deterministic_citation_binding"


def test_generic_c2_still_uses_model_repair_four_calls():
    initial = answer("Photosynthesis uses light energy. It uses light energy. [ev_001]")
    adapter = Script([initial, check, answer(), check])
    out = GenerationService(adapter).generate(req(repair_policy="generic_answer_repair_v1"))
    assert out.succeeded and out.budget["consumed_calls"] == 4
    assert "deterministic_citation_repair" not in out.token_budget


def test_deterministic_repair_cannot_publish_without_remaining_checker_slot():
    adapter = Script(
        [answer("Photosynthesis uses light energy. It uses light energy. [ev_001]"), check]
    )
    out = GenerationService(adapter).generate(req(), RequestBudget(max_calls=2))
    assert not out.succeeded and not out.delivered_projection
    assert out.budget["consumed_calls"] == 2


def test_fragment_table_preserves_unicode_exact_text_identity_and_atomic_flags():
    values = [
        {
            "fragment_id": "F001",
            "evidence_id": "ev_001",
            "exact_text": "P = nRT/V; 25 °C; α + β",
            "block_kind": "equation",
            "complete_block": False,
        },
        {
            "fragment_id": "F002",
            "evidence_id": "ev_002",
            "exact_text": "The same condition holds.\nDo not omit it.",
            "block_kind": "prose",
            "complete_block": True,
        },
    ]
    data = {"SOURCE_FRAGMENTS": values, "PROPOSED_DELIVERY": {"answer_text": "Exact text"}}
    compact = table_fragments(data)
    table = compact["SOURCE_FRAGMENT_TABLE"]
    assert [dict(zip(table["columns"], r)) for r in table["rows"]] == values
    assert (
        data["SOURCE_FRAGMENTS"] == values
        and compact["PROPOSED_DELIVERY"] == data["PROPOSED_DELIVERY"]
    )
    assert len(json.dumps(compact)) < len(json.dumps(data))


def test_complete_window_overflow_uses_lossless_table_before_checker_transport(monkeypatch):
    captured = []

    def tokens(self, messages, schema, name):
        if name == "joint_check_v2":
            data = json.loads(messages[-1]["content"])
            return self.config.window_tokens if "SOURCE_FRAGMENTS" in data else 500
        return 500

    def tabular_check(messages):
        data = json.loads(messages[-1]["content"])
        table = data.pop("SOURCE_FRAGMENT_TABLE")
        data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
        captured.extend(data["SOURCE_FRAGMENTS"])
        return check([{"content": json.dumps(data)}])

    monkeypatch.setattr(TokenCounter, "request_input", tokens)
    adapter = Script([answer(), tabular_check])
    out = GenerationService(adapter).generate(req())
    assert out.succeeded and out.budget["consumed_calls"] == 2
    assert out.token_budget["checker_payload_encodings"][0]["encoding"] == "lossless_fragment_table"
    assert [f["exact_text"] for f in captured] == [
        f["exact_text"] for f in out.attribution["fragments"]
    ]
    assert all(f["complete_block"] for f in captured)
