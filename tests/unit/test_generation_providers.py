"""Protocol-level local HTTP tests; no external provider or corpus mutations."""

from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from unittest.mock import patch

import pytest

from generation.adapters import LLMAdapter, test_connection as probe
from generation.prompt_builder import build_messages
from generation.providers import payload
from generation.service import GenerationService
from generation.token_counting import TokenCounter, estimate_tokens
from generation.types import ModelConfig, RequestBudget
from test_generation_engine import request, response, FakeResponse


@pytest.fixture
def provider_server():
    calls, replies = [], []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(
                {
                    "path": self.path,
                    "body": body,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                }
            )
            status, headers, data = replies.pop(0)
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", calls, replies
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.mark.parametrize(
    "provider", ["openai_compatible", "anthropic", "gemini", "azure_openai", "ollama"]
)
def test_actual_http_protocol_roles_auth_usage(provider_server, provider):
    base, calls, replies = provider_server
    if provider == "anthropic":
        reply = {
            "content": [{"type": "text", "text": '{"ok":true}'}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 3},
        }
    elif provider == "gemini":
        reply = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"thought": True, "text": "hidden"}, {"text": '{"ok":true}'}]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
                "totalTokenCount": 8,
            },
        }
    else:
        reply = {
            "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
    replies.append((200, {"x-request-id": "loopback-1"}, reply))
    config = ModelConfig(
        provider=provider,
        model="test-model",
        base_url=base + "/v1",
        api_version="2024-10-21" if provider == "azure_openai" else None,
    )
    messages = [
        {"role": "system", "content": "Rules"},
        {"role": "user", "content": "Earlier"},
        {"role": "assistant", "content": "Prior answer"},
        {"role": "user", "content": "Current"},
    ]
    result = LLMAdapter(config, api_key="local-fixture-secret").generate(
        messages, response_schema={"type": "object"}, response_schema_name="test"
    )
    assert not result.error and result.raw_text == '{"ok":true}'
    assert result.usage["total_tokens"] == 8 and result.usage["cost"] is None
    assert len(calls) == 1 and result.provider_request_id == "loopback-1"
    sent = calls[0]
    assert "local-fixture-secret" not in json.dumps(sent["body"]) + sent["path"]
    if provider == "anthropic":
        assert sent["body"]["system"] == "Rules"
        assert [m["role"] for m in sent["body"]["messages"]] == ["user", "assistant", "user"]
        assert sent["headers"]["x-api-key"] == "local-fixture-secret"
        assert sent["body"]["output_config"]["format"]["type"] == "json_schema"
    elif provider == "gemini":
        assert sent["body"]["systemInstruction"]["parts"][0]["text"] == "Rules"
        assert [m["role"] for m in sent["body"]["contents"]] == ["user", "model", "user"]
        assert sent["headers"]["x-goog-api-key"] == "local-fixture-secret"
    else:
        assert sent["body"]["messages"] == messages
        if provider == "azure_openai":
            assert sent["path"].endswith("/chat/completions?api-version=2024-10-21")
            assert sent["headers"]["api-key"] == "local-fixture-secret"


def test_redirect_does_not_forward_secret_or_issue_second_call(provider_server):
    base, calls, replies = provider_server
    replies.append((307, {"Location": base + "/other"}, {}))
    result = LLMAdapter(ModelConfig(provider="local", base_url=base), api_key="secret").generate(
        [], response_schema={}, response_schema_name="test"
    )
    assert result.error["details"]["http_status"] == 307
    assert len(calls) == 1 and not result.error["retryable"]


def test_managed_missing_key_never_inherits_environment():
    config = ModelConfig(
        provider="openai", configuration_id="model-settings:missing", api_key_env="LLM_API_KEY"
    )
    with (
        patch.dict("os.environ", {"LLM_API_KEY": "must-not-send"}),
        patch("generation.adapters.open_provider") as transport,
    ):
        assert (
            LLMAdapter(config)
            .generate([], response_schema={}, response_schema_name="test")
            .error["code"]
            == "CONFIGURATION_ERROR"
        )
        assert (
            LLMAdapter(config, api_key=None)
            .generate([], response_schema={}, response_schema_name="test")
            .error["code"]
            == "CONFIGURATION_ERROR"
        )
        assert not transport.called


@pytest.mark.parametrize(
    "raw",
    ['{"ok":false}', '{"ok":true,"extra":1}', '{"ok":true,"ok":true}', '```json\n{"ok":true}\n```'],
)
def test_probe_requires_exact_json_and_erases_raw(raw):
    reply = {"choices": [{"message": {"content": raw}, "finish_reason": "stop"}]}
    with patch("generation.adapters.open_provider", return_value=FakeResponse(reply)):
        result = probe(ModelConfig(provider="local", base_url="http://localhost:1"))
    assert result.error["code"] == "PROVIDER_PROBE_INVALID" and result.raw_text == ""


@pytest.mark.parametrize("provider", ["anthropic", "gemini"])
def test_native_count_is_billed_to_same_request_budget(provider):
    count_reply = {"input_tokens": 400} if provider == "anthropic" else {"totalTokens": 400}
    answer = json.dumps(response())
    generation = (
        {
            "content": [{"type": "text", "text": answer}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 410, "output_tokens": 90},
        }
        if provider == "anthropic"
        else {
            "candidates": [{"content": {"parts": [{"text": answer}]}, "finishReason": "STOP"}],
            "usageMetadata": {
                "promptTokenCount": 410,
                "candidatesTokenCount": 90,
                "totalTokenCount": 500,
            },
        }
    )
    cfg = ModelConfig(provider=provider, model="test-model", tokenizer_provider="provider")
    events = []
    with patch(
        "generation.adapters.open_provider",
        side_effect=[FakeResponse(count_reply), FakeResponse(generation)],
    ) as calls:
        result = GenerationService(api_key="fixture").generate(
            request(config=cfg), on_attempt=events.append
        )
    assert result.succeeded and result.budget["consumed_calls"] == 2
    assert [e["stage"] for e in events if e["phase"] == "start"] == ["token_count", "generation"]
    assert result.usage["total_tokens"] == 500
    assert result.token_budget["provider_input_tokens"] == 400
    assert "count" in calls.call_args_list[0].args[0].full_url.lower()
    assert len(calls.call_args_list) == 2


def test_provider_count_rejects_window_before_generation():
    cfg = ModelConfig(provider="anthropic", tokenizer_provider="provider", window_tokens=5000)
    with patch(
        "generation.adapters.open_provider", return_value=FakeResponse({"input_tokens": 4500})
    ) as calls:
        result = GenerationService(api_key="fixture").generate(request(config=cfg))
    assert result.error["code"] == "CONTEXT_LIMIT" and calls.call_count == 1
    assert result.budget["consumed_calls"] == 1


def test_whole_payload_counter_covers_profile_schema_roles_and_unicode():
    cfg = ModelConfig(tokenizer_provider="estimate")
    counter = TokenCounter(cfg)
    assert counter.count("科学") == 4 and counter.count("science") == 3
    assert counter.metadata["is_estimate"] is True
    original = request(config=cfg)
    _, selected, baseline, _ = build_messages(original, counter)
    messages, _, profiled, _ = build_messages(
        replace(original, profile={"policy": "Explain prerequisites. " * 50}), counter
    )
    assert profiled["input_reserved_tokens"] > baseline["input_reserved_tokens"]
    assert len(selected) == 1 and profiled["token_counting"]["whole_request_is_estimate"]
    assert counter.request_input(
        messages, {"type": "object", "description": "Extra " * 50}
    ) > counter.request_input(messages, {})


def test_provider_thinking_is_explicit_and_benchmark_profile_stays_frozen():
    cfg = ModelConfig(
        provider="openai_compatible",
        model="deepseek-flash",
        thinking_enabled=False,
        structured_output_mode="json_object",
    )
    body = payload(cfg, [], {}, "test")
    assert body["thinking"] == {"type": "disabled"} and body["response_format"] == {
        "type": "json_object"
    }
    assert "thinking" not in payload(ModelConfig(), [], {}, "test")
    messages, evidence, _, effective = build_messages(
        request(
            mode="benchmark_openqa",
            condition="E0",
            profile={"policy": "private-style"},
            history=[{"role": "user", "content": "private-history"}],
        )
    )
    assert not evidence and not effective.history and effective.profile is None
    assert "private-style" not in json.dumps(messages) and "private-history" not in json.dumps(
        messages
    )


def test_gemini_schema_literal_uses_supported_enum_without_loosening_local_contract():
    from generation.providers import provider_schema
    from generation.parser import parse_response, ResponseValidationError

    converted = provider_schema(
        {"type": "string", "const": "chat_response_v1", "minLength": 1}, "gemini"
    )
    assert converted == {"type": "string", "enum": ["chat_response_v1"]}
    with pytest.raises(ResponseValidationError):
        parse_response(
            json.dumps(response(schema_version="wrong")),
            mode="interactive_chat",
            condition="E1",
            evidence_ids=["ev_001"],
        )


def test_pinned_local_tokenizer_manifest_failure_is_explicit(tmp_path):
    import hashlib
    from types import SimpleNamespace
    from generation.token_counting import _huggingface

    content = b'{"fixture":"tokenizer"}'
    (tmp_path / "tokenizer.json").write_bytes(content)
    (tmp_path / "SOURCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "revision": "fixed",
                "files": [
                    {"file": "tokenizer.json", "sha256": hashlib.sha256(content).hexdigest()}
                ],
            }
        ),
        encoding="utf-8",
    )
    tokenizer = SimpleNamespace(encode=lambda text, **kwargs: text.split(), name_or_path="fixture")
    fake = SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=lambda *args, **kwargs: tokenizer)
    )
    with (
        patch.dict("sys.modules", {"transformers": fake}),
        patch("generation.token_counting.version", return_value="fixture"),
    ):
        counted = TokenCounter(
            ModelConfig(
                tokenizer_provider="huggingface",
                tokenizer_local_path=str(tmp_path),
                tokenizer_revision="fixed",
                token_count_fallback="error",
            )
        )
        assert counted.count("two tokens") == 2
        assert (
            counted.metadata["files_sha256"]["tokenizer.json"]
            == hashlib.sha256(content).hexdigest()
        )
        _huggingface.cache_clear()
        (tmp_path / "tokenizer.json").write_bytes(b"changed")
        with pytest.raises(ValueError, match="TOKENIZER_UNAVAILABLE"):
            TokenCounter(
                ModelConfig(
                    tokenizer_provider="huggingface",
                    tokenizer_local_path=str(tmp_path),
                    tokenizer_revision="fixed",
                    token_count_fallback="error",
                )
            )


