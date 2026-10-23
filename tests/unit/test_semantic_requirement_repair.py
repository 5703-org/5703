"""Offline ordinary-V5 requirement-gap routing controls, not model accuracy."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget
from generation.adapters import ProviderResult, chat_value
from test_semantic_binding_repair_routing import (
    BAD,
    SAFE,
    compact,
    judgment,
    no_external_io as no_external_io,
    packet_from,
    request,
)


FIXED = "The indicator flashes twice on startup [ev_002]."
LIMIT = "The supplied source does not specify the indicator color for a high signal."


class RequirementGapTransport:
    def __init__(self, policy, *, defect=None, final_negative=False, aggregate_only=None):
        self.policy = policy
        self.defect = defect
        self.final_negative = final_negative
        self.aggregate_only = aggregate_only
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), kwargs))
        purpose = kwargs["request_context"]["purpose"]
        if purpose == "generation":
            value = chat_value(
                "answer",
                SAFE + " " + (FIXED if self.aggregate_only else BAD),
                citations=["ev_001", "ev_002"],
            )
        elif purpose == "semantic_repair":
            data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
            assert any(row["text"] == SAFE for row in data["protected_exact_claims"])
            value = {
                "edits": [
                    {"claim_id": row["claim_id"], "replacement_text": FIXED + " " + LIMIT}
                    for row in data["original_claims"]
                    if row["claim_id"] in data["editable_claim_ids"]
                ],
                "append_answer_text": "",
            }
        else:
            initial = purpose != "joint_recheck"
            value = judgment(
                messages,
                self.policy,
                "irrelevant",
                initial=initial,
                defect=self.defect if initial else None,
            )
            value.update(
                coverage="full" if initial else "supported_partial",
                missing_facets=[] if initial else ["Indicator color for a high signal."],
                limitations_explicit=not initial,
            )
            requirements = value["requirements"].values() if self.policy else value["requirements"]
            for row in requirements:
                row.update(
                    sufficiency="partial",
                    response_coverage="covered" if initial else "limitation",
                    missing_information="The source does not give the indicator color for a high signal.",
                )
                if initial and self.defect == "gap_unspecified":
                    row["missing_information"] = ""
            if initial and self.defect == "requirement_identity":
                if self.policy:
                    first = next(iter(value["requirements"]))
                    value["requirements"]["FOREIGN"] = value["requirements"].pop(first)
                else:
                    value["requirements"][0]["requirement_id"] = "foreign_requirement"
            if initial and self.aggregate_only:
                if self.policy is None:
                    value["body_ok"] = self.aggregate_only == "body_true"
            if not initial:
                packet = packet_from(messages)
                if self.policy:
                    for key, target in packet[compact.CLAIM_TARGETS].items():
                        original = next(
                            c for c in packet["CLAIMS"] if c["claim_id"] == target["claim_id"]
                        )
                        if original["text"] == LIMIT:
                            value["claims"][key] = {"basis": "evidence_limitation"}
                        elif self.final_negative and "startup" in original["text"]:
                            value["claims"][key].update(
                                status="partial", unestablished_quote="startup"
                            )
                else:
                    originals = {c["claim_id"]: c for c in packet["CLAIMS"]}
                    for index, row in enumerate(value["claims"]):
                        original = originals[row["claim_id"]]
                        if original["text"] == LIMIT:
                            value["claims"][index] = {
                                "claim_id": row["claim_id"],
                                "basis": "evidence_limitation",
                                "reason": "Authored exact visible context limitation.",
                            }
                        elif self.final_negative and "startup" in original["text"]:
                            row["status"] = "partial"
                    value["body_ok"] = not self.final_negative
        return ProviderResult(
            raw_text=json.dumps(value),
            finish_reason="stop",
            provider="authored_offline",
            model="authored",
            request_submitted=True,
        )


def run(policy, *, calls=4, **kwargs):
    adapter = RequirementGapTransport(policy, **kwargs)
    value = request(policy, "irrelevant")
    value.question += " Include the indicator color for a high signal."
    out = GenerationService(adapter).generate(value, RequestBudget(max_calls=calls))
    return out, adapter


@pytest.mark.parametrize("policy", [None, compact.POLICY])
def test_valid_negative_and_named_requirement_gap_repair_then_freshly_check(
    policy, record_property
):
    out, adapter = run(policy)
    record_property(
        "routing_receipt",
        json.dumps(
            {
                "policy": policy,
                "stages": [row[1]["request_context"]["purpose"] for row in adapter.calls],
                "consumed_calls": out.budget["consumed_calls"],
                "succeeded": out.succeeded,
                "error": out.error,
                "published_response": out.response,
                "checks": [
                    {
                        key: row.get(key)
                        for key in (
                            "accepted",
                            "checker_inconsistencies",
                            "semantic_negative_routing",
                            "judgment_raw_aliases",
                            "primitive_judgment_raw_aliases",
                        )
                    }
                    for row in out.checks
                ],
                "fixture_only": True,
                "external_calls": 0,
            }
        ),
    )
    assert out.succeeded, out.error
    assert [row[1]["request_context"]["purpose"] for row in adapter.calls] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    first, final = out.checks
    route = first["semantic_negative_routing"]
    assert route["route"] == "semantic_repair"
    assert not route["judgment_changed"] and not route["publication_override"]
    assert {row["code"] for row in route["deferred_aggregate_issues"]} == {
        "FULL_COVERAGE_WITH_REQUIREMENT_GAP",
    }
    assert not first["accepted"] and final["accepted"]
    assert first["projection_hash"] != final["projection_hash"]
    assert out.response["answer_text"] == SAFE + " " + FIXED + " " + LIMIT
    assert out.token_budget["answer_completeness"]["status"] == "partial"


@pytest.mark.parametrize("policy", [None, compact.POLICY])
@pytest.mark.parametrize("calls", [2, 3])
def test_no_repair_without_reserved_generation_and_final_check_pair(policy, calls):
    out, adapter = run(policy, calls=calls)
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert [row[1]["request_context"]["purpose"] for row in adapter.calls] == [
        "generation",
        "joint_check",
    ]
    assert out.budget["consumed_calls"] == len(adapter.calls) == 2


@pytest.mark.parametrize("policy", [None, compact.POLICY])
def test_fresh_final_negative_never_publishes(policy):
    out, adapter = run(policy, final_negative=True)
    assert out.response is None and not out.delivered_projection
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    assert all(not check["accepted"] for check in out.checks)


@pytest.mark.parametrize("policy", [None, compact.POLICY])
@pytest.mark.parametrize("defect", ["identity", "source", "quote"])
def test_real_identity_source_or_quote_fault_never_enters_semantic_repair(policy, defect):
    out, adapter = run(policy, defect=defect)
    assert out.response is None and not out.delivered_projection and out.error
    assert "semantic_repair" not in [row[1]["request_context"]["purpose"] for row in adapter.calls]
    assert len(adapter.calls) == out.budget["consumed_calls"] <= 4


@pytest.mark.parametrize("policy", [None, compact.POLICY])
def test_body_true_aggregate_only_keeps_unchanged_checker_correction(policy):
    out, adapter = run(policy, aggregate_only="body_true")
    assert out.response is None and not out.delivered_projection
    assert "semantic_repair" not in [row[1]["request_context"]["purpose"] for row in adapter.calls]
    assert "semantic_negative_routing" not in out.checks[0]


def test_body_false_without_any_named_claim_negative_keeps_checker_correction():
    out, adapter = run(None, aggregate_only="body_false")
    assert out.response is None and not out.delivered_projection
    assert "semantic_repair" not in [row[1]["request_context"]["purpose"] for row in adapter.calls]
    assert "semantic_negative_routing" not in out.checks[0]


@pytest.mark.parametrize("policy", [None, compact.POLICY])
@pytest.mark.parametrize("defect", ["requirement_identity", "gap_unspecified"])
def test_nonaggregate_requirement_contract_fault_stays_blocked(policy, defect):
    out, adapter = run(policy, defect=defect)
    assert out.response is None and not out.delivered_projection
    assert "semantic_repair" not in [row[1]["request_context"]["purpose"] for row in adapter.calls]


@pytest.mark.parametrize("policy", [None, compact.POLICY])
def test_unknown_requirement_contract_code_stays_blocked(policy, monkeypatch):
    from generation import checked

    original = checked.assess_requirements

    def future(*args, **kwargs):
        contract, defects, coverage = original(*args, **kwargs)
        return [*contract, {"code": "FUTURE_REQUIREMENT_CONTRACT"}], defects, coverage

    monkeypatch.setattr(checked, "assess_requirements", future)
    out, adapter = run(policy)
    assert out.response is None and not out.delivered_projection
    assert "semantic_repair" not in [row[1]["request_context"]["purpose"] for row in adapter.calls]
