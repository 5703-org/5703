"""Exact saved checker rows and offline normal-service wire contract controls."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from generation import GenerationService, RequestBudget
from generation import assertion_provenance_v1 as transport
from generation import requirement_scope_v1
from generation.providers import payload
from generation.reliability_v4 import compact_schema

from test_assertion_provenance161 import (
    ScriptedTransport,
    authored_full_checker,
    decode_packet,
    mapped_request,
    private_draft,
)


FIXTURE = Path(__file__).parents[1] / "fixtures/assertion185/extra-row161.json"
CAPTURE = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _ids(schema):
    definitions = schema["$defs"]
    return [
        definitions[variant["$ref"].rsplit("/", 1)[1]]["properties"]["claim_id"]
        for variant in schema["properties"]["claims"]["items"]["anyOf"]
    ]


def _claim_errors(schema, rows):
    """Validate actual rows against only the unchanged enclosing claims contract."""
    validator = Draft202012Validator(
        {
            "$defs": schema["$defs"],
            "type": "object",
            "required": ["claims"],
            "properties": {"claims": schema["properties"]["claims"]},
        }
    )
    return list(validator.iter_errors({"claims": rows}))


def _checker(messages):
    value = authored_full_checker(messages)
    packet = decode_packet(messages)
    if "REQUIREMENT_SCOPE" in packet:
        for name in requirement_scope_v1.DERIVED_SCOPE_FIELDS:
            value.pop(name, None)
        value["requirement_scope_version"] = requirement_scope_v1.POLICY
        value["requirement_scope_sha256"] = packet["REQUIREMENT_SCOPE"]["scope_sha256"]
        value["optional_extensions"] = []
        for row in value["requirements"]:
            row["necessity"] = "required"
            row["response_missing_information"] = ""
    return value


def test_saved_original_extra_row_is_admitted_before_transport_binding_but_still_blocked_locally():
    source = Path(__file__).parents[2] / CAPTURE["source_path"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == CAPTURE["source_sha256"]
    original = deepcopy(CAPTURE)
    rows = CAPTURE["original_checker_rows"]
    schema = compact_schema(transport.AssertionCheck)
    assert not _claim_errors(schema, rows)
    assert rows[-1]["claim_id"] == "practice_present"
    assert transport.assess_judgment({"claims": rows}, CAPTURE["provenance"]) == [
        {"code": "ASSERTION_CHECK_COVERAGE_INVALID"}
    ]
    assert CAPTURE["answer_id"] is None
    assert CAPTURE["original_terminal"]["code"] == "CHECKER_INCONSISTENT"
    assert CAPTURE == original


def test_bound_schema_rejects_actual_saved_extra_row_without_changing_its_three_partial_verdicts():
    schema = compact_schema(transport.AssertionCheck)
    before = deepcopy(schema)
    capture_before = deepcopy(CAPTURE)
    bound = transport.bind_checker_schema(schema, CAPTURE["provenance"])
    assert _claim_errors(bound, CAPTURE["original_checker_rows"])
    original_rows = CAPTURE["original_checker_rows"][:3]
    assert not _claim_errors(bound, original_rows)
    assert [row["status"] for row in original_rows] == ["partial"] * 3
    assert schema == before and CAPTURE == capture_before


@pytest.mark.parametrize("defect", ["foreign", "missing", "extra", "duplicate"])
def test_foreign_missing_extra_or_duplicate_rows_never_become_accepted(defect):
    rows = deepcopy(CAPTURE["original_checker_rows"][:3])
    if defect == "foreign":
        rows[0]["claim_id"] = "practice_present"
    elif defect == "missing":
        rows.pop()
    elif defect == "extra":
        rows.append(deepcopy(CAPTURE["original_checker_rows"][-1]))
    else:
        rows[1] = deepcopy(rows[0])
    schema = transport.bind_checker_schema(
        compact_schema(transport.AssertionCheck), CAPTURE["provenance"]
    )
    # A set enum plus cardinality cannot certify uniqueness. The existing exact-ID
    # guard still rejects duplicates even when a provider ignores the schema.
    if defect != "duplicate":
        assert _claim_errors(schema, rows)
    assert transport.assess_judgment({"claims": rows}, CAPTURE["provenance"]) == [
        {"code": "ASSERTION_CHECK_COVERAGE_INVALID"}
    ]


@pytest.mark.parametrize("scoped", [False, True])
def test_normal_service_passes_bound_schema_to_the_real_provider_payload_compiler(scoped):
    request = mapped_request(
        requirement_scope_policy=requirement_scope_v1.POLICY if scoped else None
    )
    adapter = ScriptedTransport([private_draft(extra=True), _checker])
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert out.succeeded, out.error
    messages, options = adapter.calls[1]
    packet = decode_packet(messages)
    expected = [row["claim_id"] for row in packet["CLAIMS"]]
    schema = options["response_schema"]
    assert schema["properties"]["claims"]["minItems"] == len(expected)
    assert schema["properties"]["claims"]["maxItems"] == len(expected)
    assert len(_ids(schema)) == 5
    assert all(field["enum"] == expected for field in _ids(schema))
    # Use the actual provider compiler, with no key lookup or dispatch. Structured
    # transport carries this very schema and all prompt/source bytes unchanged.
    config = request.checker_config or request.config
    wire = payload(config, messages, schema, options["response_schema_name"])
    assert wire["response_format"]["json_schema"]["schema"] == schema
    assert wire["messages"] == messages
    if scoped:
        assert schema["properties"]["requirement_scope_sha256"]["const"]
        assert "core_knowledge_complete" not in schema["properties"]
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0


@pytest.mark.parametrize("scoped", [False, True])
def test_provider_ignoring_bound_contract_still_cannot_publish_or_trigger_repeated_check(scoped):
    request = mapped_request(
        requirement_scope_policy=requirement_scope_v1.POLICY if scoped else None
    )

    def ignored_contract(messages):
        value = _checker(messages)
        value["claims"].append(deepcopy(CAPTURE["original_checker_rows"][-1]))
        return value

    adapter = ScriptedTransport([private_draft(extra=True), ignored_contract])
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=4))
    assert out.response is None and out.delivered_projection == {}
    assert out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0
    assert not any(row["published"] for row in out.drafts)


def test_empty_assertion_inventory_requires_empty_output_without_an_invalid_empty_enum():
    provenance = {"version": transport.POLICY, "assertions": []}
    schema = transport.bind_checker_schema(compact_schema(transport.AssertionCheck), provenance)
    Draft202012Validator.check_schema(schema)
    assert not _claim_errors(schema, [])
    assert _claim_errors(schema, CAPTURE["original_checker_rows"][:1])
    assert transport.assess_judgment({"claims": []}, provenance) == []


@pytest.mark.parametrize("response_type", ["social", "clarification", "refusal"])
def test_nonfactual_generated_row_needs_no_source_to_bind_its_checker_identity(response_type):
    value = private_draft(text="Please clarify the transport you mean.", ids=[])
    value["response_type"] = response_type
    value["refusal_reason"] = "INSUFFICIENT_EVIDENCE" if response_type == "refusal" else None
    _, provenance = transport.compile_draft(value, [])
    row = {
        "claim_id": provenance["assertions"][0]["claim_id"],
        "basis": "nonfactual",
        "reason": "Authored control for a nonfactual output row.",
    }
    bound = transport.bind_checker_schema(compact_schema(transport.AssertionCheck), provenance)
    assert not _claim_errors(bound, [row])
    assert transport.assess_judgment({"claims": [row]}, provenance) == []


@pytest.mark.parametrize(
    "defect", ["duplicate", "foreign_version", "bad_schema", "unknown_ref", "malformed_ref"]
)
def test_invalid_binding_inputs_fail_closed(defect):
    provenance = deepcopy(CAPTURE["provenance"])
    schema = compact_schema(transport.AssertionCheck)
    if defect == "duplicate":
        provenance["assertions"][1]["claim_id"] = provenance["assertions"][0]["claim_id"]
    elif defect == "foreign_version":
        provenance["version"] = "unknown"
    elif defect == "bad_schema":
        schema["properties"]["claims"] = {"type": "string"}
    else:
        reference = "#/$defs/unknown" if defect == "unknown_ref" else "foreign.json#/claim"
        schema["properties"]["claims"]["items"]["anyOf"][0]["$ref"] = reference
    original_schema, original_provenance = deepcopy(schema), deepcopy(provenance)
    with pytest.raises(ValueError, match="ASSERTION_CHECK_SCHEMA_BINDING_INVALID"):
        transport.bind_checker_schema(schema, provenance)
    assert schema == original_schema and provenance == original_provenance
