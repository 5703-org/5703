"""Runtime response, mode-boundary, provider and shared budget regressions."""

from dataclasses import replace
import hashlib
import json
from unittest.mock import patch
from urllib.error import HTTPError
import pytest

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation.adapters import LLMAdapter, retry_after
from generation.parser import parse_response, ResponseValidationError
from generation.prompt_builder import build_messages
from generation.types import ProviderResult, failure
from personalisation import compile_profile


def evidence(
    text="Photosynthesis converts light energy into chemical energy stored in sugars. Chlorophyll captures light needed for photosynthesis.",
    **updates,
):
    return {
        "evidence_id": "ev_001",
        "chunk_id": "chunk1",
        "asset_id": "asset1",
        "processing_id": "proc1",
        "source_title": "Authored biology fixture",
        "section": "Photosynthesis",
        "pages": [1],
        "locator": "page 1",
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "context_order": 1,
        "inherited_from": None,
        **updates,
    }


def request(**updates):
    return GenerationRequest(
        **{
            "request_id": "req1",
            "mode": "interactive_chat",
            "condition": "E1",
            "question": "What is photosynthesis?",
            "evidence": [evidence()],
            **updates,
        }
    )


def response(**updates):
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "Photosynthesis captures light. [ev_001]",
        "short_answer": "Light capture",
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        **updates,
    }


class ScriptedAdapter:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        value = next(self.results)
        return (
            value
            if isinstance(value, ProviderResult)
            else ProviderResult(raw_text=value, finish_reason="stop")
        )


@pytest.mark.parametrize(
    "raw",
    [
        "```json\n{}\n```",
        "{} {}",
        "{} trailing",
        "[]",
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":1,"x":2}',
        '{"nested":{"x":1,"x":2}}',
    ],
)
def test_strict_json_negatives(raw):
    with pytest.raises(ResponseValidationError):
        parse_response(raw, mode="interactive_chat", condition="E1", evidence_ids=["ev_001"])


@pytest.mark.parametrize(
    "updates",
    [
        {"confidence": True},
        {"extra": 1},
        {"answer_text": "No marker"},
        {"citations": ["ev_999"], "answer_text": "Wrong source. [ev_999]"},
        {"response_type": "answer", "citations": [], "answer_text": "Unsupported"},
    ],
)
def test_schema_and_selected_source_negatives(updates):
    with pytest.raises(ResponseValidationError):
        parse_response(
            json.dumps(response(**updates)),
            mode="interactive_chat",
            condition="E1",
            evidence_ids=["ev_001"],
        )


def test_actual_role_order_profile_off_and_frozen_benchmark_boundary():
    history = [
        {"id": "u1", "role": "user", "content": "What is photosynthesis?"},
        {"id": "a1", "role": "assistant", "content": "Earlier explanation. [ev_001]"},
    ]
    messages, selected, _, _ = build_messages(
        request(
            question="Why does it need light?",
            history=history,
            profile=compile_profile(None, False),
        )
    )
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert "[ev_001]" not in messages[2]["content"]
    assert selected[0]["text"] in messages[0]["content"]
    for mode in ("benchmark_openqa", "benchmark_mcq"):
        command = request(
            mode=mode,
            question_id="q1",
            options={k: v for k, v in zip("ABCD", ["sugar", "rock", "metal", "plastic"])}
            if mode.endswith("mcq")
            else None,
            history=history,
            summary="Secret old conversation",
            profile=compile_profile({"level": "advanced"}),
        )
        clean = replace(command, history=[], summary=None, profile=None)
        assert build_messages(command)[0] == build_messages(clean)[0]
    assert "OPTION_A" not in json.dumps(messages)
    assert "evidence_status" not in json.dumps(messages)


def test_mock_changes_with_current_evidence_and_history_sensitive_query():
    engine = GenerationService()
    a = engine.generate(request())
    b = engine.generate(
        request(
            question="Why does it need light?",
            history=[{"id": "u1", "role": "user", "content": "What is photosynthesis?"}],
        )
    )
    assert a.succeeded and b.succeeded
    assert "light" in b.response["answer_text"]
    assert b.response["citations"] == ["ev_001"]
    assert (
        engine.generate(request(question="Why does it need light?", history=[])).response[
            "response_type"
        ]
        == "clarification"
    )
    assert (
        engine.generate(request(question="Hello", evidence=[])).response["response_type"]
        == "social"
    )
    assert engine.generate(request(evidence=[])).response["refusal_reason"] == "NO_EVIDENCE"
    unrelated = engine.generate(
        request(evidence=[evidence("A pulley is a grooved wheel with a rope.")])
    )
    assert unrelated.response["refusal_reason"] == "INSUFFICIENT_EVIDENCE"


def test_shared_four_call_budget_covers_transient_and_one_format_repair():
    transient = ProviderResult(
        error=failure("PROVIDER_HTTP_ERROR", "429", retryable=True, retry_after_seconds=0)
    )
    adapter = ScriptedAdapter([transient, transient, "not json", json.dumps(response())])
    events = []
    outcome = GenerationService(adapter, sleep=lambda _: None).generate(
        request(), on_attempt=events.append
    )
    assert outcome.succeeded
    assert outcome.budget["consumed_calls"] == 4
    assert outcome.budget["transient_retries"] == 2
    assert outcome.budget["format_repairs"] == 1
    assert [event["budget"]["consumed_calls"] for event in events if event["phase"] == "start"] == [
        1,
        2,
        3,
        4,
    ]
    assert len([event for event in events if event["phase"] == "finish"]) == 4
    assert outcome.usage["total_tokens"] is None and outcome.usage["cost"] is None