def test_configuration_failure_records_selection_but_no_submitted_evidence():
    outcome = GenerationService(api_key=None).generate(
        request(config=ModelConfig(provider="openai", configuration_id="model-settings:missing"))
    )
    assert outcome.error["code"] == "CONFIGURATION_ERROR"
    assert outcome.token_budget["selected_count"] == 1
    assert outcome.token_budget["submitted_count"] == 0 and outcome.evidence == []


def test_empty_provider_response_retries_once_with_same_budget_then_publishes():
    empty = {
        "choices": [{"message": {"content": " " * 209}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 209, "total_tokens": 509},
    }
    valid = {"choices": [{"message": {"content": json.dumps(response())}, "finish_reason": "stop"}]}
    cfg = ModelConfig(
        provider="local", base_url="http://localhost:1/v1", structured_output_mode="json_object"
    )
    with patch(
        "generation.adapters.open_provider", side_effect=[FakeResponse(empty), FakeResponse(valid)]
    ) as transport:
        result = GenerationService(sleep=lambda _: None).generate(request(config=cfg))
    assert result.succeeded and transport.call_count == 2
    assert result.budget["consumed_calls"] == 2 and result.budget["transient_retries"] == 1
    assert result.attempts[0]["error"]["code"] == "EMPTY_RESPONSE"
    assert result.attempts[0]["error"]["details"]["content_characters"] == 209
    sent = json.loads(transport.call_args.args[0].data)
    assert sum(m["role"] == "system" for m in sent["messages"]) == 1
    assert "not examples of the required output format" in sent["messages"][0]["content"]


def test_format_repair_explains_refusal_marker_rule_without_changing_validator():
    invalid = response(
        response_type="refusal",
        short_answer=None,
        citations=[],
        refusal_reason="INSUFFICIENT_EVIDENCE",
    )
    valid = {
        **invalid,
        "answer_text": "The passages do not support this specific additional claim.",
    }
    from test_generation_engine import ScriptedAdapter

    adapter = ScriptedAdapter([json.dumps(invalid), json.dumps(valid)])
    result = GenerationService(adapter).generate(request())
    assert result.succeeded and result.response["response_type"] == "refusal"
    assert result.attempts[0]["error"]["code"] == "CITATION_MARKER_MISMATCH"
    feedback = adapter.calls[1][0][-1]["content"]
    assert "A refusal must have citations=[] and no inline evidence markers" in feedback
    assert "Allowed current evidence IDs: ev_001" in feedback
