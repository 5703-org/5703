"""Exposed negative and authored native-service controls, not model quality."""

import ast

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket

import pytest

from generation import GenerationService, RequestBudget
from generation import checker_claim_anchors_v2 as anchors
from generation import repair_citation_coordination_v4 as coordination
from generation.adapters import LLMAdapter, chat_value
from generation.local_repair import ClaimPatch, apply_claim_patch
from generation.parser import ResponseValidationError
from generation.checked import compact_schema
from test_checker_claim_anchors211 import answer_check, request_v2
from test_checker_claim_spans210 import Transport, packet_from


FIXTURES = Path(__file__).parents[1] / "fixtures" / "repair212"
SAFE = "Osmosis moves water through a semipermeable membrane [ev_002]."
BODY = SAFE + " Neither process requires cellular energy [ev_001]."
SHORT = SAFE + " Neither requires cellular energy [ev_001]."


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempted = []

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("No network, actual provider or DB in phase212 controls")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    yield
    assert not attempted


def captured_repair():
    pins = json.loads((FIXTURES / "pins.json").read_text("utf-8"))
    values = {}
    for row in pins["rows"]:
        raw = (FIXTURES / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        values[row["path"]] = json.loads(raw)
    request = values["http-15-request.json"]
    data = json.loads(request["messages"][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    context = next(
        m for m in request["messages"] if m["content"].startswith("CONTEXT_DATA_JSON:\n")
    )
    evidence = json.loads(context["content"].split("\n", 1)[1])["CURRENT_EVIDENCE"]
    response = values["http-15-response.body"]
    assert response["choices"][0]["finish_reason"] == "stop"
    return data, json.loads(response["choices"][0]["message"]["content"]), evidence


def test_actual_http15_still_fails_strict_summary_binding_without_autoborrow():
    data, patch, evidence = captured_repair()
    before = deepcopy(data)
    with pytest.raises(ResponseValidationError) as error:
        apply_claim_patch(
            data["draft"],
            data["original_claims"],
            data["protected_exact_claims"],
            patch,
            [row["evidence_id"] for row in evidence],
        )
    assert error.value.code == "CLAIM_PATCH_SUMMARY_BINDING"
    assert data == before


def test_actual_feedback_plan_marks_whole_negatives_and_protected_summary_without_certifying():
    data, _, _ = captured_repair()
    before = deepcopy(data)
    plan = coordination.field_plan(data)
    assert plan["negative_scope"] == "complete_original_claim"
    assert plan["defect_quote_role"] == "non_exhaustive_witness"
    assert len(plan["whole_negative_claim_ids"]) == 3
    assert len(plan["fields"]["answer_text"]["editable_claim_ids"]) == 2
    assert len(plan["fields"]["short_answer"]["editable_claim_ids"]) == 1
    assert len(plan["fields"]["short_answer"]["protected_claim_ids"]) == 1
    assert plan["summary_marker_rule"] == "subset_of_recomposed_body_markers"
    assert plan["new_citation_ids_allowed_in_coordinated_body_and_summary"]
    assert not plan["semantic_support_certified"] and not plan["publication_override"]
    assert not plan["protected_spans_may_change"] and data == before


def request_v4():
    base = request_v2()
    evidence, maps = deepcopy(base.evidence), deepcopy(base.source_map)
    source_texts = [
        "Diffusion expends no cellular energy.",
        "Osmosis moves water through a semipermeable membrane.",
        "Osmosis is a diffusion process that requires no cellular energy.",
    ]
    evidence.append(deepcopy(evidence[0]))
    for number, (row, text) in enumerate(zip(evidence, source_texts), 1):
        chunk, unit = f"chunk-{number}", f"unit-{number}"
        digest = hashlib.sha256(text.encode()).hexdigest()
        row.update(
            evidence_id=f"ev_{number:03d}",
            chunk_id=chunk,
            text=text,
            text_hash=digest,
            context_order=number,
            pages=[number],
        )
        maps[chunk] = dict(
            maps["chunk-1"],
            chunk_text=text,
            chunk_hash=digest,
            units=[{"id": unit, "page": number, "cleaned_text": text, "text_hash": digest}],
            spans=[
                {
                    "unit_id": unit,
                    "page": number,
                    "start": 0,
                    "end": len(text),
                    "chunk_start": 0,
                    "chunk_end": len(text),
                }
            ],
        )
    return replace(
        base,
        request_id="phase212-authored-contract",
        repair_policy=coordination.POLICY,
        question="What moves in osmosis, and does it require cellular energy?",
        evidence=evidence,
        source_map=maps,
    )


def check(messages, *, initial=False, unsupported_final=False):
    result = answer_check(messages)
    packet = packet_from(messages)
    originals = {c["claim_id"]: c for c in packet["CLAIMS"]}
    for row in result["claims"]:
        text = originals[row["claim_id"]]["text"]
        if (initial and "Neither" in text) or (
            unsupported_final and "requires no cellular energy" in text
        ):
            row["status"] = "partial"
            row["assertions"][0].update(
                status="partial",
                unestablished_quote=("Neither" if initial else "requires no cellular energy"),
            )
            result["body_ok"] = False
    result["repair_fragment_ids"] = [
        f["fragment_id"] for f in packet["SOURCE_FRAGMENTS"] if f["evidence_id"] == "ev_003"
    ]
    for requirement in result["requirements"]:
        requirement["evidence"] = [
            {
                "evidence_id": f["evidence_id"],
                "fragment_id": f["fragment_id"],
                "quote": f["exact_text"],
            }
            for f in packet["SOURCE_FRAGMENTS"]
            if f["evidence_id"] in {"ev_002", "ev_003"}
        ]
    return result


def execute(*, legacy=False, unsupported_final=False):
    seen = {}

    def patch(messages):
        text = messages[-1]["content"]
        if legacy:
            assert "REPAIR_FIELD_COORDINATION_JSON:" not in text
        else:
            assert "COMPLETE original claim" in text
            plan = json.loads(
                text.split("REPAIR_FIELD_COORDINATION_JSON:\n", 1)[1].split(
                    "\nREPAIR_DATA_JSON:\n", 1
                )[0]
            )
            assert plan["negative_scope"] == "complete_original_claim"
            assert plan["fields"]["short_answer"]["protected_claim_ids"]
            seen["plan"] = plan
        data = json.loads(text.split("REPAIR_DATA_JSON:\n", 1)[1])
        seen["feedback"] = data
        source = "ev_001" if unsupported_final else "ev_003"
        return {
            "edits": [
                {
                    "claim_id": c["claim_id"],
                    "replacement_text": (
                        f"Osmosis requires no cellular energy [{source}]."
                        if unsupported_final
                        else f"Osmosis is a diffusion process that requires no cellular energy [{source}]."
                    ),
                }
                for c in data["original_claims"]
                if c["claim_id"] in data["editable_claim_ids"]
            ],
            "append_answer_text": "",
        }

    generated = chat_value("answer", BODY, citations=["ev_002", "ev_001"])
    generated["short_answer"] = SHORT
    transport = Transport(
        [
            generated,
            lambda m: check(m, initial=True),
            patch,
            lambda m: check(m, unsupported_final=unsupported_final),
        ]
    )
    request = request_v4()
    if legacy:
        request = replace(request, repair_policy="claim_patch_repair_v3")
    out = GenerationService(transport).generate(request, RequestBudget())
    return out, transport, seen


def test_actual_service_coordinates_new_body_summary_source_and_requires_fresh_final_check():
    out, transport, seen = execute()
    assert out.succeeded, out.error
    assert len(transport.calls) == out.budget["consumed_calls"] == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.response["citations"] == ["ev_002", "ev_003"]
    for field in ("answer_text", "short_answer"):
        assert SAFE in out.response[field] and "[ev_003]" in out.response[field]
        assert "Neither" not in out.response[field]
    assert out.token_budget["repair_policy"] == coordination.POLICY
    assert out.token_budget["repair_compiler_policy"] == "claim_patch_repair_v3"
    assert out.token_budget["repair_field_coordination_plans"] == [seen["plan"]]
    assert transport.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert transport.calls[2][1]["response_schema"] == compact_schema(ClaimPatch)
    initial, final = (packet_from(transport.calls[i][0]) for i in (1, 3))
    assert initial[anchors.ANCHORS] != final[anchors.ANCHORS]
    assert out.checks[0]["effective_body_ok"] is False
    for binding in final["ACTUAL_CITATION_BINDINGS"]:
        claim = next(c for c in final["CLAIMS"] if c["claim_id"] == binding["claim_id"])
        if "requires no cellular energy" in claim["text"]:
            assert {c["evidence_id"] for c in binding["citations"]} == {"ev_003"}


def test_equal_summary_body_marker_sets_do_not_certify_unestablished_predicate():
    out, transport, _ = execute(unsupported_final=True)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(transport.calls) == out.budget["consumed_calls"] == 4
    assert out.checks[-1]["effective_body_ok"] is False


def test_historical_v3_keeps_old_prompt_and_compiler_without_new_plan():
    out, transport, _ = execute(legacy=True)
    assert out.succeeded, out.error
    assert len(transport.calls) == 4
    assert out.token_budget["repair_policy"] == "claim_patch_repair_v3"
    assert "repair_compiler_policy" not in out.token_budget
    assert "repair_field_coordination_plans" not in out.token_budget


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_mode": "fast"},
        {"answer_mode": "general_knowledge"},
        {"checker_claim_policy": "asserted_support_spans_v1"},
        {"reading_context": {"text": "reading"}},
        {"teaching_context": {"teaching_mode": "hint", "turn_role": "user_question"}},
        {"teaching_context": {"teaching_mode": "direct", "turn_role": "attempt"}},
        {
            "teaching_context": {
                "teaching_mode": "direct",
                "turn_role": "user_question",
                "learner_attempt": "x",
            }
        },
        {
            "teaching_context": {
                "teaching_mode": "direct",
                "turn_role": "user_question",
                "practice_context": {"x": 1},
            }
        },
    ],
)
def test_incompatible_frozen_v4_is_rejected_without_dispatch(changes):
    request = replace(request_v4(), **changes)
    with pytest.raises(ValueError, match="REPAIR_COORDINATION_POLICY_INCOMPATIBLE"):
        coordination.validate_request(request)
    transport = Transport([])
    out = GenerationService(transport).generate(request, RequestBudget())
    assert out.error is not None and not transport.calls


def test_actual_imports_and_legacy_compiler_prompt_are_unchanged():
    from generation import checked, local_repair

    root = Path(__file__).resolve().parents[2]
    for module in (coordination, checked, local_repair):
        assert Path(module.__file__).resolve().is_relative_to(root)
    assert not coordination.validate_request(
        replace(request_v4(), repair_policy="claim_patch_repair_v3")
    )
    evidence = root / "tests/fixtures/repair212"
    pins = {
        "local_repair.py.txt": "3115857478a71bbd8b4356355501e8bf3fff04ee1a7585ff7110c50578c5d03f",
        "claim_patch_repair_v1.txt": "8721f68c3dd83c3d4b3dc5045e1b46c00ecadeb953ac9e076d46dadb7809e4ac",
    }
    for name, expected in pins.items():
        assert hashlib.sha256((evidence / name).read_bytes()).hexdigest() == expected
    # Freeze executable structure, including literal values; source formatting is not behavior.
    # The original unformatted bytes remain hash-pinned in a portable text fixture.
    assert ast.dump(
        ast.parse((root / "generation/local_repair.py").read_text(encoding="utf-8"))
    ) == ast.dump(ast.parse((evidence / "local_repair.py.txt").read_text(encoding="utf-8")))
    assert (root / "generation/prompts/claim_patch_repair_v1.txt").read_bytes() == (
        evidence / "claim_patch_repair_v1.txt"
    ).read_bytes()
