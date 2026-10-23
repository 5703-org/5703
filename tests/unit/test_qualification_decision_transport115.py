"""Source-binding/decision transport controls, never semantic accuracy fixtures."""

from copy import deepcopy
import json
import socket

import pytest
from generation import GenerationService, RequestBudget
from generation.qualification_v1 import ReliableQualificationCheck, decision_derivative
from test_context_qualification_v1 import request, source_request, verdict, SOURCE
from test_enhancement_generation import Script, answer


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Decision transport controls cannot use network or DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)


def quote_only(value):
    result = deepcopy(value)
    for record in result["qualification_assessments"]:
        record.pop("citation_support_exists")
        for role in ("supporting_quotes", "limiting_quotes", "revision_supporting_quotes"):
            for quote in record[role]:
                quote.pop("fragment_id")
    return result


def run(judge, value=None):
    return GenerationService(Script([answer(), judge])).generate(
        value or request(), RequestBudget(max_calls=2)
    )


def test_quote_only_schema_has_no_redundant_model_support_flag_or_source_identity():
    schema = ReliableQualificationCheck.model_json_schema()
    assert set(schema["$defs"]["ExactQuote"]["properties"]) == {"quote"}
    assert "citation_support_exists" not in schema["$defs"]["QualificationAssessment"]["properties"]


def test_unique_quote_only_binds_program_owned_coordinates():
    out = run(lambda messages: quote_only(verdict(messages)))
    assert out.succeeded, out.error
    row = out.checks[0]["qualification_assessment"]["claims"][0]
    bound = row["resolved_quotes"][0]
    assert bound["quote"] == SOURCE[bound["start"] : bound["end"]]
    assert bound["source_unit_id"] and bound["fragment_id"]
    assert out.checks[0]["gate_decisions"]["qualification_context_accepted"]


@pytest.mark.parametrize("forgery", ["nonexistent", "coordinates", "forged_legacy_alias"])
def test_matching_valid_control_passes_but_forged_quote_cannot_publish(forgery):
    assert run(lambda messages: quote_only(verdict(messages))).succeeded

    def bad(messages):
        value = quote_only(verdict(messages))
        quote = value["qualification_assessments"][0]["supporting_quotes"][0]
        if forgery == "nonexistent":
            quote["quote"] = "Not present in any eligible source."
        elif forgery == "coordinates":
            quote["start"] = 0
        else:
            quote["fragment_id"] = "F999"
        return value

    out = run(bad)
    assert not out.succeeded and not out.delivered_projection
    assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"


def test_unique_limiting_quote_passes_but_duplicate_source_occurrences_fail():
    def conflict(messages):
        value = quote_only(verdict(messages))
        row = value["qualification_assessments"][0]
        row.update(context_status="conflict", limiting_quotes=deepcopy(row["supporting_quotes"]))
        return value

    unique = run(conflict)
    assert unique.checks[0]["validation_state"] == "validated"
    assert unique.checks[0]["qualification_assessment"]["rejection_kind"] == "context"
    duplicate = run(conflict, source_request(SOURCE + "\n\n" + SOURCE))
    assert duplicate.error["code"] == "QUALIFICATION_CONTRACT_INVALID"
    assert "ambiguous" in json.dumps(duplicate.checks)


def test_explanatory_prose_is_bounded_without_touching_status_or_quote():
    saved = {}

    def long(messages):
        value = quote_only(verdict(messages))
        value["claims"][0]["reason"] = "x" * 1006
        value["qualification_assessments"][0]["reason"] = "q" * 1006
        saved["raw"] = deepcopy(value)
        return value

    out = run(long)
    assert out.succeeded, out.error
    check = out.checks[0]
    assert json.loads(check["raw_text"]) == saved["raw"]
    assert len(check["typed_judgment_raw_aliases"]["claims"][0]["reason"]) == 800
    assert len(check["typed_judgment_raw_aliases"]["qualification_assessments"][0]["reason"]) == 200
    assert len(check["qualification_decision_derivative"]["bounded_prose"]) == 2
    assert (
        check["typed_judgment_raw_aliases"]["claims"][0]["status"]
        == saved["raw"]["claims"][0]["status"]
    )


def test_diagnostic_resource_limit_and_decision_quote_limits_are_retained():
    with pytest.raises(ValueError, match="DIAGNOSTIC_PROSE_RESOURCE_LIMIT"):
        decision_derivative({"claims": [{"reason": "x" * 16385}]})

    def bad(messages):
        value = quote_only(verdict(messages))
        value["qualification_assessments"][0]["supporting_quotes"][0]["quote"] = "x" * 601
        return value

    assert run(bad).error["code"] == "QUALIFICATION_CONTRACT_INVALID"


def test_deprecated_support_flag_is_observable_and_not_a_hidden_context_veto():
    def disagree(messages):
        value = verdict(messages)
        value["qualification_assessments"][0]["citation_support_exists"] = False
        return value

    out = run(disagree)
    assert out.succeeded, out.error
    gates = out.checks[0]["gate_decisions"]
    assert gates["qualification_context_accepted"] and gates["qualification_accepted"]
    assert gates["qualification_rejection_kind"] == "none"
    assert gates["semantic_disagreements"][0]["raw_support_flag"] is False
    assert gates["semantic_disagreements"][0]["bound_support_quote_present"] is True


def test_clear_context_and_source_rejection_are_separate_observable_decisions():
    def source_reject(messages):
        value = quote_only(verdict(messages))
        value["body_ok"] = False
        claim = value["claims"][0]
        claim["status"] = "partial"
        for unit in claim["units"]:
            unit.update(status="partial", conditions_preserved=False)
        return value

    out = run(source_reject)
    assert out.checks[0]["validation_state"] == "validated"
    gates = out.checks[0]["gate_decisions"]
    assert gates["qualification_context_accepted"] and gates["qualification_accepted"]
    assert gates["qualification_rejection_kind"] == "none"
    assert not gates["source_relation_accepted"] and not gates["overall_answer_accepted"]
    assert gates["semantic_disagreements"][0]["kind"] == "context_clear_with_source_rejection"


def test_clear_with_limiting_evidence_cannot_claim_contextual_rejection():
    def forged(messages):
        value = quote_only(verdict(messages))
        row = value["qualification_assessments"][0]
        row["limiting_quotes"] = deepcopy(row["supporting_quotes"])
        return value

    out = run(forged)
    assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"


def test_supported_source_claim_cannot_drop_its_required_bound_quote():
    assert run(lambda messages: quote_only(verdict(messages))).succeeded

    def empty(messages):
        value = quote_only(verdict(messages))
        value["qualification_assessments"][0]["supporting_quotes"] = []
        return value

    out = run(empty)
    assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"
    assert "QUALIFICATION_SUPPORTED_QUOTE_MISSING" in json.dumps(out.checks)


@pytest.mark.parametrize(
    "container", ["claims", "units", "qualification_assessments", "supporting_quotes"]
)
@pytest.mark.parametrize("value", [None, 7, [None]])
def test_malformed_containers_use_finite_contract_rejection(container, value):
    def malformed(messages):
        result = quote_only(verdict(messages))
        if container in {"claims", "qualification_assessments"}:
            result[container] = value
        elif container == "units":
            result["claims"][0][container] = value
        else:
            result["qualification_assessments"][0][container] = value
        return result

    out = run(malformed)
    assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"
    assert len(out.attempts) == 2
    assert not out.delivered_projection
