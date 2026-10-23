"""Exposed HTTP11 failures and authored native-service contract controls.

Scripted judgments prove routing and fail-closed behavior, not model quality.
"""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket

from pydantic import ValidationError
import pytest

from generation import GenerationService, RequestBudget
from generation import checker_claim_anchors_v2 as anchors
from generation import checker_claim_spans_v1 as spans
from generation.adapters import LLMAdapter, chat_value
from generation.checker_encoding import decode
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import assess_requirements
from test_checker_claim_spans210 import (
    Transport,
    authored_check,
    packet_from,
    pipeline_request,
    simple_packet,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "checker211"


def test_actual_generation_imports_resolve_to_this_candidate_source():
    import generation
    from generation import checked

    root = Path(__file__).resolve().parents[2]
    for module in (generation, checked, anchors, spans):
        assert Path(module.__file__).resolve().is_relative_to(root)


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempted = []

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("No network, actual provider transport or DB in phase211 controls")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    yield
    assert not attempted


def native_http11():
    pins = json.loads((FIXTURES / "pins.json").read_text("utf8"))
    values = {}
    for row in pins["rows"]:
        raw = (FIXTURES / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        values[row["path"]] = json.loads(raw)
    request = values["http-11-request.json"]
    packet = decode(json.loads(request["messages"][-1]["content"]))
    response = values["http-11-response.body"]
    assert response["choices"][0]["finish_reason"] == "stop"
    return packet, json.loads(response["choices"][0]["message"]["content"])


def anchored(raw, packet):
    """Authored structural conversion; does not repair contradictory judgments."""
    raw = deepcopy(raw)
    by_id = {a["claim_id"]: a for a in packet[anchors.ANCHORS]}
    rank = {"supported": 0, "partial": 1, "unsupported": 2}
    for claim in raw["claims"]:
        if claim["basis"] != "textbook":
            continue
        parts = claim["assertions"]
        negative = [p for p in parts if p["status"] != "supported"]
        claim["assertions"] = [
            {
                "anchor_id": by_id[claim["claim_id"]]["anchor_id"],
                "status": max((p["status"] for p in parts), key=rank.get),
                "fragment_ids": list(dict.fromkeys(f for p in parts for f in p["fragment_ids"])),
                "unestablished_quote": negative[0]["unestablished_quote"] if negative else "",
            }
        ]
    return raw


def evaluate(raw, packet):
    typed = anchors.OrdinaryCheck.model_validate(raw).model_dump()
    judgment, binding_issues = normalize_judgment(typed, packet["ACTUAL_CITATION_BINDINGS"])
    assert not binding_issues
    return anchors.assess(typed, judgment, packet)


def test_actual_http11_remains_negative_and_v1_reproduces_all_observed_contract_failures():
    packet, raw = native_http11()
    typed = spans.OrdinaryCheck.model_validate(raw).model_dump()
    judgment, _ = normalize_judgment(typed, packet["ACTUAL_CITATION_BINDINGS"])
    _, issues, _ = spans.assess(typed, judgment, packet)
    codes = [i["code"] for i in issues]
    assert codes.count("CLAIM_ASSERTION_COVERAGE_GAP") >= 6
    assert "CLAIM_NEGATIVE_WITHOUT_ASSERTED_DEFECT" in codes
    contract, _, _ = assess_requirements(
        typed,
        packet["CONTEXT_COVERAGE"],
        packet["SOURCE_FRAGMENTS"],
        answer_mode="textbook",
        teaching_mode="direct",
    )
    assert "REQUIREMENT_SUFFICIENCY_CONTRADICTION" in {i["code"] for i in contract}
    packet = anchors.prepare_packet(packet)
    effective, issues, audit = evaluate(anchored(raw, packet), packet)
    assert [i["code"] for i in issues] == ["CLAIM_NEGATIVE_WITHOUT_ASSERTED_DEFECT"]
    assert effective["body_ok"] is False and audit["contract_valid"] is False
    target = "claim_4b4f81ae4b5d9c1d50da6608_1"
    assert next(c for c in effective["claims"] if c["claim_id"] == target)["status"] == "partial"
    originals = {c["claim_id"]: c for c in packet["CLAIMS"]}
    for finding in audit["claims"]:
        part = finding["assertions"][0]
        assert part["quote"] == originals[finding["claim_id"]]["text"]
        assert part["quote"].endswith(".")
        assert (part["start"], part["end"]) == (0, len(part["quote"]))


def simple_assessment(text="🧬 A ≤ 0.5, B → C [ev_001].", *, status="supported", gap=""):
    packet = anchors.prepare_packet(simple_packet(text))
    assertion = {
        "anchor_id": packet[anchors.ANCHORS][0]["anchor_id"],
        "status": status,
        "fragment_ids": ["F1"],
        "unestablished_quote": gap,
    }
    row = {
        "claim_id": "c",
        "basis": "textbook",
        "status": status,
        "citations": [{"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": ["F1"]}],
        "assertions": [assertion],
        "reason": "Authored fixture.",
    }
    judgment = {"claims": [{"claim_id": "c", "status": status}], "body_ok": status == "supported"}
    return packet, {"claims": [row]}, judgment


def test_whole_anchor_includes_unicode_operators_decimals_citations_and_field_offsets():
    packet, raw, judgment = simple_assessment()
    _, issues, audit = anchors.assess(raw, judgment, packet)
    assert not issues
    part = audit["claims"][0]["assertions"][0]
    assert part["quote"] == "🧬 A ≤ 0.5, B → C [ev_001]."
    assert (part["start"], part["end"], part["field_start"], part["field_end"]) == (
        0,
        len(part["quote"]),
        7,
        7 + len(part["quote"]),
    )
    assert not audit["semantic_support_locally_certified"]
    assert not audit["positive_verdicts_locally_created"]


@pytest.mark.parametrize("mutation", ["id", "missing_packet", "text", "offset", "binding"])
def test_unknown_stale_missing_or_tampered_server_anchors_fail_closed(mutation):
    packet, raw, judgment = simple_assessment()
    if mutation == "id":
        raw["claims"][0]["assertions"][0]["anchor_id"] = "ca_unknown"
    elif mutation == "missing_packet":
        packet.pop(anchors.ANCHORS)
    elif mutation == "text":
        packet["CLAIMS"][0]["text"] = "A > 0.5."
    elif mutation == "offset":
        packet["CLAIMS"][0]["start"] += 1
    else:
        packet["ACTUAL_CITATION_BINDINGS"][0]["citations"][0]["allowed_fragment_ids"] = []
    _, issues, audit = anchors.assess(raw, judgment, packet)
    assert issues and not audit["contract_valid"]


@pytest.mark.parametrize("assertions", [[], [{"anchor_id": "x"}, {"anchor_id": "x"}]])
def test_missing_and_duplicate_assessment_records_fail_schema(assertions):
    packet, raw, _ = simple_assessment()
    raw["claims"][0]["assertions"] = assertions
    with pytest.raises(ValidationError):
        anchors.TextbookClaim.model_validate(raw["claims"][0])


def test_other_claim_anchor_or_globally_admitted_fragment_cannot_supply_own_proof():
    packet, raw, judgment = simple_assessment()
    other = deepcopy(packet["CLAIMS"][0])
    other.update(claim_id="other", text="Another claim.")
    packet["CLAIMS"].append(other)
    packet = anchors.prepare_packet(packet)
    raw["claims"][0]["assertions"][0]["anchor_id"] = packet[anchors.ANCHORS][1]["anchor_id"]
    assert anchors.assess(raw, judgment, packet)[1][0]["code"] == "CLAIM_ANCHOR_IDENTITY_INVALID"
    raw["claims"][0]["assertions"][0]["anchor_id"] = packet[anchors.ANCHORS][0]["anchor_id"]
    packet["SOURCE_FRAGMENTS"].append({"fragment_id": "GLOBAL", "evidence_id": "ev_999"})
    raw["claims"][0]["assertions"][0]["fragment_ids"] = ["GLOBAL"]
    assert (
        anchors.assess(raw, judgment, packet)[1][0]["code"]
        == "CLAIM_ASSERTION_OUTSIDE_OWN_SELECTION"
    )


@pytest.mark.parametrize("gap", ["", "invented equality", "[ev_001]"])
def test_negative_requires_exact_substantive_original_defect(gap):
    packet, raw, judgment = simple_assessment(status="partial", gap=gap)
    effective, issues, _ = anchors.assess(raw, judgment, packet)
    assert any(i["code"] == "CLAIM_ASSERTION_DEFECT_ANCHOR_INVALID" for i in issues)
    assert effective["claims"][0]["status"] == "partial"


@pytest.mark.parametrize(
    "reason", ["All good.", "Marking partial.", "完全支持。", "unsupported false"]
)
def test_reason_never_upgrades_raw_negative_or_overrides_structured_subspan(reason):
    packet, raw, judgment = simple_assessment(status="partial", gap="A ≤ 0.5")
    row = raw["claims"][0]
    row["reason"] = reason
    effective, issues, _ = anchors.assess(raw, judgment, packet)
    assert not issues and effective["claims"][0]["status"] == "partial"
    row["assertions"][0].update(status="supported", unestablished_quote="")
    effective, issues, _ = anchors.assess(raw, judgment, packet)
    assert issues[0]["code"] == "CLAIM_NEGATIVE_WITHOUT_ASSERTED_DEFECT"
    assert effective["claims"][0]["status"] == "partial"


def test_valid_negative_can_only_lower_optimistic_claim_and_never_become_protected():
    packet, raw, judgment = simple_assessment()
    raw["claims"][0]["assertions"][0].update(status="partial", unestablished_quote="A ≤ 0.5")
    effective, issues, audit = anchors.assess(raw, judgment, packet)
    assert not issues and effective["claims"][0]["status"] == "partial"
    assert audit["claims"][0]["raw_status"] == "supported"


def answer_check(messages, *, negative=False, bad_anchor=False):
    packet = packet_from(messages)
    result = anchored(authored_check(messages, initial=negative), packet)
    if bad_anchor:
        result["claims"][0]["assertions"][0]["anchor_id"] = "ca_stale"
    return result


def request_v2():
    return replace(pipeline_request(), checker_claim_policy=anchors.POLICY)


def test_real_generation_service_four_stage_repair_rebuilds_anchors_and_fresh_gate():
    first = "Osmosis is a special case of diffusion: it moves water through a semipermeable membrane [ev_002]. Osmosis is a special case of diffusion [ev_001]."
    repaired = "Osmosis is a special case of diffusion [ev_001]: it moves water through a semipermeable membrane [ev_002]."
    seen = {}

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        bad = next(c for c in data["original_claims"] if ":" in c["text"])
        safe = next(c for c in data["original_claims"] if ":" not in c["text"])
        assert bad["claim_id"] in data["editable_claim_ids"]
        assert safe["claim_id"] not in data["editable_claim_ids"]
        assert safe["claim_id"] in {c["claim_id"] for c in data["protected_exact_claims"]}
        assert data["claim_support_spans"]["contract_valid"]
        seen.update(bad=bad, safe=safe)
        return {
            "edits": [{"claim_id": bad["claim_id"], "replacement_text": repaired}],
            "append_answer_text": "",
        }

    adapter = Transport(
        [
            chat_value("answer", first, citations=["ev_001", "ev_002"]),
            lambda m: answer_check(m, negative=True),
            patch,
            answer_check,
        ]
    )
    out = GenerationService(adapter).generate(request_v2(), RequestBudget())
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == len(adapter.calls) == 4
    assert (
        repaired in out.response["answer_text"]
        and seen["safe"]["text"] in out.response["answer_text"]
    )
    first_packet, final_packet = (packet_from(adapter.calls[i][0]) for i in (1, 3))
    assert first_packet[anchors.ANCHORS] != final_packet[anchors.ANCHORS]
    assert all(out.checks[i]["claim_support_spans"]["version"] == anchors.POLICY for i in (0, 1))
    assert out.checks[0]["effective_body_ok"] is False
    assert out.checks[0]["typed_judgment_raw_aliases"]["body_ok"] is True
    for i in (1, 3):
        messages, kwargs = adapter.calls[i]
        assert anchors.INSTRUCTIONS in messages[0]["content"]
        assert spans.INSTRUCTIONS not in messages[0]["content"]
        assert kwargs["response_schema_name"] == anchors.SCHEMA


@pytest.mark.parametrize("bad_anchor", [False, True])
def test_final_negative_or_malformed_check_cannot_publish_or_exceed_four_calls(bad_anchor):
    first = "Osmosis is a special case of diffusion: it moves water [ev_002]. Osmosis is a special case of diffusion [ev_001]."

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        return {
            "edits": [
                {
                    "claim_id": data["editable_claim_ids"][0],
                    "replacement_text": "Osmosis is a special case of diffusion [ev_001]: it moves water [ev_002].",
                }
            ],
            "append_answer_text": "",
        }

    adapter = Transport(
        [
            chat_value("answer", first, citations=["ev_001", "ev_002"]),
            lambda m: answer_check(m, negative=True),
            patch,
            lambda m: answer_check(m, negative=True, bad_anchor=bad_anchor),
        ]
    )
    out = GenerationService(adapter).generate(request_v2(), RequestBudget())
    assert out.response is None
    assert out.error["code"] == ("CHECKER_INCONSISTENT" if bad_anchor else "SEMANTIC_CHECK_FAILED")
    assert out.budget["consumed_calls"] == len(adapter.calls) == 4


def test_malformed_initial_then_valid_negative_stops_before_uncheckable_repair():
    first = "Osmosis is a special case of diffusion: it moves water [ev_002]."
    adapter = Transport(
        [
            chat_value("answer", first, citations=["ev_002"]),
            lambda m: answer_check(m, bad_anchor=True),
            lambda m: answer_check(m, negative=True),
        ]
    )
    out = GenerationService(adapter).generate(request_v2(), RequestBudget())
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == len(adapter.calls) == 3
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]


def test_historical_v1_frozen_policy_still_has_original_schema_prompt_and_no_anchors():
    adapter = Transport(
        [
            chat_value(
                "answer", "Osmosis is a special case of diffusion [ev_001].", citations=["ev_001"]
            ),
            authored_check,
        ]
    )
    out = GenerationService(adapter).generate(pipeline_request(), RequestBudget())
    assert out.succeeded, out.error
    messages, kwargs = adapter.calls[1]
    assert kwargs["response_schema_name"] == spans.SCHEMA
    assert spans.INSTRUCTIONS in messages[0]["content"]
    assert anchors.ANCHORS not in packet_from(messages)
    assert spans.contract(request_v2()) is anchors
    assert spans.contract(pipeline_request()) is spans


@pytest.mark.parametrize("contradiction", ["negative_without_defect", "source_sufficiency"])
def test_real_service_rejects_contradictory_new_records_without_local_status_repair(contradiction):
    def invalid(messages):
        value = answer_check(messages)
        if contradiction == "negative_without_defect":
            value["claims"][0]["status"] = "partial"
            value["body_ok"] = False
        else:
            value["requirements"][0]["missing_information"] = (
                "A real source gap would contradict sufficient."
            )
        return value

    adapter = Transport(
        [
            chat_value(
                "answer", "Osmosis is a special case of diffusion [ev_001].", citations=["ev_001"]
            ),
            invalid,
            invalid,
        ]
    )
    out = GenerationService(adapter).generate(request_v2(), RequestBudget())
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == len(adapter.calls) == 3
    assert len(out.checks) == 2
    assert all(c["validation_state"] == "checker_inconsistent" for c in out.checks)
