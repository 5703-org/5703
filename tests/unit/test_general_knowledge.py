"""Explicit ungrounded interactive mode never changes textbook or benchmark defaults."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from contracts.models import ChatMessageCreate
from generation import GenerationService
from generation.parser import parse_response, ResponseValidationError
from generation.prompt_builder import build_messages
from generation.types import ProviderResult, failure
from test_generation_engine import request, response, ScriptedAdapter


def general(**updates):
    return request(answer_mode="general_knowledge", evidence=[], **updates)


def independent_answer(**updates):
    return response(**{"answer_text": "A model-knowledge explanation.", "citations": [], **updates})


def test_public_mode_is_explicit_bounded_and_defaults_to_textbook():
    assert ChatMessageCreate(content="Explain rain").answer_mode == "textbook"
    assert (
        ChatMessageCreate(content="Explain rain", answer_mode="general_knowledge").answer_mode
        == "general_knowledge"
    )
    for value in [None, "automatic", "E0", True]:
        with pytest.raises(ValidationError):
            ChatMessageCreate(content="Explain rain", answer_mode=value)


def test_default_empty_evidence_still_refuses_without_model_call():
    adapter = ScriptedAdapter([])
    output = GenerationService(adapter=adapter).generate(request(evidence=[]))
    assert output.response["response_type"] == "refusal"
    assert output.budget["consumed_calls"] == 0 and adapter.calls == []


def test_explicit_general_uses_model_without_textbook_evidence_or_citation_audit():
    adapter = ScriptedAdapter([json.dumps(independent_answer())])
    output = GenerationService(adapter=adapter).generate(general())
    assert output.error is None and output.response["response_type"] == "answer"
    assert output.response["citations"] == [] and output.evidence == []
    assert output.budget["consumed_calls"] == 1 and len(adapter.calls) == 1
    assert adapter.calls[0][1]["request_context"]["answer_mode"] == "general_knowledge"
    assert output.token_budget["prompt_version"] == "general_knowledge_v1"
    assert output.token_budget["source_provenance"] == "model_general_knowledge_unverified"
    assert output.token_budget["evidence_tokens"] == 0
    assert output.token_budget["citation_audit"]["status"] == "not_applicable"
    assert output.token_budget["citation_audit"]["support_verified"] is None


def test_general_mock_honestly_refuses_independent_factual_generation():
    output = GenerationService().generate(general(question="Explain a rainbow."))
    assert output.model_mode == "mock" and output.response["response_type"] == "refusal"
    assert "mock answerer" in output.response["answer_text"]
    assert output.response["citations"] == []


def test_general_followup_prompt_has_valid_format_example_with_no_source_authority():
    messages, _, _, _ = build_messages(general(question="Explain that more simply."))
    line = next(
        line for line in messages[0]["content"].splitlines() if line.startswith('{"schema_version"')
    )
    example = parse_response(
        line,
        mode="interactive_chat",
        condition="E1",
        evidence_ids=[],
        answer_mode="general_knowledge",
    )
    assert example["citations"] == [] and example["confidence"] is None
    assert "format example, not an answer or factual source" in messages[0]["content"]


def test_general_rejects_accidental_evidence_before_any_call():
    adapter = ScriptedAdapter([])
    command = replace(request(), answer_mode="general_knowledge")
    output = GenerationService(adapter=adapter).generate(command)
    assert output.response is None and output.error["code"] == "GENERAL_KNOWLEDGE_EVIDENCE"
    assert output.budget["consumed_calls"] == 0 and adapter.calls == []


def test_general_history_is_context_not_citation_authority_and_is_not_mutated():
    history = [
        {"role": "user", "content": "Explain this old textbook concept."},
        {"role": "assistant", "content": "An old textbook claim. [ev_001]"},
    ]
    before = deepcopy(history)
    command = general(
        history=history, summary="Old answer [ev_002]", profile={"policy": "Use short sentences."}
    )
    messages, selected, budget, effective = build_messages(command)
    assert selected == [] and history == before and command.summary.endswith("[ev_002]")
    assert all("[ev_001]" not in m["content"] and "[ev_002]" not in m["content"] for m in messages)
    assert "Use short sentences." in messages[0]["content"]
    assert "unverified conversation" in messages[0]["content"]
    assert effective.summary == "Old answer "
    assert budget["total_reserved_tokens"] <= command.config.window_tokens


@pytest.mark.parametrize(
    "mode,condition",
    [("benchmark_openqa", "E0"), ("benchmark_openqa", "E1"), ("benchmark_mcq", "E0")],
)
def test_general_cannot_change_frozen_benchmark_modes(mode, condition):
    command = general(
        mode=mode,
        condition=condition,
        options={"A": "a", "B": "b", "C": "c", "D": "d"} if mode == "benchmark_mcq" else None,
    )
    with pytest.raises(ResponseValidationError, match="interactive only"):
        build_messages(command)


def test_explicit_textbook_does_not_change_benchmark_prompt_or_history_policy():
    command = request(mode="benchmark_openqa", condition="E0", evidence=[])
    old = build_messages(command)
    explicit = build_messages(replace(command, answer_mode="textbook"))
    assert old[:3] == explicit[:3]
    assert "answer_mode" not in old[2]


@pytest.mark.parametrize(
    "updates",
    [
        {"citations": ["ev_001"]},
        {"answer_text": "A false source marker [ev_001]"},
        {"short_answer": "A false source marker [EV_998]"},
    ],
)
def test_general_output_cannot_fabricate_textbook_citations(updates):
    payload = independent_answer()
    payload.update(updates)
    with pytest.raises(ResponseValidationError) as error:
        parse_response(
            json.dumps(payload),
            mode="interactive_chat",
            condition="E1",
            evidence_ids=[],
            answer_mode="general_knowledge",
        )
    assert error.value.code == "GENERAL_KNOWLEDGE_CITATIONS"


def test_textbook_parser_still_requires_citations_for_factual_answer():
    with pytest.raises(ResponseValidationError) as error:
        parse_response(
            json.dumps(independent_answer()),
            mode="interactive_chat",
            condition="E1",
            evidence_ids=[],
        )
    assert error.value.code == "MISSING_CITATIONS"


def test_general_citation_violation_keeps_one_repair_then_fails_without_answer():
    bad = json.dumps(independent_answer(answer_text="A source [ev_999]"))
    adapter = ScriptedAdapter([bad, bad])
    output = GenerationService(adapter=adapter).generate(general())
    assert output.response is None and output.error["code"] == "GENERAL_KNOWLEDGE_CITATIONS"
    assert output.budget["consumed_calls"] == 2 and output.budget["format_repairs"] == 1
    assert len(adapter.calls) == 2 and output.evidence == []


def test_general_provider_failure_does_not_switch_mode_or_synthesize_answer():
    error = ProviderResult(error=failure("PROVIDER_TIMEOUT", "Timed out", retryable=True))
    adapter = ScriptedAdapter([error, error, error])
    output = GenerationService(adapter=adapter, sleep=lambda _: None).generate(general())
    assert output.response is None and output.error["code"] == "PROVIDER_TIMEOUT"
    assert output.budget["consumed_calls"] == 3 and output.budget["transient_retries"] == 2
    assert all(
        call[1]["request_context"]["answer_mode"] == "general_knowledge" for call in adapter.calls
    )
    assert output.evidence == []
