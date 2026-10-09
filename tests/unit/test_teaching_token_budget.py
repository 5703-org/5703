"""Whole teaching payload accounting and explicit one-rewrite-call policy."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

from generation.adapters import LLMAdapter
from generation.types import ModelConfig
from personalisation.study import TeachingStudyService


def inputs(extra=""):
    text = "Photosynthesis stores light energy in sugars. " + extra
    return {
        "run_id": "authored-token-budget",
        "item_id": "one-item",
        "condition": "C2",
        "target_level": "beginner",
        "base_answer": {
            "response_type": "answer",
            "answer_text": "Photosynthesis stores light energy in sugars. [ev_001]",
            "citations": ["ev_001"],
        },
        "evidence": [
            {
                "evidence_id": "ev_001",
                "chunk_id": "fixture-chunk",
                "asset_id": "fixture-asset",
                "processing_id": "fixture-processing",
                "source_title": "Authored token-budget fixture",
                "section": "Science",
                "pages": [1],
                "locator": "page 1",
                "text": text,
                "text_hash": hashlib.sha256(text.encode()).hexdigest(),
                "context_order": 1,
            }
        ],
    }


class ObservedAdapter:
    def __init__(self):
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append(deepcopy(messages))
        return LLMAdapter(ModelConfig()).generate(messages, **kwargs)

    def count_tokens(self, *_args, **_kwargs):
        raise AssertionError("Teaching policy permits no additional provider count call")


def test_complete_evidence_and_profile_count_against_window_before_single_call():
    adapter = ObservedAdapter()
    service = TeachingStudyService(adapter=adapter)
    config = ModelConfig(tokenizer_provider="estimate", window_tokens=100000, max_tokens=256)
    original = inputs("Unique tail evidence sentence. " * 100)
    frozen = deepcopy(original)
    result = service.generate(**original, config=config)
    assert result["state"] == "succeeded" and len(adapter.calls) == 1
    transmitted = json.loads(adapter.calls[0][-1]["content"])
    assert transmitted["evidence"][0]["text"] == original["evidence"][0]["text"]
    assert transmitted["presentation_policy"]
    assert original == frozen
    report = result["token_budget"]
    assert report["counter"] == "unicode_character_estimate_v1"
    assert report["tokenizer"]["whole_request_is_estimate"] is True
    assert report["tokenizer"]["protocol_safety_tokens"] == 128
    assert report["total_reserved_tokens"] == report["input_tokens"] + 256
    short = service.generate(**inputs(), config=config)
    assert short["token_budget"]["input_tokens"] < report["input_tokens"]
    rejected = service.generate(
        **original, config=replace(config, window_tokens=report["total_reserved_tokens"] - 1)
    )
    assert rejected["error"]["code"] == "CONTEXT_LIMIT"
    assert rejected["budget"]["consumed_calls"] == 0 and len(adapter.calls) == 2
    accepted = service.generate(
        **original, config=replace(config, window_tokens=report["total_reserved_tokens"])
    )
    assert accepted["state"] == "succeeded" and accepted["budget"]["consumed_calls"] == 1


def test_provider_count_mode_requires_explicit_estimate_without_extra_call():
    adapter = ObservedAdapter()
    service = TeachingStudyService(adapter=adapter)
    config = ModelConfig(
        provider="anthropic",
        model="fixture-only",
        base_url="https://example.invalid/v1",
        tokenizer_provider="provider",
        token_count_fallback="error",
    )
    rejected = service.generate(**inputs(), config=config)
    assert rejected["error"]["code"] == "TOKENIZER_UNAVAILABLE"
    assert rejected["budget"]["consumed_calls"] == 0 and adapter.calls == []
    allowed = service.generate(**inputs(), config=replace(config, token_count_fallback="estimate"))
    assert allowed["state"] == "succeeded" and len(adapter.calls) == 1
    assert allowed["token_budget"]["provider_count_calls"] == 0
    assert (
        allowed["token_budget"]["tokenizer"]["fallback_reason"]
        == "single_rewrite_policy_no_provider_count_request"
    )


def test_configured_local_tokenizer_selection_is_used_and_missing_strict_mapping_stops(monkeypatch):
    from generation import token_counting

    names = []

    class AuthoredEncoding:
        def encode(self, text, **kwargs):
            return text.split()

    def selected(name):
        names.append(name)
        return AuthoredEncoding()

    monkeypatch.setattr(token_counting, "_tiktoken", selected)
    adapter = ObservedAdapter()
    service = TeachingStudyService(adapter=adapter)
    config = ModelConfig(
        provider="openai",
        model="fixture-model",
        base_url="https://example.invalid/v1",
        tokenizer_provider="tiktoken",
        tokenizer_name="fixture_encoding",
        token_count_fallback="error",
    )
    result = service.generate(**inputs(), config=config)
    assert result["state"] == "succeeded" and names == ["fixture_encoding"]
    assert result["token_budget"]["tokenizer"]["source"] == "tiktoken"
    assert result["token_budget"]["tokenizer"]["is_estimate"] is False
    assert result["token_budget"]["tokenizer"]["whole_request_is_estimate"] is True

    def missing(_name):
        raise ValueError("fixture encoding unavailable")

    monkeypatch.setattr(token_counting, "_tiktoken", missing)
    failed = service.generate(**inputs(), config=config)
    assert failed["error"]["code"] == "TOKENIZER_UNAVAILABLE" and len(adapter.calls) == 1
