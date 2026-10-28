"""Answer-origin controls exercise contracts, not model semantic accuracy."""

from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator
from generation import GenerationService, RequestBudget
from generation import answer_delivery_target_v1 as audit, requirement_scope_v1
from generation.parser import ResponseValidationError
from test_assertion_provenance161 import (
    ScriptedTransport,
    decode_packet,
    mapped_request,
    private_draft,
    no_external_io,
)
from test_assertion_checker_schema185 import _checker

IDENTITY = {"owner": "owner-a", "session": "session-a", "job": "job-a", "request": "request-a"}


def request():
    req = mapped_request(
        requirement_scope_policy=requirement_scope_v1.POLICY, answer_delivery_policy=audit.POLICY
    )
    req.answer_delivery_identity = {**IDENTITY, "request": req.request_id}
    return req


def audited_checker(messages):
    value = _checker(messages)
    packet = decode_packet(messages)
    metadata = packet["ANSWER_DELIVERY_AUDIT"]
    value["answer_delivery_audit"] = {
        "version": audit.POLICY,
        "binding_sha256": metadata["binding_sha256"],
        "requirements": [
            {
                "requirement_id": rid,
                "quotes": [
                    {
                        "surface": "answer_text",
                        "quote": packet["PROPOSED_DELIVERY"]["response"]["answer_text"],
                    }
                ],
            }
            for rid in metadata["requirement_ids"]
        ],
    }
    return value


def test_native_generation_preserves_all_existing_gates_without_extra_calls():
    adapter = ScriptedTransport([private_draft(extra=True), audited_checker])
    outcome = GenerationService(adapter).generate(request(), RequestBudget(max_calls=2))
    assert outcome.succeeded, outcome.error
    messages, options = adapter.calls[1]
    assert options["response_schema_name"] == audit.SCHEMA_NAME
    assert "answer_delivery_audit" in options["response_schema"]["required"]
    assert "ANSWER DELIVERY AUDIT" in messages[0]["content"]
    assert len(adapter.calls) == outcome.budget["consumed_calls"] == 2
    assert outcome.budget["format_repairs"] == outcome.budget["transient_retries"] == 0


@pytest.mark.parametrize("fault", ["origin", "citation"])
def test_native_bad_origin_or_existing_citation_fault_cannot_publish(fault):
    def invalid(messages):
        value = audited_checker(messages)
        if fault == "origin":
            value["answer_delivery_audit"]["requirements"][0]["quotes"][0]["quote"] = (
                "Copied only from source."
            )
        else:
            value["claims"][0]["citations"][0]["evidence_id"] = "ev_foreign"
        return value

    adapter = ScriptedTransport([private_draft(extra=True), invalid])
    outcome = GenerationService(adapter).generate(request(), RequestBudget(max_calls=4))
    assert not outcome.succeeded and outcome.response is None
    assert len(adapter.calls) == 2
    assert outcome.budget["format_repairs"] == outcome.budget["transient_retries"] == 0


def test_ordinary_request_remains_unchanged():
    adapter = ScriptedTransport([private_draft(extra=True), _checker])
    req = mapped_request(requirement_scope_policy=requirement_scope_v1.POLICY)
    assert GenerationService(adapter).generate(req, RequestBudget(max_calls=2)).succeeded
    assert "ANSWER_DELIVERY_AUDIT" not in decode_packet(adapter.calls[1][0])


@pytest.mark.parametrize("defect", ["policy", "identity", "verification", "scope"])
def test_invalid_opt_in_stops_before_any_dispatch(defect):
    req = request()
    if defect == "policy":
        req.answer_delivery_policy = "unknown"
    if defect == "identity":
        req.answer_delivery_identity = None
    if defect == "verification":
        req.verification_mode = "unchecked"
    if defect == "scope":
        req.requirement_scope_policy = None
    adapter = ScriptedTransport([])
    result = GenerationService(adapter).generate(req, RequestBudget(max_calls=2))
    assert not result.succeeded and result.error and result.response is None
    assert not adapter.calls
