"""Authored punctuation regressions; no model quality or historical-case closure claim."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.modules.answering import service as answering
from generation import GenerationService, RequestBudget
from generation import assertion_boundary_v2 as boundary
from generation import assertion_citation_derivation_v1 as derived
from generation import assertion_provenance_v1 as legacy
from generation.adapters import LLMAdapter
from generation.reliability_v5 import response_claims
from generation.types import ProviderResult
from test_checker_claim_spans210 import pipeline_request

ROOT = Path(__file__).parents[2]


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Boundary controls permit no model, network or database access")

    for name in ("connect", "connect_ex", "bind"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    assert Path(derived.__file__).resolve().is_relative_to(ROOT)
    assert Path(answering.__file__).resolve().is_relative_to(ROOT)
    yield
    assert not attempts


def source(text):
    digest = hashlib.sha256(text.encode()).hexdigest()
    fragment = {
        "fragment_id": "authored-fragment",
        "evidence_id": "ev_001",
        "exact_text": text,
        "text_hash": digest,
        "complete_block": True,
        "start": 0,
        "end": len(text),
        "chunk_start": 0,
        "chunk_end": len(text),
    }
    evidence = {"evidence_id": "ev_001", "text": text, "text_hash": digest}
    return [fragment], [evidence]


def draft(text):
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": [{"assertion_id": "A001", "text": text, "source_ids": ["F001"]}],
        "short_answer": None,
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }


def compile_current(value, fragments, evidence):
    return derived.compile_draft(
        value, fragments, evidence, provider_output_policy=derived.CURRENT_POLICY
    )


@pytest.mark.parametrize("abbreviation", ["e.g.", "i.e.", "E.G."])
def test_current_v4_keeps_abbreviation_sentence_exact_and_legacy_v3_still_rejects(abbreviation):
    text = f"The source gives an example, {abbreviation} a complete supported process."
    fragments, evidence = source(text)
    original = draft(text)
    public, proof = compile_current(original, fragments, evidence)
    assert original == draft(text)
    assert public["answer_text"] == text + " [ev_001]"
    assert proof["claim_boundary_policy"] == boundary.POLICY
    assert proof["citation_construction"]["version"] == derived.CURRENT_POLICY
    assert proof["semantic_support_certified"] is False
    claims = legacy.compiled_claims(public, proof)
    assert len(claims) == 1
    assert claims[0]["start"] == 0 and claims[0]["end"] == len(public["answer_text"])
    assert claims[0]["text"] == public["answer_text"]
    assert legacy.checker_bindings(claims, proof, fragments)[0]["citations"] == [
        {"evidence_id": "ev_001", "allowed_fragment_ids": ["F001"]}
    ]
    with pytest.raises(ValueError, match="ASSERTION_COMPLETE_CLAIM_REQUIRED"):
        derived.compile_draft(original, fragments, evidence)
    with pytest.raises(ValueError, match="ASSERTION_COMPLETE_CLAIM_REQUIRED"):
        legacy.compile_draft({**original, "citations": ["ev_001"]}, fragments)


@pytest.mark.parametrize("text", ["The value is 3.5 in the source.", "An ordinary complete claim."])
def test_unaffected_rows_keep_identical_public_output_claim_ids_and_old_provenance(text):
    fragments, evidence = source(text)
    old_public, old_proof = derived.compile_draft(draft(text), fragments, evidence)
    current_public, current_proof = compile_current(draft(text), fragments, evidence)
    assert current_public == old_public
    assert legacy.compiled_claims(current_public, current_proof) == response_claims(old_public)
    assert current_proof["assertions"] == old_proof["assertions"]
    assert "claim_boundary_policy" not in old_proof


@pytest.mark.parametrize(
    "text",
    [
        "The cell grows. It then divides.",
        "Examples include e.g. glucose. A separate claim follows.",
        "An unsupported prefix\nA complete sentence.",
        "A complete sentence. [ev_002]",
    ],
)
def test_true_multiple_claims_newlines_and_model_inline_markers_remain_rejected(text):
    fragments, evidence = source(text)
    with pytest.raises(
        ValueError, match="ASSERTION_COMPLETE_CLAIM_REQUIRED|ASSERTION_TEXT_INVALID"
    ):
        compile_current(draft(text), fragments, evidence)


@pytest.mark.parametrize(
    "defect", ["unknown", "duplicate", "empty", "incomplete", "hash", "excluded"]
)
def test_v4_preserves_every_source_selection_gate(defect):
    text = "The source gives examples, e.g. a complete process."
    fragments, evidence = source(text)
    value = draft(text)
    if defect == "unknown":
        value["answer_text"][0]["source_ids"] = ["F999"]
    elif defect == "duplicate":
        value["answer_text"][0]["source_ids"] *= 2
    elif defect == "empty":
        value["answer_text"][0]["source_ids"] = []
    elif defect == "incomplete":
        fragments[0]["complete_block"] = False
    elif defect == "hash":
        fragments[0]["text_hash"] = "0" * 64
    else:
        evidence = []
    with pytest.raises(ValueError):
        compile_current(value, fragments, evidence)


def test_only_new_fast_submissions_select_v4_and_explicit_v3_stays_frozen():
    fields = {"assertion_source_policy": legacy.POLICY}
    settings = Settings()
    assert settings.chat_fast_assertion_citations == "source_selected_v3"
    assert (
        answering._provider_output_submission_policy(settings, fields, verification_mode="fast")
        == derived.CURRENT_POLICY
    )
    assert (
        answering._provider_output_submission_policy(settings, fields, verification_mode="verified")
        == "json_field_contract_v2"
    )
    assert (
        answering._provider_output_submission_policy(settings, {}, verification_mode="fast")
        == "json_field_contract_v2"
    )
    for selection, expected in [
        ("source_selected_v2", derived.POLICY),
        ("legacy_v1", "json_field_contract_v2"),
    ]:
        configured = SimpleNamespace(
            chat_fast_assertion_citations=selection,
            chat_provider_output_policy="json_field_contract_v2",
        )
        assert (
            answering._provider_output_submission_policy(
                configured, fields, verification_mode="fast"
            )
            == expected
        )
    configured = SimpleNamespace(
        chat_fast_assertion_citations="source_selected_v3",
        chat_provider_output_policy=derived.POLICY,
    )
    assert (
        answering._provider_output_submission_policy(configured, fields, verification_mode="fast")
        == derived.POLICY
    )


class OneDraft:
    def __init__(self, value):
        self.value, self.calls = value, []

    def generate(self, messages, **options):
        assert not self.calls
        self.calls.append((deepcopy(messages), deepcopy(options)))
        return ProviderResult(
            raw_text=json.dumps(self.value),
            provider="authored_offline",
            model="boundary-control",
            finish_reason="stop",
            request_submitted=False,
        )


def test_current_v4_pipeline_keeps_single_exact_claim_through_final_fast_binding_checks():
    request = pipeline_request()
    request.config = replace(
        request.config,
        provider="openai",
        model="offline-control",
        base_url="https://offline.invalid/v1",
        window_tokens=32768,
        max_tokens=1024,
    )
    request.assertion_source_policy = legacy.POLICY
    request.checker_claim_policy = None
    request.provider_output_policy = derived.CURRENT_POLICY
    request.verification_mode = "fast"
    text = "Osmosis is a special case of diffusion, i.e. water moves by diffusion."
    adapter = OneDraft(draft(text))
    outcome = GenerationService(adapter).generate(request, RequestBudget(max_calls=1))
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == text + " [ev_001]"
    assert outcome.response["citations"] == ["ev_001"]
    assert len(adapter.calls) == 1 and not outcome.checks
    assert outcome.token_budget["semantic_verification"]["status"] == "not_requested"
    assert outcome.drafts[0]["assertion_provenance"]["claim_boundary_policy"] == boundary.POLICY
    checked_request = replace(request, verification_mode="verified")
    with pytest.raises(ValueError, match="ASSERTION_CITATION_POLICY_INCOMPATIBLE"):
        derived.validate_request(checked_request)
