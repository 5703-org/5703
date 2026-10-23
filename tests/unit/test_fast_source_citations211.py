"""Actual exposed OFF09 and authored transport controls; no semantic PASS labels."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.answering import service as answering
from generation import GenerationService, RequestBudget
from generation import assertion_citation_derivation_v1 as derived
from generation import assertion_provenance_v1 as legacy
from generation.adapters import LLMAdapter
from generation.reliability_v5 import response_claims
from generation.types import ProviderResult
from test_checker_claim_spans210 import pipeline_request

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests/fixtures/native211"


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Phase211 permits no real network, model or database connection")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    assert Path(answering.__file__).resolve().is_relative_to(ROOT)
    assert Path(derived.__file__).resolve().is_relative_to(ROOT)
    yield
    assert attempts == []


def settings(**changes):
    return SimpleNamespace(
        **{
            "chat_provider_output_policy": "json_field_contract_v2",
            "chat_fast_assertion_citations": "source_selected_v2",
            **changes,
        }
    )


def select(config=None, fields=None, mode="fast"):
    return answering._provider_output_submission_policy(
        config or settings(),
        {"assertion_source_policy": legacy.POLICY} if fields is None else fields,
        verification_mode=mode,
    )


def capture():
    pins = json.loads((FIXTURES / "pins.json").read_text("utf8"))
    values = {}
    for row in pins["rows"]:
        raw = (FIXTURES / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        values[row["path"]] = json.loads(raw)
    wire = values["http-09-request.json"]
    packets = [
        json.loads(message["content"].split("\n", 1)[1])
        for message in wire["messages"]
        if message["content"].startswith("CONTEXT_DATA_JSON:\n")
    ]
    assert len(packets) == 1
    packet = packets[0]
    bank = legacy.decode_generation_source_bank(
        {
            key: packet[key]
            for key in (
                "ASSERTION_SOURCE_BANK",
                "ASSERTION_SOURCE_LOCATORS",
                "GENERATION_INPUT_ENCODING",
            )
        }
    )
    fragments = [
        {
            **row["source_locator"],
            "fragment_id": row["fragment_id"],
            "evidence_id": row["evidence_id"],
            "exact_text": row["exact_text"],
            "text_hash": row["text_sha256"],
            "complete_block": row["complete_block"],
        }
        for row in bank
    ]
    raw = json.loads(values["http-09-response.body"]["choices"][0]["message"]["content"])
    return packet, raw, bank, fragments


def test_fresh_defaults_keep_source_derived_fast_citations_and_original_checker():
    assert Settings.model_fields["chat_fast_assertion_citations"].default == "source_selected_v3"
    assert Settings.model_fields["chat_checker_claim_policy"].default is None
    assert select() == derived.POLICY


@pytest.mark.parametrize("mode", ["verified", None])
def test_checked_and_legacy_omitted_modes_keep_their_configured_output_policy(mode):
    assert select(mode=mode) == "json_field_contract_v2"


@pytest.mark.parametrize("policy", ["strict_v1", "json_example_once_v1"])
def test_explicit_legacy_output_choice_is_not_promoted(policy):
    assert select(settings(chat_provider_output_policy=policy)) == policy


def test_explicit_fast_optout_and_unselected_assertion_route_stay_legacy():
    assert select(settings(chat_fast_assertion_citations="legacy_v1")) == "json_field_contract_v2"
    assert select(fields={}) == "json_field_contract_v2"
    assert (
        select(settings(chat_provider_output_policy=derived.POLICY), mode="verified")
        == derived.POLICY
    )


def test_actual_OFF09_missing_aggregate_ev009_remains_strict_v1_failure():
    _, raw, _, fragments = capture()
    original = deepcopy(raw)
    assert raw["citations"] == ["ev_007", "ev_005", "ev_001"]
    with pytest.raises(ValueError, match="ASSERTION_CITATIONS_MISMATCH"):
        legacy.compile_draft(raw, fragments)
    assert raw == original


def test_actual_OFF09_new_schema_derives_only_its_explicit_body_union_and_keeps_own_proof():
    packet, raw, bank, fragments = capture()
    saved = deepcopy(raw)
    reduced = deepcopy(raw)
    reduced.pop("citations")
    public, proof = derived.compile_draft(reduced, fragments, packet["CURRENT_EVIDENCE"])
    assert public["citations"] == ["ev_007", "ev_005", "ev_009", "ev_001"]
    assert proof["citation_construction"]["semantic_support_certified"] is False
    assert proof["citation_construction"]["source_bank_sha256"] == legacy._canonical_hash(bank)
    for actual, proposed in zip(
        proof["assertions"], raw["answer_text"] + [raw["short_answer"]], strict=True
    ):
        assert actual["assertion_id"] == proposed["assertion_id"]
        assert actual["assertion_text"] == proposed["text"]
        assert [row["source_id"] for row in actual["sources"]] == proposed["source_ids"]
    claims = response_claims(public)
    bindings = legacy.checker_bindings(claims, proof, fragments)
    for index, selected in [(3, "F038"), (4, "F039"), (5, "F040")]:
        assert bindings[index]["citations"] == [
            {"evidence_id": "ev_009", "allowed_fragment_ids": [selected]}
        ]
    assert raw == saved  # The saved old response is never normalized or rewritten.


def test_new_schema_rejects_old_aggregate_field_instead_of_silently_repairing_history():
    packet, raw, _, fragments = capture()
    with pytest.raises(ValidationError, match="Extra inputs"):
        derived.compile_draft(raw, fragments, packet["CURRENT_EVIDENCE"])


@pytest.mark.parametrize(
    "defect", ["unknown", "duplicate", "empty", "incomplete", "hash", "excluded"]
)
def test_derivation_keeps_original_source_selection_gates(defect):
    packet, raw, _, fragments = capture()
    raw.pop("citations")
    evidence = packet["CURRENT_EVIDENCE"]
    if defect == "unknown":
        raw["answer_text"][0]["source_ids"] = ["F999"]
    elif defect == "duplicate":
        raw["answer_text"][0]["source_ids"] *= 2
    elif defect == "empty":
        raw["answer_text"][0]["source_ids"] = []
    elif defect == "incomplete":
        fragments[29]["complete_block"] = False
    elif defect == "hash":
        fragments[29]["text_hash"] = "0" * 64
    else:
        evidence = [item for item in evidence if item["evidence_id"] != "ev_009"]
    with pytest.raises(ValueError):
        derived.compile_draft(raw, fragments, evidence)


class OneOfflineDraft:
    def __init__(self, draft):
        self.draft, self.calls = draft, []

    def generate(self, messages, **options):
        assert not self.calls, "Fast path cannot add a model or checker call"
        self.calls.append((deepcopy(messages), deepcopy(options)))
        return ProviderResult(
            raw_text=json.dumps(self.draft),
            provider="authored_offline",
            model="contract_control",
            finish_reason="stop",
            request_submitted=False,
        )


def authored_pipeline(policy):
    request = pipeline_request()
    request.config = replace(
        request.config,
        provider="openai",
        model="offline-control",
        base_url="https://offline.invalid/v1",
        window_tokens=65536,
        max_tokens=1024,
    )
    request.assertion_source_policy = legacy.POLICY
    request.checker_claim_policy = None
    request.provider_output_policy = policy
    request.verification_mode = "fast"
    draft = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": [
            {
                "assertion_id": "A001",
                "text": "Osmosis is a special case of diffusion.",
                "source_ids": ["F001"],
            }
        ],
        "short_answer": None,
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }
    return request, draft


def test_fresh_fast_pipeline_uses_reduced_schema_one_call_and_truthful_unchecked_state():
    request, draft = authored_pipeline(select())
    transport = OneOfflineDraft(draft)
    outcome = GenerationService(transport).generate(request, RequestBudget(max_calls=1))
    assert outcome.succeeded, outcome.error
    assert outcome.response["citations"] == ["ev_001"]
    assert len(transport.calls) == outcome.budget["consumed_calls"] == 1 and not outcome.checks
    messages, options = transport.calls[0]
    assert options["response_schema_name"] == derived.DRAFT_SCHEMA
    assert "citations" not in options["response_schema"]["properties"]
    assert "Do not emit a citations field." in messages[0]["content"]
    assert outcome.token_budget["semantic_verification"]["status"] == "not_requested"
    assert outcome.token_budget["semantic_verification"]["check_executed"] is False
    assert (
        outcome.drafts[0]["assertion_provenance"]["citation_construction"][
            "semantic_support_certified"
        ]
        is False
    )


def test_historical_frozen_policy_does_not_read_new_default_or_normalize_old_mismatch():
    request, draft = authored_pipeline("json_field_contract_v2")
    draft["citations"] = ["ev_002"]
    snapshot = deepcopy(draft)
    transport = OneOfflineDraft(draft)
    outcome = GenerationService(transport).generate(request, RequestBudget(max_calls=1))
    assert not outcome.succeeded and outcome.response is None
    assert outcome.error["details"]["validation_code"] == "ASSERTION_CITATIONS_MISMATCH"
    assert transport.calls[0][1]["response_schema_name"] == legacy.DRAFT_SCHEMA
    assert draft == snapshot and len(transport.calls) == 1 and not outcome.checks
