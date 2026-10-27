"""Answer-origin controls exercise contracts, not model semantic accuracy."""

from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator
from generation import GenerationService, RequestBudget
from generation import answer_delivery_v1 as audit, requirement_scope_v1
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


def fixture(text="Pressure (kPa): 2.5.", coverage="covered"):
    packet = {
        "CHECK_SCOPE": audit.CHECK_SCOPE,
        "REQUIREMENT_SCOPE": {"core_requirements": [{"id": "R1"}]},
        "PROPOSED_DELIVERY": {"response": {"answer_text": text}},
        "SOURCE_FRAGMENTS": [{"exact_text": "The source has 2.5 kPa."}],
    }
    base = {
        "type": "object",
        "required": ["requirements"],
        "additionalProperties": False,
        "properties": {"requirements": {"type": "array"}},
    }
    frozen, schema, wire = audit.prepare(packet, base, IDENTITY)
    reply = {
        "requirements": [{"requirement_id": "R1", "response_coverage": coverage}],
        "answer_delivery_audit": {
            "version": audit.POLICY,
            "binding_sha256": frozen["binding_sha256"],
            "requirements": [
                {"requirement_id": "R1", "quotes": [{"surface": "answer_text", "quote": text}]}
            ],
        },
    }
    return packet, base, frozen, schema, wire, reply


@pytest.mark.parametrize(
    "text",
    [
        "Pressure (kPa): 2.5.",
        "The pressure is 2500 Pa.",
        "The amount is 2.5e-3 mol.",
        "The pH is 7.00.",
        "The pressure is 2.5; its unit is omitted.",
    ],
)
def test_exact_origin_preserves_decision_but_does_not_certify_unit_semantics(text):
    packet, base, frozen, schema, wire, reply = fixture(text)
    Draft202012Validator.check_schema(schema)
    before = deepcopy(reply)
    result, receipt = audit.unwrap(reply, packet, base, IDENTITY, frozen, schema)
    assert result == {"requirements": reply["requirements"]}
    assert receipt["origin_valid"] and not receipt["semantic_completeness_verified"]
    assert not receipt["decisions_rewritten"] and reply == before
    assert "owner-a" not in str(wire)


@pytest.mark.parametrize(
    "defect", ["source", "prior", "blank", "duplicate", "surface", "missing", "id", "binding"]
)
def test_wrong_origin_or_binding_is_rejected(defect):
    packet, base, frozen, schema, wire, reply = fixture()
    row = reply["answer_delivery_audit"]["requirements"][0]
    if defect == "source":
        row["quotes"][0]["quote"] = "The source has 2.5 kPa."
    if defect == "prior":
        row["quotes"][0]["quote"] = "Previous answer: 2.5 kPa."
    if defect == "blank":
        row["quotes"][0]["quote"] = " "
    if defect == "duplicate":
        row["quotes"] *= 2
    if defect == "surface":
        row["quotes"][0]["surface"] = "SOURCE_FRAGMENTS"
    if defect == "missing":
        row["quotes"] = []
    if defect == "id":
        row["requirement_id"] = "R2"
    if defect == "binding":
        reply["answer_delivery_audit"]["binding_sha256"] = "0" * 64
    with pytest.raises(ResponseValidationError):
        audit.unwrap(reply, packet, base, IDENTITY, frozen, schema)


@pytest.mark.parametrize("field", ["owner", "session", "job", "request"])
def test_lifecycle_identity_drift_is_rejected(field):
    packet, base, frozen, schema, wire, reply = fixture()
    changed = {**IDENTITY, field: "other"}
    with pytest.raises(ResponseValidationError, match="binding changed"):
        audit.unwrap(reply, packet, base, changed, frozen, schema)


def test_empty_surface_is_explicit_error_not_invalid_schema():
    packet, base, *_ = fixture()
    packet["PROPOSED_DELIVERY"]["response"] = {"answer_text": ""}
    with pytest.raises(ValueError, match="SURFACE_REQUIRED"):
        audit.prepare(packet, base, IDENTITY)


def test_not_covered_remains_not_covered_and_needs_no_invented_quote():
    packet, base, frozen, schema, wire, reply = fixture(coverage="missing")
    reply["answer_delivery_audit"]["requirements"][0]["quotes"] = []
    result, _ = audit.unwrap(reply, packet, base, IDENTITY, frozen, schema)
    assert result["requirements"][0]["response_coverage"] == "missing"


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
