"""Exact exposed captures and authored transport controls, not model quality scores."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation import checker_claim_spans_v1 as spans
from generation.adapters import LLMAdapter, chat_value
from generation.checker_encoding import decode
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import protected_claims
from generation.types import ProviderResult


FIXTURES = Path(__file__).parents[1] / "fixtures" / "checker210"
GAP = "claim_4b4f81ae4b5d9c1d50da6608_1"
ENERGY = "claim_3828fbf489079e04e37b000e_1"


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempted = []

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("No network, actual model transport or DB in phase210 unit tests")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    yield
    assert not attempted


def captured(number):
    pins = json.loads((FIXTURES / "pins.json").read_text("utf8"))
    values = {}
    for row in pins["rows"]:
        raw = (FIXTURES / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        values[row["path"]] = json.loads(raw)
    request = values[f"http-{number:02d}-request.json"]
    packet = decode(json.loads(request["messages"][-1]["content"]))
    response = values[f"http-{number:02d}-response.body"]
    return packet, json.loads(response["choices"][0]["message"]["content"])


def part(quote, status="supported", ids=("F029",), gap=""):
    return {"quote": quote, "status": status, "fragment_ids": list(ids), "unestablished_quote": gap}


def add_whole_assertions(raw, packet):
    raw = deepcopy(raw)
    claims = {row["claim_id"]: row for row in packet["CLAIMS"]}
    for row in raw["claims"]:
        if row["basis"] == "textbook":
            text = claims[row["claim_id"]]["text"]
            ids = [
                fid
                for ref in row["citations"]
                if ref["relation"] == "supporting"
                for fid in ref["fragment_ids"]
            ]
            row["assertions"] = [
                part(text, row["status"], ids, "" if row["status"] == "supported" else text)
            ]
    return raw


def evaluate(raw, packet):
    typed = spans.OrdinaryCheck.model_validate(raw).model_dump()
    normalized, binding_issues = normalize_judgment(typed, packet["ACTUAL_CITATION_BINDINGS"])
    assert not binding_issues
    return spans.assess(typed, normalized, packet)


def test_actual_q03_intro_gap_is_not_protected_or_repaired_by_another_claim():
    packet, raw = captured(4)
    raw = add_whole_assertions(raw, packet)
    text = next(row["text"] for row in packet["CLAIMS"] if row["claim_id"] == GAP)
    row = next(row for row in raw["claims"] if row["claim_id"] == GAP)
    prefix, rest = text.split(":", 1)
    row["assertions"] = [part(prefix + ":", "partial", (), prefix), part(rest, ids=("F029",))]
    old = normalize_judgment(raw, packet["ACTUAL_CITATION_BINDINGS"])[0]
    assert GAP in {row["claim_id"] for row in protected_claims(packet["CLAIMS"], old, [])}
    effective, issues, audit = evaluate(raw, packet)
    assert not issues and row["status"] == "supported"
    assert next(row for row in effective["claims"] if row["claim_id"] == GAP)["status"] == "partial"
    assert GAP not in {row["claim_id"] for row in protected_claims(packet["CLAIMS"], effective, [])}
    observation = next(row for row in audit["claims"] if row["claim_id"] == GAP)
    assert (observation["raw_status"], observation["effective_status"]) == ("supported", "partial")
    final_packet, _ = captured(6)
    assert text == next(row["text"] for row in final_packet["CLAIMS"] if row["claim_id"] == GAP)
    assert any(
        "Osmosis is a special case of diffusion [ev_001]" in row["text"]
        for row in final_packet["CLAIMS"]
    )


@pytest.mark.parametrize("number", [4, 6])
def test_admitted_or_other_claim_fragment_cannot_support_this_claim(number):
    packet, raw = captured(number)
    raw = add_whole_assertions(raw, packet)
    row = next(row for row in raw["claims"] if row["claim_id"] == GAP)
    row["assertions"][0]["fragment_ids"] = ["F002"]
    _, issues, _ = evaluate(raw, packet)
    assert any(row["code"] == "CLAIM_ASSERTION_OUTSIDE_OWN_SELECTION" for row in issues)


def test_exact_conjunction_is_two_supported_propositions_but_invented_equivalence_is_invalid():
    packet, raw = captured(6)
    raw = add_whole_assertions(raw, packet)
    row = next(row for row in raw["claims"] if row["claim_id"] == ENERGY)
    row["status"] = "supported"
    text = row["assertions"][0]["quote"]
    left, right = text.split(", and ", 1)
    row["assertions"] = [
        part(left + ",", ids=("F058",)),
        part("and " + right, ids=("F008", "F009")),
    ]
    effective, issues, _ = evaluate(raw, packet)
    assert not issues
    assert next(c for c in effective["claims"] if c["claim_id"] == ENERGY)["status"] == "supported"
    row["assertions"][1] = part(
        "diffusion is passive transport", "partial", (), "diffusion is passive transport"
    )
    _, issues, _ = evaluate(raw, packet)
    assert any(i["code"] == "CLAIM_ASSERTION_ANCHOR_INVALID" for i in issues)


@pytest.mark.parametrize(
    "reason",
    ["Marking partial.", "完全支持；但缺少证据", "unsupported negative false", "All good."],
)
def test_prose_reason_does_not_change_structured_routing(reason):
    packet, raw = captured(4)
    raw = add_whole_assertions(raw, packet)
    row = next(row for row in raw["claims"] if row["claim_id"] == GAP)
    row["reason"] = reason
    row["assertions"][0].update(status="partial", unestablished_quote="special case of diffusion")
    effective, issues, _ = evaluate(raw, packet)
    assert not issues
    assert next(c for c in effective["claims"] if c["claim_id"] == GAP)["status"] == "partial"


def simple_packet(text):
    return {
        "CLAIMS": [
            {
                "claim_id": "c",
                "text": text,
                "start": 7,
                "end": 7 + len(text),
                "answer_field": "short_answer",
            }
        ],
        "ACTUAL_CITATION_BINDINGS": [
            {
                "claim_id": "c",
                "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F1"]}],
            }
        ],
        "SOURCE_FRAGMENTS": [{"fragment_id": "F1", "evidence_id": "ev_001", "exact_text": text}],
    }


def simple_assessment(text, assertions, status="supported"):
    row = {
        "claim_id": "c",
        "basis": "textbook",
        "status": status,
        "reason": "Fixture.",
        "citations": [{"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": ["F1"]}],
        "assertions": assertions,
    }
    judgment = {"claims": [{"claim_id": "c", "status": status}], "body_ok": status == "supported"}
    return spans.assess({"claims": [row]}, judgment, simple_packet(text))


@pytest.mark.parametrize("middle", ["→", "≤", "≥", "≠", "¬", "−", "×", ".", ","])
def test_relationship_operators_and_decimal_punctuation_cannot_be_unassessed(middle):
    _, issues, _ = simple_assessment(
        "A" + middle + "B", [part("A", ids=("F1",)), part("B", ids=("F1",))]
    )
    assert any(i["code"] == "CLAIM_ASSERTION_COVERAGE_GAP" for i in issues)


def test_unicode_offsets_bind_actual_auxiliary_field_and_negative_is_never_upgraded():
    text = "🧬 A ≤ B."
    effective, issues, audit = simple_assessment(text, [part(text, ids=("F1",))], status="partial")
    assert any(i["code"] == "CLAIM_NEGATIVE_WITHOUT_ASSERTED_DEFECT" for i in issues)
    assert effective["claims"][0]["status"] == "partial"
    _, issues, audit = simple_assessment(
        text, [part(text, "partial", ("F1",), "A ≤ B")], status="partial"
    )
    assert not issues
    anchor = audit["claims"][0]["assertions"][0]
    assert (anchor["start"], anchor["end"], anchor["field_start"], anchor["field_end"]) == (
        0,
        len(text),
        7,
        7 + len(text),
    )
    assert anchor["answer_field"] == "short_answer"


def test_fresh_policy_freezes_while_absent_historical_policy_remains_legacy():
    settings = SimpleNamespace(
        chat_checker_claim_policy=spans.POLICY,
        chat_joint_checker_policy="typed_joint_v5",
        chat_source_relation_policy="off",
        chat_checker_schema_policy=None,
        chat_checker_output_policy=None,
    )
    command = json.loads(
        json.dumps(
            {
                "checker_claim_policy": spans.submission_policy(
                    settings, answer_mode="textbook", verification_mode="verified"
                )
            }
        )
    )
    request = GenerationRequest(
        request_id="new",
        mode="interactive_chat",
        condition="E1",
        question="Q",
        reliability_policy="evidence_reliability_v5",
        checker_claim_policy=command["checker_claim_policy"],
    )
    assert spans.validate_request(request)
    assert not spans.validate_request(replace(request, checker_claim_policy=None))
    assert (
        spans.submission_policy(settings, answer_mode="textbook", verification_mode="fast") is None
    )
    assert (
        spans.submission_policy(
            settings, answer_mode="general_knowledge", verification_mode="verified"
        )
        is None
    )
    assert (
        spans.submission_policy(
            settings,
            answer_mode="textbook",
            verification_mode="verified",
            assertion_source_policy="assertion_source_transport_v1",
        )
        is None
    )


class Transport:
    def __init__(self, replies):
        self.replies, self.calls = iter(replies), []

    def generate(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), kwargs))
        value = next(self.replies)
        if callable(value):
            value = value(messages)
        return ProviderResult(
            raw_text=json.dumps(value),
            finish_reason="stop",
            provider="authored_contract_control",
            model="authored",
            request_submitted=True,
        )


def test_existing_compact_transport_is_preserved_and_bad_frozen_overlap_fails_before_dispatch():
    from generation.openrouter_routes import BASE_URL

    compact = ModelConfig(
        provider="openai_compatible",
        base_url=BASE_URL,
        model="google/gemini-3.5-flash-lite",
        temperature=None,
        openrouter_route_profile="gemini35_google_vertex_compact_checker_v3",
    )
    settings = SimpleNamespace(
        chat_checker_claim_policy=spans.POLICY,
        chat_joint_checker_policy="typed_joint_v5",
        chat_source_relation_policy="off",
        chat_checker_schema_policy=None,
        chat_checker_output_policy=None,
    )
    assert (
        spans.submission_policy(
            settings,
            answer_mode="textbook",
            verification_mode="verified",
            checker_config=compact,
        )
        is None
    )
    adapter = Transport([])
    out = GenerationService(adapter).generate(replace(pipeline_request(), checker_config=compact))
    assert out.error["code"] == "CHECKER_CLAIM_POLICY_INVALID"
    assert not adapter.calls and not out.attempts


def pipeline_request():
    evidence, maps = [], {}
    texts = [
        "Osmosis is a special case of diffusion.",
        "Osmosis moves water through a semipermeable membrane.",
    ]
    for number, text in enumerate(texts, 1):
        h = hashlib.sha256(text.encode()).hexdigest()
        chunk, unit = f"chunk-{number}", f"unit-{number}"
        evidence.append(
            {
                "evidence_id": f"ev_{number:03d}",
                "chunk_id": chunk,
                "asset_id": "fixture",
                "processing_id": "fixture",
                "source_title": "Authored source",
                "section": "Transport",
                "pages": [number],
                "locator": "Authored",
                "text": text,
                "text_hash": h,
                "context_order": number,
            }
        )
        maps[chunk] = {
            "document_version_id": "v1",
            "processing_id": "fixture",
            "asset_id": "fixture",
            "chunk_text": text,
            "chunk_hash": h,
            "units": [{"id": unit, "page": number, "cleaned_text": text, "text_hash": h}],
            "spans": [
                {
                    "unit_id": unit,
                    "page": number,
                    "start": 0,
                    "end": len(text),
                    "chunk_start": 0,
                    "chunk_end": len(text),
                }
            ],
        }
    return GenerationRequest(
        request_id="phase210-synthetic",
        mode="interactive_chat",
        condition="E1",
        question="Explain osmosis.",
        evidence=evidence,
        source_map=maps,
        config=ModelConfig(tokenizer_provider="estimate"),
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        checker_claim_policy=spans.POLICY,
        repair_policy="claim_patch_repair_v3",
        teaching_context={"teaching_mode": "direct", "help_level": 0, "turn_role": "user_question"},
    )


def packet_from(messages):
    for message in messages:
        if message["content"].startswith("{"):
            item = json.loads(message["content"])
            if "CLAIMS" in item:
                return decode(item) if "CHECKER_INPUT_ENCODING" in item else item
    raise AssertionError("No original checker packet")


def authored_check(messages, *, initial=False, malformed=False):
    data = packet_from(messages)
    claims = []
    bindings = {row["claim_id"]: row["citations"] for row in data["ACTUAL_CITATION_BINDINGS"]}
    for claim in data["CLAIMS"]:
        citations = [
            {
                "evidence_id": b["evidence_id"],
                "fragment_ids": b["allowed_fragment_ids"],
                "relation": "supporting",
            }
            for b in bindings[claim["claim_id"]]
        ]
        ids = [f for b in citations for f in b["fragment_ids"]]
        parts = [part(claim["text"], ids=ids)]
        if initial and ":" in claim["text"]:
            left, right = claim["text"].split(":", 1)
            parts = [part(left + ":", "partial", (), left), part(right, ids=ids)]
            if malformed:
                parts[0]["quote"] = "an invented relationship"
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "basis": "textbook",
                "status": "supported",
                "citations": citations,
                "reason": "Authored transport control, not an independent semantic verdict.",
                "assertions": parts,
            }
        )
    fragment = data["SOURCE_FRAGMENTS"][0]
    return {
        "claims": claims,
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": False,
        "reason": "Authored transport control.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": "not_applicable",
        "tutor_question_ok": True,
        "requirements": [
            {
                "requirement_id": r["id"],
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {
                        "evidence_id": fragment["evidence_id"],
                        "fragment_id": fragment["fragment_id"],
                        "quote": fragment["exact_text"],
                    }
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored contract control.",
            }
            for r in data["CONTEXT_COVERAGE"]["requirements"]
        ],
        "non_repetitive_next_action": True,
    }


def test_actual_pipeline_routes_structured_negative_to_local_repair_and_fresh_gate_in_four_calls():
    initial = "Osmosis is a special case of diffusion: it moves water through a semipermeable membrane [ev_002]. Osmosis is a special case of diffusion [ev_001]."
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
            chat_value("answer", initial, citations=["ev_001", "ev_002"]),
            lambda m: authored_check(m, initial=True),
            patch,
            authored_check,
        ]
    )
    out = GenerationService(adapter).generate(pipeline_request(), RequestBudget())
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == 4
    assert out.checks[0]["typed_judgment_raw_aliases"]["body_ok"] is True
    assert out.checks[0]["effective_body_ok"] is False
    assert out.checks[0]["typed_judgment_raw_aliases"]["claims"][0]["status"] == "supported"
    assert (
        repaired in out.response["answer_text"]
        and seen["safe"]["text"] in out.response["answer_text"]
    )
    for index in (1, 3):
        messages, kwargs = adapter.calls[index]
        assert spans.INSTRUCTIONS in messages[0]["content"]
        assert kwargs["response_schema_name"] == spans.SCHEMA


def test_contract_correction_then_negative_preserves_the_required_repair_and_recheck_pair():
    text = "Osmosis is a special case of diffusion: it moves water [ev_002]."
    adapter = Transport(
        [
            chat_value("answer", text, citations=["ev_002"]),
            lambda m: authored_check(m, initial=True, malformed=True),
            lambda m: authored_check(m, initial=True),
        ]
    )
    out = GenerationService(adapter).generate(pipeline_request(), RequestBudget())
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 3
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]


@pytest.mark.parametrize(
    "malformed,code", [(True, "CHECKER_INCONSISTENT"), (False, "SEMANTIC_CHECK_FAILED")]
)
def test_defective_final_check_fails_closed_at_four_calls(malformed, code):
    first = "Osmosis is a special case of diffusion: it moves water [ev_002]. Osmosis is a special case of diffusion [ev_001]."

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        bad = next(
            c for c in data["original_claims"] if c["claim_id"] == data["editable_claim_ids"][0]
        )
        return {
            "edits": [
                {
                    "claim_id": bad["claim_id"],
                    "replacement_text": "Osmosis is a special case of diffusion [ev_001]: it moves water [ev_002].",
                }
            ],
            "append_answer_text": "",
        }

    adapter = Transport(
        [
            chat_value("answer", first, citations=["ev_001", "ev_002"]),
            lambda m: authored_check(m, initial=True),
            patch,
            lambda m: authored_check(m, initial=True, malformed=malformed),
        ]
    )
    out = GenerationService(adapter).generate(pipeline_request(), RequestBudget())
    assert out.response is None and out.error["code"] == code
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4


def test_historical_command_without_policy_still_uses_legacy_schema_and_two_calls():
    def legacy_check(messages):
        value = authored_check(messages)
        for row in value["claims"]:
            row.pop("assertions")
        return value

    adapter = Transport(
        [
            chat_value(
                "answer", "Osmosis is a special case of diffusion [ev_001].", citations=["ev_001"]
            ),
            legacy_check,
        ]
    )
    command = json.loads("{}")
    request = replace(pipeline_request(), checker_claim_policy=command.get("checker_claim_policy"))
    out = GenerationService(adapter).generate(request, RequestBudget())
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v5_ordinary_question_v1"
    assert spans.INSTRUCTIONS not in adapter.calls[1][0][0]["content"]
    assert "claim_support_spans" not in out.checks[0]
