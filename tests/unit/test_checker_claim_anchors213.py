"""Single-decision contract controls; scripted replies do not prove model quality."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket

from pydantic import ValidationError
import pytest

from generation import GenerationService, RequestBudget
from generation import checker_claim_anchors_v2 as previous
from generation import checker_claim_anchors_v3 as compact
from generation.adapters import LLMAdapter, chat_value
from generation.binding_repair import table_fragments
from generation.checker_encoding import encode
from generation.reliability_v4 import compact_schema, normalize_judgment
from test_checker_claim_spans210 import Transport, packet_from, simple_packet
from test_repair_citation_coordination212 import BODY, SAFE, SHORT, check, request_v4


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempted = []

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("No network/provider/DB in phase213 controls")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    yield
    assert not attempted


def request_v3():
    return replace(request_v4(), checker_claim_policy=compact.POLICY)


def primitive(canonical, packet):
    """Authored test adapter, never a migration of an actual negative capture."""
    result = {
        k: deepcopy(v)
        for k, v in canonical.items()
        if k not in {"claims", "requirements", "body_ok", "reason"}
    }
    result["version"] = compact.POLICY
    by_id = {c["claim_id"]: c for c in canonical["claims"]}
    result["claims"] = {}
    for key, target in packet[compact.CLAIM_TARGETS].items():
        row = deepcopy(by_id[target["claim_id"]])
        row.pop("claim_id")
        row.pop("reason")
        if row["basis"] == "textbook":
            row["unestablished_quote"] = row.pop("assertions")[0]["unestablished_quote"]
        result["claims"][key] = row
    by_id = {r["requirement_id"]: r for r in canonical["requirements"]}
    result["requirements"] = {}
    for key, target in packet[compact.REQUIREMENT_TARGETS].items():
        row = deepcopy(by_id[target["requirement_id"]])
        row.pop("requirement_id")
        result["requirements"][key] = row
    return result


def reply(messages, *, initial=False, unsupported_final=False):
    return primitive(
        check(messages, initial=initial, unsupported_final=unsupported_final), packet_from(messages)
    )


def tiny():
    text = "🧬 Stage A ≤ 0.5 uses X [ev_001]."
    packet = simple_packet(text)
    packet["CONTEXT_COVERAGE"] = {"requirements": [{"id": "r"}]}
    packet["SOURCE_FRAGMENTS"][0].update(block_kind="prose", complete_block=True)
    packet = compact.prepare_packet(packet)
    raw = {
        "version": compact.POLICY,
        "claims": {
            "C1": {
                "basis": "textbook",
                "status": "supported",
                "citations": [
                    {"evidence_id": "ev_001", "fragment_ids": ["F1"], "relation": "supporting"}
                ],
                "unestablished_quote": "",
            }
        },
        "requirements": {
            "R1": {
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [{"evidence_id": "ev_001", "fragment_id": "F1", "quote": text}],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored source assessment.",
            }
        },
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": False,
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": "not_applicable",
        "tutor_question_ok": True,
        "non_repetitive_next_action": True,
    }
    return packet, raw


def test_dynamic_required_objects_single_status_and_transparent_projection():
    packet, raw = tiny()
    schema = compact_schema(compact.wire_model(packet))
    compact.validate_wire_schema(packet, schema)
    assert set(schema["properties"]) == set(raw)
    assert "body_ok" not in schema["properties"] and "reason" not in schema["properties"]
    canonical, audit = compact.project(raw, packet)
    assert canonical["body_ok"] is True
    assert (
        canonical["claims"][0]["status"]
        == canonical["claims"][0]["assertions"][0]["status"]
        == "supported"
    )
    assert audit["canonical_origin"] == "server_versioned_projection"
    assert audit["reason_origin"].startswith("server_generated")
    assert (
        not audit["positive_verdicts_locally_created"]
        and not audit["semantic_support_locally_certified"]
    )
    assert canonical["claims"][0]["reason"].startswith("Server projection")
    assert (
        audit["claim_targets"]["C1"]["text_sha256"]
        == hashlib.sha256(packet["CLAIMS"][0]["text"].encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_claim",
        "foreign_claim",
        "missing_requirement",
        "foreign_requirement",
        "body",
        "reason",
        "nested",
    ],
)
def test_missing_foreign_or_legacy_decision_channels_are_not_filled_or_ignored(mutation):
    packet, raw = tiny()
    if mutation == "missing_claim":
        raw["claims"].pop("C1")
    elif mutation == "foreign_claim":
        raw["claims"]["C99"] = deepcopy(raw["claims"]["C1"])
    elif mutation == "missing_requirement":
        raw["requirements"].pop("R1")
    elif mutation == "foreign_requirement":
        raw["requirements"]["R99"] = deepcopy(raw["requirements"]["R1"])
    elif mutation == "nested":
        raw["claims"]["C1"]["assertions"] = []
    elif mutation == "body":
        raw["body_ok"] = False
    else:
        raw["claims"]["C1"]["reason"] = "Marking partial."
    with pytest.raises(ValidationError):
        compact.project(raw, packet)


@pytest.mark.parametrize("mutation", ["claim", "anchor", "binding"])
def test_server_target_tampering_is_rejected_before_schema_projection(mutation):
    packet, raw = tiny()
    if mutation == "claim":
        packet[compact.CLAIM_TARGETS]["C1"]["claim_id"] = "foreign"
    elif mutation == "anchor":
        packet["CLAIMS"][0]["text"] += " silently changed"
    else:
        packet["ACTUAL_CITATION_BINDINGS"][0]["citations"][0]["allowed_fragment_ids"] = []
    with pytest.raises(ValueError, match="TARGET_MAP_INVALID"):
        compact.project(raw, packet)


@pytest.mark.parametrize(
    "mutation", ["positive_with_defect", "negative_without_defect", "foreign_source"]
)
def test_wrong_union_or_inconsistent_single_negative_witness_remains_invalid(mutation):
    packet, raw = tiny()
    row = raw["claims"]["C1"]
    if mutation == "positive_with_defect":
        row["unestablished_quote"] = "uses X"
    elif mutation == "negative_without_defect":
        row["status"] = "partial"
    else:
        row["citations"][0]["fragment_ids"] = ["GLOBAL"]
    canonical, _ = compact.project(raw, packet)
    normalized, binding_issues = normalize_judgment(canonical, packet["ACTUAL_CITATION_BINDINGS"])
    _, issues, _ = compact.assess(canonical, normalized, packet)
    assert issues or binding_issues


def test_honest_negative_primitive_is_negative_without_reason_parsing():
    packet, raw = tiny()
    raw["claims"]["C1"].update(status="partial", unestablished_quote="uses X")
    canonical, _ = compact.project(raw, packet)
    normalized, _ = normalize_judgment(canonical, packet["ACTUAL_CITATION_BINDINGS"])
    effective, issues, audit = compact.assess(canonical, normalized, packet)
    assert (
        not issues
        and canonical["body_ok"] is False
        and effective["claims"][0]["status"] == "partial"
    )
    assert audit["raw_model_records"] == "primitive_judgment_raw_aliases.claims"


def test_all_existing_nontextbook_basis_proofs_remain_typed_and_never_default_to_textbook():
    packet, raw = tiny()
    for decision in [
        {"basis": "problem_input", "status": "supported", "problem_quote": "Stage A uses X"},
        {"basis": "nonfactual"},
        {"basis": "evidence_limitation"},
        {"basis": "general_knowledge", "status": "partial"},
    ]:
        candidate = deepcopy(raw)
        candidate["claims"]["C1"] = decision
        canonical, _ = compact.project(candidate, packet)
        assert canonical["claims"][0]["basis"] == decision["basis"]
    candidate = deepcopy(raw)
    candidate["claims"]["C1"] = {
        "basis": "derived_calculation",
        "status": "supported",
        "citations": [],
    }
    with pytest.raises(ValidationError):
        compact.project(candidate, packet)


@pytest.mark.parametrize("encoding", ["objects", "table", "lossless"])
def test_guard_schema_helper_resolves_only_exact_native_packet_encodings(encoding):
    packet, _ = tiny()
    encoded = (
        packet
        if encoding == "objects"
        else table_fragments(packet)
        if encoding == "table"
        else encode(packet)
    )
    assert compact.decoded_wire_packet(encoded) == packet
    schema = compact_schema(compact.wire_model(packet))
    with pytest.raises(ValueError, match="EXACT_WIRE_SCHEMA"):
        compact.validate_wire_schema(packet, compact_schema(previous.OrdinaryCheck))
    schema["required"].remove("claims")
    with pytest.raises(ValueError, match="EXACT_WIRE_SCHEMA"):
        compact.validate_wire_schema(packet, schema)


def test_exposed_18_19_remain_failures_and_are_never_optimistically_projected():
    fixtures = Path(__file__).parents[1] / "fixtures/checker213"
    pins = json.loads((fixtures / "pins.json").read_text("utf-8"))
    records = {}
    for row in pins["rows"]:
        raw = (fixtures / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        records[row["path"]] = json.loads(raw)
    packet, _ = tiny()
    for number in (18, 19):
        response = records[f"http-{number}-response.body"]
        assert response["choices"][0]["finish_reason"] == "stop"
        raw = json.loads(response["choices"][0]["message"]["content"])
        assert len(raw["claims"]) == (2 if number == 18 else 7)
        assert raw["body_ok"] is False
        assert all(c["status"] == "supported" for c in raw["claims"])
        with pytest.raises(ValidationError):
            compact.project(raw, packet)


def run_pipeline(*, final_negative=False, malformed_first=False, legacy=False, final_gate=None):
    seen = {}

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        assert "REPAIR_FIELD_COORDINATION_JSON:" in messages[-1]["content"]
        seen["protected"] = data["protected_exact_claims"]
        return {
            "edits": [
                {
                    "claim_id": c["claim_id"],
                    "replacement_text": "Osmosis requires no cellular energy [ev_003].",
                }
                for c in data["original_claims"]
                if c["claim_id"] in data["editable_claim_ids"]
            ],
            "append_answer_text": "",
        }

    def initial(messages):
        value = reply(messages, initial=True)
        if malformed_first:
            value["claims"].pop(next(iter(value["claims"])))
        return value

    generated = chat_value("answer", BODY, citations=["ev_002", "ev_001"])
    generated["short_answer"] = SHORT
    responses = [generated, initial]
    if malformed_first:
        responses += [lambda m: reply(m, initial=True)]
    else:

        def final(messages):
            result = reply(messages, unsupported_final=final_negative)
            if final_gate is not None:
                result[final_gate[0]] = final_gate[1]
            return result

        responses += [patch, final]
    if legacy:

        def legacy_final(messages):
            value = check(messages)
            if final_gate is not None:
                value[final_gate[0]] = final_gate[1]
            return value

        responses = [generated, lambda m: check(m, initial=True), patch, legacy_final]
    transport = Transport(responses)
    request = request_v4() if legacy else request_v3()
    out = GenerationService(transport).generate(request, RequestBudget())
    return out, transport, seen


def test_real_service_single_negative_routes_repair_and_fresh_whole_check_in_four_calls():
    out, transport, seen = run_pipeline()
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == len(transport.calls) == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    for field in ("answer_text", "short_answer"):
        assert SAFE in out.response[field] and "[ev_003]" in out.response[field]
    for index, call in enumerate((transport.calls[1], transport.calls[3])):
        messages, kwargs = call
        packet = packet_from(messages)
        compact.validate_wire_schema(packet, kwargs["response_schema"])
        assert kwargs["response_schema_name"] == compact.SCHEMA
        assert "Return each required object key exactly once" in messages[0]["content"]
        assert "body_ok MUST be false" not in messages[0]["content"]
        audit = out.checks[index]
        assert "typed_judgment_raw_aliases" not in audit
        assert isinstance(audit["primitive_judgment_raw_aliases"]["claims"], dict)
        assert isinstance(audit["projected_typed_judgment_aliases"]["claims"], list)
        assert not audit["primitive_projection"]["semantic_support_locally_certified"]
    assert (
        packet_from(transport.calls[1][0])[compact.ANCHORS]
        != packet_from(transport.calls[3][0])[compact.ANCHORS]
    )
    assert out.checks[0]["effective_body_ok"] is False and seen["protected"]


def test_real_final_negative_cannot_publish_and_malformed_correction_reserves_repair_pair():
    for negative, malformed, expected_calls in [(True, False, 4), (False, True, 3)]:
        out, transport, _ = run_pipeline(final_negative=negative, malformed_first=malformed)
        assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert out.budget["consumed_calls"] == len(transport.calls) == expected_calls


def test_v2_frozen_prompt_wire_and_v4_repair_behavior_are_unchanged():
    out, transport, _ = run_pipeline(legacy=True)
    assert out.succeeded, out.error
    assert transport.calls[1][1]["response_schema_name"] == previous.SCHEMA
    assert previous.INSTRUCTIONS in transport.calls[1][0][0]["content"]
    assert "primitive_projection" not in out.checks[0]
    assert compact.CLAIM_TARGETS not in packet_from(transport.calls[1][0])


@pytest.mark.parametrize(
    "gate",
    [
        ("complete_answer", False),
        ("coverage", "none"),
        ("tutor_question_ok", False),
    ],
)
def test_independent_final_semantic_gate_cannot_be_overridden_by_positive_support(gate):
    out, transport, _ = run_pipeline(final_gate=gate)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(transport.calls) == out.budget["consumed_calls"] == 4
    assert out.checks[-1]["projected_typed_judgment_aliases"][gate[0]] == gate[1]


def test_all_requirement_axes_and_independent_coverage_flags_remain_model_decisions():
    packet, raw = tiny()
    raw["requirements"]["R1"].update(
        relevance="unrelated",
        sufficiency="partial",
        conditions_preserved=False,
        response_coverage="partial",
        missing_information="An authored source gap.",
    )
    raw.update(
        coverage="supported_partial",
        missing_facets=["An authored facet."],
        limitations_explicit=True,
        complete_answer=False,
        non_repetitive_next_action=False,
        cumulative_ok=False,
        suggestions_ok=False,
        evidence_display_ok=False,
        attempt_evaluation_ok=False,
    )
    canonical, audit = compact.project(raw, packet)
    assert {k: v for k, v in canonical["requirements"][0].items() if k != "requirement_id"} == raw[
        "requirements"
    ]["R1"]
    for key in raw:
        if key not in {"claims", "requirements", "version"}:
            assert canonical[key] == raw[key]
    assert audit["wire_schema_sha256"] != audit["canonical_schema_sha256"]


def test_actual_imports_resolve_to_candidate_not_main():
    from generation import checked

    root = Path(__file__).resolve().parents[2]
    for module in (compact, checked):
        assert Path(module.__file__).resolve().is_relative_to(root)


@pytest.mark.parametrize("gate", [("scope_ok", False), ("specific_help", False)])
def test_direct_gate_applicability_matches_historical_v2_without_rewriting_flags(gate):
    old, _, _ = run_pipeline(legacy=True, final_gate=gate)
    new, _, _ = run_pipeline(final_gate=gate)
    assert old.succeeded and new.succeeded
    assert old.checks[-1]["typed_judgment_raw_aliases"][gate[0]] is False
    assert new.checks[-1]["projected_typed_judgment_aliases"][gate[0]] is False
    # These two teaching flags are not active rejection gates in the existing
    # direct branch. This protocol change preserves, rather than broadens, it.