def test_invalid_twice_is_error_not_refusal_and_retry_retains_budget():
    budget = RequestBudget()
    adapter = ScriptedAdapter(["bad", "bad again"])
    failed = GenerationService(adapter).generate(request(), budget)
    assert failed.response is None and failed.error["code"] == "INVALID_JSON"
    restored = RequestBudget.from_dict(failed.budget)
    retry = GenerationService(ScriptedAdapter(["still invalid"])).generate(request(), restored)
    assert retry.budget["format_repairs"] == 1
    assert retry.budget["consumed_calls"] == 3
    assert len(retry.attempts) == 1
    exhausted = GenerationService(ScriptedAdapter([])).generate(
        request(), RequestBudget(consumed_calls=4)
    )
    assert exhausted.error["code"] == "BUDGET_EXHAUSTED"


def test_complete_json_with_length_finish_never_publishes_or_repairs():
    adapter = ScriptedAdapter(
        [ProviderResult(raw_text=json.dumps(response()), finish_reason="length")]
    )
    result = GenerationService(adapter).generate(request())
    assert result.response is None and result.error["code"] == "OUTPUT_TRUNCATED"
    assert result.budget["consumed_calls"] == 1


def test_context_budget_includes_profile_schema_and_output_and_drops_whole_chunks():
    passages = [
        evidence(
            "Photosynthesis " + "different words in sentences " * 500,
            evidence_id=f"ev_{i:03d}",
            chunk_id=f"c{i}",
        )
        for i in range(1, 4)
    ]
    _, selected, report, _ = build_messages(request(evidence=passages))
    assert 0 < len(selected) < len(passages)
    assert report["excluded_evidence"]
    assert all(
        item["text_hash"] == hashlib.sha256(item["text"].encode()).hexdigest() for item in selected
    )
    assert report["total_reserved_tokens"] <= report["window_tokens"]
    assert report["output_reserved_tokens"] == 1024
    with pytest.raises(ResponseValidationError, match="exceed"):
        build_messages(request(config=ModelConfig(window_tokens=100)))
    with pytest.raises(ResponseValidationError, match="hash"):
        build_messages(request(evidence=[evidence(text_hash="wrong")]))


class FakeResponse:
    headers = {"x-request-id": "provider-request-1"}

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, *_):
        return json.dumps(self.payload).encode()


def live_config():
    return ModelConfig(
        provider="openai_compatible",
        model="explicit-test-model",
        base_url="https://example.invalid/v1",
        api_key_env="TEST_LOCAL_ONLY_KEY",
    )


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"choices": []}, "PROVIDER_RESPONSE_ERROR"),
        ({"choices": [{}]}, "PROVIDER_RESPONSE_ERROR"),
        ({"choices": [{"message": {}}]}, "PROVIDER_RESPONSE_ERROR"),
        ({"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}, "EMPTY_RESPONSE"),
        (
            {"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]},
            "OUTPUT_TRUNCATED",
        ),
    ],
)
def test_provider_empty_and_truncated_envelopes(payload, code):
    with (
        patch.dict("os.environ", {"TEST_LOCAL_ONLY_KEY": "dummy"}),
        patch("generation.adapters.open_provider", return_value=FakeResponse(payload)),
    ):
        result = LLMAdapter(live_config()).generate(
            [{"role": "user", "content": "Q"}], response_schema={}, response_schema_name="test"
        )
    assert result.error["code"] == code


@pytest.mark.parametrize(
    "status,retryable", [(429, True), (500, True), (503, True), (401, False), (403, False)]
)
def test_provider_http_metadata_and_retryability(status, retryable):
    exception = HTTPError(
        "https://example.invalid/v1",
        status,
        "failure",
        {"Retry-After": "2", "x-request-id": "request-42"},
        None,
    )
    with (
        patch.dict("os.environ", {"TEST_LOCAL_ONLY_KEY": "dummy"}),
        patch("generation.adapters.open_provider", side_effect=exception),
    ):
        result = LLMAdapter(live_config()).generate(
            [], response_schema={}, response_schema_name="test"
        )
    assert result.error["retryable"] is retryable
    assert result.error["details"]["http_status"] == status
    assert result.error["details"]["retry_after_seconds"] == 2
    assert result.provider_request_id == "request-42"


def test_http_adapter_sends_actual_roles_and_unknown_usage_remains_null():
    messages = [
        {"role": "system", "content": "Rules"},
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Prior"},
        {"role": "user", "content": "Current"},
    ]
    payload = {
        "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
    }
    with (
        patch.dict("os.environ", {"TEST_LOCAL_ONLY_KEY": "dummy"}),
        patch("generation.adapters.open_provider", return_value=FakeResponse(payload)) as call,
    ):
        result = LLMAdapter(live_config()).generate(
            messages, response_schema={}, response_schema_name="test"
        )
    assert json.loads(call.call_args.args[0].data)["messages"] == messages
    assert result.usage["total_tokens"] == 16
    assert result.usage["reasoning_tokens"] is None and result.usage["cost"] is None
    with patch.dict("os.environ", {}, clear=True):
        missing = GenerationService().generate(request(config=live_config()))
    assert missing.error["code"] == "CONFIGURATION_ERROR" and missing.model_mode == "live"
