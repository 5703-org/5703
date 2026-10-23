"""Offline adapter controls; structural preservation is not source entailment.

The runner selects the source candidate. These portable tests use production
transport, original validators and publication gates with authored judgments.
No model, database, credentials or real provider boundary is used.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

import generation
from generation import GenerationService, RequestBudget, adapters, checked, providers
from generation import lossless_unit_findings_v1 as old
from generation import single_selection_findings_v2 as new
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck

sys.path.insert(0, str(Path(generation.__file__).resolve().parents[1] / "tests" / "unit"))
from test_enhancement_generation import Script, answer
from test_full_checker_encoding_integration82 import BODY, full_judgment, packet
from test_lossless_output_integration84 import fixture_request, vertex_config


@pytest.fixture(autouse=True)
def isolated_boundary_and_audit_clock(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Offline controls cannot open sockets or resolve DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)

    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(checked, "datetime", FixtureClock)


class FakeResponse:
    status = 200

    def __init__(self, raw):
        self.raw = raw
        self.headers = {"x-request-id": "authored-wire-contract87"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(
            {
                "choices": [{"message": {"content": self.raw}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
            }
        ).encode("utf-8")


def invalid_shape(wire, codec, context, fault):
    """Mutate only authored wire fixtures, never any saved provider evidence."""
    key = old.KEYS.get if codec is old else lambda value: value
    claims = wire[key("claims")]
    if fault == "missing_metadata":
        wire.pop("h" if codec is old else "context_sha256")
    elif fault == "stale_metadata":
        wire["h" if codec is old else "context_sha256"] = "0" * 64
    elif fault == "original_claim_id":
        claims[0][key("claim_id")] = context.packet["CLAIMS"][0]["claim_id"]
    elif fault == "missing_parent_status":
        claims[0].pop(key("status"))
    elif fault == "missing_citations":
        claims[0].pop(key("citations"))
    elif fault == "missing_claim":
        claims.pop()
    elif fault == "missing_unit":
        claims[0][key("units")].pop()
    elif fault == "foreign_source":
        claims[0][key("units")][0][key("fragment_ids")] = ["F999"]
    else:
        raise AssertionError("Unknown authored fault")


def execute(monkeypatch, policy, *, negative=False, fault=None):
    request = fixture_request(policy, checker_config=vertex_config())
    teacher = Script([answer(BODY, short_answer=None)])
    capture = []
    codec = new if policy == new.VERSION else old if policy == old.VERSION else None

    def fake_provider(envelope, timeout):
        body = json.loads(envelope.data)
        authored = full_judgment(body["messages"])
        if negative:
            authored["claims"][0]["units"][0].update(
                status="unsupported",
                fragment_ids=[],
                relation_preserved=False,
                conditions_preserved=False,
                reason="Authored missing condition; no support upgrade.",
            )
        original = deepcopy(authored)
        context = codec.build_context(packet(body["messages"])) if codec is not None else None
        if codec is None:
            raw = json.dumps(authored)
        else:
            wire = codec.encode_full(authored, context)
            if fault is not None:
                invalid_shape(wire, codec, context, fault)
            raw = codec.canonical(wire)
        capture.append({"body": body, "authored": original, "raw": raw, "context": context})
        assert authored == original
        return FakeResponse(raw)

    monkeypatch.setattr(adapters, "open_provider", fake_provider)
    checker = adapters.LLMAdapter(request.checker_config, api_key="synthetic-test-only")
    original_generate = checker.generate

    def observed_generate(*args, **kwargs):
        result = original_generate(*args, **kwargs)
        capture[-1].update(
            result=result, original_messages=args[0], response_schema=kwargs["response_schema"]
        )
        return result

    checker.generate = observed_generate
    outcome = GenerationService(adapter=teacher, checker_adapter=checker).generate(
        request, RequestBudget(max_calls=2)
    )
    assert len(teacher.calls) == len(capture) == 1
    assert outcome.budget["consumed_calls"] == 2
    return outcome, capture[0]


@pytest.mark.parametrize("negative", [False, True])
def test_both_policies_preserve_original_judgments_and_publication_gates(monkeypatch, negative):
    baseline, original = execute(monkeypatch, None, negative=negative)
    assert baseline.succeeded is (not negative), baseline.error
    for policy in (old.VERSION, new.VERSION):
        outcome, record = execute(monkeypatch, policy, negative=negative)
        assert outcome.succeeded == baseline.succeeded
        assert outcome.response == baseline.response
        assert outcome.delivered_projection == baseline.delivered_projection
        compared_attributions = []
        for checked_outcome in (outcome, baseline):
            attribution = deepcopy(checked_outcome.attribution)
            for claim in attribution["claims"]:
                assert (
                    claim["support"].pop("rubric_hash") == checked_outcome.checks[0]["rubric_hash"]
                )
            compared_attributions.append(attribution)
        assert compared_attributions[0] == compared_attributions[1]
        assert record["authored"] == original["authored"]
        assert packet(record["original_messages"]) == packet(original["original_messages"])
        assert record["body"]["messages"][-1] == record["original_messages"][-1]
        assert record["response_schema"] == compact_schema(ReliableUnitCheck)
        assert record["body"]["response_format"] == {"type": "json_object"}
        schema_text = next(
            m["content"] for m in record["body"]["messages"] if m["role"] == "system"
        )
        schema = json.loads(schema_text.rsplit("Match this JSON schema: ", 1)[1])
        assert schema == (old if policy == old.VERSION else new).wire_schema(record["context"])
        version_key, digest_key = (
            ("v", "h") if policy == old.VERSION else ("version", "context_sha256")
        )
        assert schema["properties"][digest_key]["const"] == record["context"].digest
        assert {version_key, digest_key}.issubset(schema["required"])
        for name in (
            "typed_judgment_raw_aliases",
            "actual_citation_bindings",
            "source_relation_assessment",
            "semantic_sufficiency",
        ):
            assert outcome.checks[0][name] == baseline.checks[0][name]
        result = record["result"]
        diagnostic = result.diagnostic["checker_transport"]
        assert json.loads(result.raw_text) == record["authored"]
        assert result.transport_raw_text == record["raw"]
        assert diagnostic["hydrated_full_v2_sha256"] == old.digest(record["authored"])
        assert (
            diagnostic["raw_compact_sha256"]
            == hashlib.sha256(record["raw"].encode("utf-8")).hexdigest()
        )
        assert (
            diagnostic["canonical_schema_sha256"]
            == old.build_context(packet(record["original_messages"])).canonical_schema_sha256
        )
        assert diagnostic["source_entailment_certified"] is False
        assert diagnostic["original_full_validators_required"] is True
        assert "decode_failure" not in diagnostic
        if negative:
            assert outcome.error["code"] == baseline.error["code"] == "SEMANTIC_CHECK_FAILED"
            assert outcome.response is None and not outcome.delivered_projection
            unit = outcome.checks[0]["source_relation_assessment"]["claims"][0]["obligations"][0]
            assert unit["status"] == "unsupported" and unit["fragment_ids"] == []
            assert unit["relation_preserved"] is unit["conditions_preserved"] is False
        else:
            assert outcome.checks[0]["accepted"] is baseline.checks[0]["accepted"] is True


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
@pytest.mark.parametrize(
    "fault",
    [
        "missing_metadata",
        "stale_metadata",
        "original_claim_id",
        "missing_parent_status",
        "missing_citations",
        "missing_claim",
        "missing_unit",
        "foreign_source",
    ],
)
def test_invalid_complete_contract_never_recovers_or_publishes(monkeypatch, policy, fault):
    outcome, record = execute(monkeypatch, policy, fault=fault)
    assert outcome.error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert outcome.response is None and not outcome.delivered_projection
    result = record["result"]
    assert result.raw_text == result.transport_raw_text == record["raw"]
    assert result.diagnostic["stage"] == "decode"
    diagnostic = result.diagnostic["checker_transport"]
    assert diagnostic["hydrated_full_v2_sha256"] is None
    assert diagnostic["source_entailment_certified"] is False
    detail = diagnostic["decode_failure"]["detail"]
    if policy == new.VERSION and fault in {"missing_metadata", "stale_metadata"}:
        assert detail == {
            "category": "CONTRACT_INVALID",
            "code": "SINGLE_SELECTION_METADATA_INVALID",
        }
    elif policy == new.VERSION and fault == "original_claim_id":
        assert detail == {
            "category": "CONTRACT_INVALID",
            "code": "SINGLE_SELECTION_CLAIM_REFERENCE_INVALID",
        }
    elif policy == old.VERSION and fault == "missing_unit":
        assert detail == {"category": "SCHEMA_VALIDATION_INVALID"}
    else:
        assert detail == {"category": "LOCAL_DECODE_ERROR"}


@pytest.mark.parametrize(
    "exception",
    [
        ValueError("Missing, unknown or stale projection metadata"),
        ValueError("Unknown claim alias"),
        ValueError("Unknown claim reference: untrusted-provider-text"),
        ValueError("Missing, unknown or stale single-selection metadata", "untrusted extra"),
        TypeError("Unknown claim reference"),
    ],
)
def test_legacy_or_dynamic_exception_content_is_never_exported(exception):
    assert providers._checker_decode_failure(exception) == {"category": "LOCAL_DECODE_ERROR"}


def test_exception_subclass_cannot_impersonate_trusted_static_error():
    class UntrustedValueError(ValueError):
        pass

    assert providers._checker_decode_failure(UntrustedValueError("Unknown claim reference")) == {
        "category": "LOCAL_DECODE_ERROR"
    }


def contract_repair_run(
    monkeypatch, policy, *, negative=False, max_calls=4, repeat_invalid=False, http_error=False
):
    """A model authors each new judgment; local code never repairs the first one."""
    request = fixture_request(policy, checker_config=vertex_config())
    teacher = Script([answer(BODY, short_answer=None)])
    codec = new if policy == new.VERSION else old
    capture = []

    class HttpFailure(FakeResponse):
        status = 400

        def read(self, limit):
            return json.dumps(
                {"error": {"message": "Authored HTTP rejection", "type": "bad_request"}}
            ).encode("utf-8")

    def fake_provider(envelope, timeout):
        body = json.loads(envelope.data)
        # Correction feedback follows the unchanged single original packet.
        packet_message = next(
            m
            for m in body["messages"]
            if m["role"] == "user" and m["content"].lstrip().startswith("{")
        )
        decoded_packet = packet([packet_message])
        authored = full_judgment([packet_message])
        if capture and negative:
            authored["claims"][0]["units"][0].update(
                status="unsupported",
                fragment_ids=[],
                relation_preserved=False,
                conditions_preserved=False,
                reason="Fresh authored rejection of unsupported condition.",
            )
        context = codec.build_context(decoded_packet)
        wire = codec.encode_full(authored, context)
        if not capture or repeat_invalid:
            wire["claims" if codec is new else "cs"][0]["basis" if codec is new else "b"] = (
                "guidance"
            )
        raw = codec.canonical(wire)
        capture.append(
            {
                "body": body,
                "packet": decoded_packet,
                "context": context,
                "authored": deepcopy(authored),
                "raw": raw,
            }
        )
        return HttpFailure(raw) if http_error else FakeResponse(raw)

    monkeypatch.setattr(adapters, "open_provider", fake_provider)
    checker = adapters.LLMAdapter(request.checker_config, api_key="synthetic-test-only")
    original_generate = checker.generate

    def observed_generate(*args, **kwargs):
        result = original_generate(*args, **kwargs)
        capture[-1].update(
            result=result, original_messages=args[0], response_schema=kwargs["response_schema"]
        )
        return result

    checker.generate = observed_generate
    outcome = GenerationService(adapter=teacher, checker_adapter=checker).generate(
        request, RequestBudget(max_calls=max_calls)
    )
    return outcome, teacher, capture


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
@pytest.mark.parametrize("negative", [False, True])
def test_decode_failure_uses_bounded_fresh_checker_contract_repair_and_all_original_gates(
    monkeypatch, policy, negative
):
    outcome, teacher, capture = contract_repair_run(monkeypatch, policy, negative=negative)
    assert len(teacher.calls) == 1 and len(capture) == 2
    assert outcome.budget["consumed_calls"] == 3 and outcome.budget["transient_retries"] == 0
    assert [attempt["purpose"] for attempt in outcome.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    first, fresh = capture
    assert first["result"].error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert first["result"].raw_text == first["result"].transport_raw_text == first["raw"]
    assert first["result"].diagnostic["checker_transport"]["hydrated_full_v2_sha256"] is None
    assert first["packet"] == fresh["packet"] and first["context"].digest == fresh["context"].digest
    assert first["response_schema"] == fresh["response_schema"] == compact_schema(ReliableUnitCheck)
    assert outcome.checks[0]["accepted"] is False
    assert outcome.checks[0]["checker_inconsistencies"] == [
        {
            "code": "CHECKER_SCHEMA_INVALID",
            "feedback_version": "checker_contract_feedback_v2",
            "parse_code": "CHECKER_TRANSPORT_INVALID",
        }
    ]
    assert json.loads(fresh["result"].raw_text) == fresh["authored"]
    assert fresh["result"].diagnostic["checker_transport"]["source_entailment_certified"] is False
    assert outcome.succeeded is (not negative), outcome.error
    if negative:
        assert outcome.response is None and not outcome.delivered_projection
        assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
        unit = outcome.checks[-1]["source_relation_assessment"]["claims"][0]["obligations"][0]
        assert unit["status"] == "unsupported" and unit["fragment_ids"] == []
        assert unit["relation_preserved"] is unit["conditions_preserved"] is False
    else:
        assert outcome.response["answer_text"] == BODY and outcome.response["citations"] == [
            "ev_001"
        ]
        assert outcome.checks[-1]["accepted"] is True
        assert outcome.checks[-1]["source_relation_assessment"]["accepted"] is True


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_decode_failure_with_no_spare_call_keeps_original_terminal_error(monkeypatch, policy):
    outcome, teacher, capture = contract_repair_run(monkeypatch, policy, max_calls=2)
    assert len(teacher.calls) == len(capture) == 1
    assert outcome.budget["consumed_calls"] == 2
    assert outcome.error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert outcome.response is None and not outcome.delivered_projection


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_repeated_invalid_decode_keeps_existing_single_correction_limit(monkeypatch, policy):
    outcome, teacher, capture = contract_repair_run(monkeypatch, policy, repeat_invalid=True)
    assert len(teacher.calls) == 1 and len(capture) == 2
    assert outcome.budget["consumed_calls"] == 3
    assert outcome.error["code"] == "CHECKER_INCONSISTENT"
    assert outcome.response is None and not outcome.delivered_projection
    assert all(
        record["result"].raw_text == record["result"].transport_raw_text == record["raw"]
        for record in capture
    )


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION])
def test_http_failure_never_enters_checker_contract_repair(monkeypatch, policy):
    outcome, teacher, capture = contract_repair_run(monkeypatch, policy, http_error=True)
    assert len(teacher.calls) == len(capture) == 1
    assert outcome.budget["consumed_calls"] == 2
    assert capture[0]["result"].diagnostic["http_status"] == 400
    assert capture[0]["result"].diagnostic["stage"] == "http"
    assert outcome.error["code"] not in {"CHECKER_TRANSPORT_INVALID", "CHECKER_INCONSISTENT"}
    assert outcome.response is None and not outcome.delivered_projection
