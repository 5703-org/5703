"""Synthetic fixed-route and optional SDK checks, without sockets or private configuration."""

from dataclasses import asdict, replace
from io import BytesIO
import json
import math
from urllib.error import HTTPError

import httpx
import pytest

from app.modules.model_settings.schemas import ModelValues
from generation.adapters import LLMAdapter
from generation.openrouter_routes import (
    BASE_URL,
    CURRENT_PROFILE_IDS,
    PROFILES,
    VERSION,
    preferences,
)
from generation.provider_diagnostics import gateway_http_diagnostic, gateway_reported_cost
from generation.providers import endpoint, headers, payload
from generation.types import ModelConfig


KEY = "synthetic-gateway-credential"
MESSAGES = [{"role": "user", "content": "synthetic-learner-sensitive-marker"}]
SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def structured_routing_probe(profile_id):
    if PROFILES[profile_id].checker_transport == "compact_findings_v3":
        return (
            {
                "type": "object",
                "properties": {"ok": {"type": "boolean", "const": True}},
                "required": ["ok"],
                "additionalProperties": False,
            },
            "compatibility_structured_v2",
        )
    return SCHEMA, "synthetic_route"


def configured(profile_id="qwen38_alibaba_v1"):
    route = PROFILES[profile_id]
    return ModelConfig(
        provider="openai_compatible",
        model=route.model,
        base_url=BASE_URL,
        max_tokens=64,
        temperature=0 if route.temperature_supported else None,
        configuration_id="model-settings:synthetic-gateway",
        openrouter_route_profile=profile_id,
    )


def completion(config, *, usage=None, content='{"ok":true}', reason="stop", model=None):
    return {
        "id": "synthetic-completion-1",
        "object": "chat.completion",
        "created": 1,
        "model": model or config.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": reason,
            }
        ],
        **({"usage": usage} if usage is not None else {}),
    }


class Reply:
    def __init__(self, body, status=200, headers=None):
        self.body = json.dumps(body).encode()
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.body[:limit]


@pytest.fixture(autouse=True)
def no_socket(monkeypatch):
    def reject(*_args, **_kwargs):
        raise AssertionError("Synthetic route tests must not resolve or connect a socket")

    monkeypatch.setattr("socket.create_connection", reject)
    monkeypatch.setattr("socket.getaddrinfo", reject)


@pytest.mark.parametrize("profile_id", tuple(PROFILES))
def test_explicit_profiles_preserve_one_key_exact_model_and_fixed_routing(profile_id):
    config = configured(profile_id)
    config.validate()
    route = PROFILES[profile_id]
    schema, schema_name = structured_routing_probe(profile_id)
    body = payload(config, MESSAGES, schema, schema_name)
    assert endpoint(config) == BASE_URL + "/chat/completions"
    assert headers(config, KEY) == {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + KEY,
    }
    assert body["model"] == route.model and body["messages"] == MESSAGES
    assert body["provider"]["order"] == body["provider"]["only"] == [route.provider_slug]
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["require_parameters"] is True
    assert "models" not in body and "tools" not in body
    assert ModelConfig.from_dict(config.to_dict()) == config
    public = {
        key: value
        for key, value in config.to_dict().items()
        if key not in {"configuration_id", "api_key_env"}
    }
    assert ModelValues(**public).openrouter_route_profile == profile_id
    if route.prompt_price_cap is not None:
        assert body["provider"]["max_price"] == {
            "prompt": route.prompt_price_cap,
            "completion": route.completion_price_cap,
        }


@pytest.mark.parametrize(
    "changed",
    [
        {"openrouter_route_profile": None},
        {"openrouter_route_profile": "unverified-family"},
        {"openrouter_route_profile": ["qwen38_alibaba_v1"]},
        {"model": "qwen/unverified-model"},
        {"provider": "openai"},
        {"base_url": "https://provider.example.invalid/v1"},
        {"base_url": "https://openrouter.ai/api/v1/chat/completions"},
        {"base_url": "https://openrouter.ai:443/api/v1"},
        {"base_url": "http://localhost:1/v1"},
        {"auth_header": "api-key"},
        {"api_version": "synthetic-version"},
        {
            "capability_version": "provider_capabilities_v1",
            "capabilities": {"api_style": "responses"},
        },
    ],
)
def test_invalid_route_stops_before_any_transport(monkeypatch, changed):
    calls = []
    monkeypatch.setattr(
        "generation.adapters.open_provider", lambda *args, **kwargs: calls.append(args)
    )
    result = LLMAdapter(replace(configured(), **changed), api_key=KEY).generate(
        MESSAGES, response_schema=SCHEMA, response_schema_name="synthetic_route"
    )
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False and calls == []
    assert result.usage["cost"] is None


@pytest.mark.parametrize("key", [None, "", "\nsynthetic", " " * 3])
def test_gateway_missing_or_invalid_key_does_not_inherit_environment(monkeypatch, key):
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-synthetic-env-key")
    calls = []
    monkeypatch.setattr(
        "generation.adapters.open_provider", lambda *args, **kwargs: calls.append(args)
    )
    result = LLMAdapter(configured(), api_key=key).generate_basic(MESSAGES)
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False and calls == []


def test_managed_gateway_without_injected_credential_has_no_environment_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("SYNTHETIC_GATEWAY_KEY", KEY)
    result = LLMAdapter(replace(configured(), api_key_env="SYNTHETIC_GATEWAY_KEY")).generate_basic(
        MESSAGES
    )
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False


def test_no_default_route_and_non_gateway_legacy_serialization_and_wire_stay_compatible():
    config = ModelConfig(
        provider="openai_compatible",
        model="synthetic",
        base_url="https://provider.example.invalid/v1",
    )
    assert config.openrouter_route_profile is None
    config.validate()
    assert preferences(config) is None
    legacy = asdict(config)
    legacy.pop("openrouter_route_profile")
    assert config.to_dict() == legacy
    assert "provider" not in payload(config, MESSAGES, SCHEMA, "synthetic")
    assert headers(config, None) == {"Content-Type": "application/json"}
    assert VERSION == "openrouter_fixed_routes_v2"
    assert CURRENT_PROFILE_IDS == (
        "openai_luna_v2",
        "qwen38_alibaba_v2",
        "glm53_deepinfra_fp4_v1",
        "gemini35_google_vertex_v1",
        "gemini35_google_vertex_minimal_v1",
        "gemini35_google_vertex_compact_checker_v3",
    )
    with pytest.raises(TypeError):
        PROFILES["unreviewed"] = PROFILES["qwen38_alibaba_v1"]


@pytest.mark.parametrize(
    "profile_id,reasoning",
    [
        ("openai_luna_v2", {"enabled": False}),
        ("qwen38_alibaba_v2", {"enabled": False}),
        ("glm53_deepinfra_fp4_v1", {"effort": "low"}),
    ],
)
@pytest.mark.parametrize("basic", [False, True])
def test_current_routes_pin_supported_reasoning_without_changing_output_limit(
    profile_id, reasoning, basic
):
    config = configured(profile_id)
    wire = payload(config, MESSAGES, SCHEMA, "synthetic", basic=basic)
    assert wire["reasoning"] == reasoning
    assert "thinking" not in wire and "reasoning_effort" not in wire
    assert wire["max_tokens"] == config.max_tokens == 64
    assert wire["messages"] == MESSAGES
    assert wire["provider"]["only"] == [PROFILES[profile_id].provider_slug]
    if profile_id == "glm53_deepinfra_fp4_v1":
        assert wire["provider"]["only"] == ["deepinfra/fp4"]
        assert wire["provider"]["max_price"] == {"prompt": 0.15, "completion": 0.5}


@pytest.mark.parametrize("profile_id", CURRENT_PROFILE_IDS)
@pytest.mark.parametrize(
    "changed",
    [
        {"thinking_enabled": True},
        {"thinking_enabled": False},
        {"reasoning_effort": "low"},
        {"reasoning_effort": "none"},
    ],
)
def test_current_fixed_reasoning_conflicts_stop_before_transport(monkeypatch, profile_id, changed):
    calls = []
    monkeypatch.setattr(
        "generation.adapters.open_provider", lambda *args, **kwargs: calls.append(args)
    )
    result = LLMAdapter(replace(configured(profile_id), **changed), api_key=KEY).generate_basic(
        MESSAGES
    )
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False and calls == []
    assert result.usage["cost"] is None


@pytest.mark.parametrize(
    "profile_id",
    [
        "openai_luna_v1",
        "qwen38_alibaba_v1",
        "openai_nano_v1",
        "qwen_streamlake_v1",
        "mistral_deepinfra_fp8_v1",
    ],
)
@pytest.mark.parametrize("basic", [False, True])
def test_predecessor_profiles_keep_their_exact_reasoning_omission(profile_id, basic):
    config = configured(profile_id)
    wire = payload(config, MESSAGES, SCHEMA, "synthetic", basic=basic)
    assert "reasoning" not in wire and "thinking" not in wire
    assert PROFILES[profile_id].reasoning_enabled is None
    assert PROFILES[profile_id].reasoning_effort is None


def test_luna_unsupported_temperature_is_rejected_before_transport():
    with pytest.raises(ValueError, match="protocol"):
        replace(configured("openai_luna_v1"), temperature=0).validate()
    assert "temperature" not in payload(configured("openai_luna_v1"), MESSAGES, SCHEMA, "synthetic")


def test_legacy_gateway_public_configuration_is_readable_without_allowing_execution(monkeypatch):
    config = replace(configured(), openrouter_route_profile=None)
    public = {
        key: value
        for key, value in config.to_dict().items()
        if key not in {"configuration_id", "api_key_env"}
    }
    legacy = ModelValues(**public)
    assert legacy.model == config.model and legacy.openrouter_route_profile is None
    with pytest.raises(ValueError, match="explicit fixed"):
        config.validate()
    calls = []
    monkeypatch.setattr(
        "generation.adapters.open_provider", lambda *args, **kwargs: calls.append(args)
    )
    result = LLMAdapter(config, api_key=KEY).generate_basic(MESSAGES)
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False and calls == []


@pytest.mark.parametrize("profile_id", ["openai_luna_v1", "openai_nano_v1"])
def test_openai_gateway_strict_schema_preserves_nullable_optional_fields(profile_id):
    schema = {
        "type": "object",
        "properties": {
            "required_text": {"type": "string"},
            "optional_note": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "default": None,
            },
        },
        "required": ["required_text"],
    }
    wire = payload(configured(profile_id), MESSAGES, schema, "synthetic")
    transformed = wire["response_format"]["json_schema"]["schema"]
    assert transformed["required"] == ["required_text", "optional_note"]
    assert transformed["additionalProperties"] is False
    assert (
        transformed["properties"]["optional_note"]["anyOf"]
        == schema["properties"]["optional_note"]["anyOf"]
    )
    assert "default" not in transformed["properties"]["optional_note"]
    assert schema["required"] == ["required_text"] and "additionalProperties" not in schema


@pytest.mark.parametrize("profile_id", tuple(PROFILES))
def test_actual_native_request_crosses_installed_sdk_mock_boundary_once(monkeypatch, profile_id):
    openai = pytest.importorskip("openai", reason="Optional SDK bridge; production uses urllib")
    config = configured(profile_id)
    schema, schema_name = structured_routing_probe(profile_id)
    captured, native_calls = [], []

    def mock_transport(request):
        captured.append(request)
        return httpx.Response(
            200, json=completion(config), headers={"x-request-id": "synthetic-request-1"}
        )

    with httpx.Client(
        transport=httpx.MockTransport(mock_transport), trust_env=False, follow_redirects=False
    ) as client:
        sdk = openai.OpenAI(
            api_key=KEY,
            base_url=BASE_URL,
            max_retries=0,
            http_client=client,
            organization="synthetic-org",
            project="synthetic-project",
        )

        def bridge(envelope, timeout):
            native_calls.append(envelope)
            body = json.loads(envelope.data)
            extra = {"provider": body.pop("provider")}
            if "reasoning" in body:
                extra["reasoning"] = body.pop("reasoning")
            raw = sdk.chat.completions.with_raw_response.create(
                **body, extra_body=extra, timeout=timeout
            )
            return Reply(
                raw.http_response.json(),
                raw.http_response.status_code,
                dict(raw.http_response.headers),
            )

        monkeypatch.setattr("generation.adapters.open_provider", bridge)
        result = LLMAdapter(config, api_key=KEY).generate(
            MESSAGES, response_schema=schema, response_schema_name=schema_name
        )
    assert result.error is None and result.raw_text == '{"ok":true}'
    assert result.usage["cost"] is None
    assert len(native_calls) == len(captured) == 1
    assert str(captured[0].url) == native_calls[0].full_url == BASE_URL + "/chat/completions"
    assert json.loads(captured[0].content) == json.loads(native_calls[0].data)
    assert (
        captured[0].headers["authorization"]
        == native_calls[0].get_header("Authorization")
        == "Bearer " + KEY
    )
    assert captured[0].headers["content-type"] == "application/json"
    assert json.loads(captured[0].content)["max_tokens"] == 64


@pytest.mark.parametrize(
    "status,category",
    [
        (401, "authentication_rejected"),
        (402, "credit_or_budget_rejected"),
        (403, "access_or_policy_denied"),
        (404, "resource_or_route_not_found"),
        (429, "rate_or_quota_limited"),
        (502, "model_or_provider_unavailable"),
        (503, "route_unavailable"),
        (500, "unknown_provider_failure"),
    ],
)
def test_native_and_sdk_error_boundary_preserves_status_unknown_cost_and_zero_retry(
    monkeypatch, status, category
):
    openai = pytest.importorskip("openai", reason="Optional SDK bridge; production uses urllib")
    calls = []
    body = {"error": {"code": status, "message": KEY + MESSAGES[0]["content"]}}

    def mock_transport(request):
        calls.append(request)
        return httpx.Response(status, json=body, headers={"Retry-After": "1"})

    with httpx.Client(transport=httpx.MockTransport(mock_transport), trust_env=False) as client:
        sdk = openai.OpenAI(
            api_key=KEY,
            base_url=BASE_URL,
            max_retries=0,
            http_client=client,
            organization="synthetic-org",
            project="synthetic-project",
        )

        def bridge(envelope, timeout):
            wire = json.loads(envelope.data)
            extra = {"provider": wire.pop("provider")}
            if "reasoning" in wire:
                extra["reasoning"] = wire.pop("reasoning")
            try:
                sdk.chat.completions.create(**wire, extra_body=extra, timeout=timeout)
            except openai.APIStatusError as exc:
                raise HTTPError(
                    envelope.full_url,
                    exc.status_code,
                    "Synthetic SDK failure",
                    dict(exc.response.headers),
                    BytesIO(exc.response.content),
                ) from None
            raise AssertionError("Expected synthetic HTTP failure")

        monkeypatch.setattr("generation.adapters.open_provider", bridge)
        result = LLMAdapter(configured(), api_key=KEY).generate_basic(MESSAGES)
    assert len(calls) == 1 and result.request_submitted is True
    assert result.error["code"] == "PROVIDER_HTTP_ERROR" and result.error["retryable"] is False
    assert result.diagnostic["http_status"] == status
    assert result.diagnostic["gateway_failure_category"] == category
    assert result.usage["cost"] is None
    assert KEY not in json.dumps(asdict(result)) and MESSAGES[0]["content"] not in json.dumps(
        asdict(result)
    )


@pytest.mark.parametrize("placement", ["top", "choice"])
def test_http200_error_is_not_success_and_does_not_fabricate_http_status(monkeypatch, placement):
    detail = {"code": 403, "message": KEY, "metadata": {"error_type": "refusal", "raw": MESSAGES}}
    body = (
        {"error": detail}
        if placement == "top"
        else {
            "choices": [
                {"message": {"content": "partial"}, "finish_reason": "error", "error": detail}
            ]
        }
    )
    monkeypatch.setattr("generation.adapters.open_provider", lambda *_args, **_kwargs: Reply(body))
    result = LLMAdapter(configured(), api_key=KEY, retain_invalid_output=True).generate_basic(
        MESSAGES
    )
    assert result.error["code"] == "PROVIDER_GATEWAY_ERROR" and result.raw_text == ""
    assert result.diagnostic["http_status"] == 200
    assert result.diagnostic["gateway_embedded_error_code"] == 403
    assert result.diagnostic["gateway_failure_category"] == "model_content_refusal"
    assert result.usage["cost"] is None and result.error["retryable"] is False
    assert "partial" not in json.dumps(asdict(result)) and KEY not in json.dumps(asdict(result))


@pytest.mark.parametrize(
    "detail,category",
    [
        ({"code": "invalid_json_schema"}, "request_schema_rejected"),
        ({"code": "unsupported_parameter"}, "request_parameter_rejected"),
        ({"metadata": {"error_type": "permission_denied"}}, "access_or_policy_denied"),
        ({"metadata": {"error_type": "provider_unavailable"}}, "model_or_provider_unavailable"),
        ({"metadata": {"error_type": "authentication"}}, "authentication_rejected"),
        (
            {
                "code": MESSAGES[0]["content"],
                "param": MESSAGES[0]["content"],
                "metadata": {"error_type": KEY},
            },
            "unknown_provider_failure",
        ),
        ({"code": {}, "param": [], "metadata": {"error_type": []}}, "unknown_provider_failure"),
    ],
)
def test_only_recognized_gateway_evidence_survives_redacted_diagnostic(detail, category):
    diagnostic = gateway_http_diagnostic(
        400, json.dumps({"error": detail}).encode(), secrets=(KEY,), messages=MESSAGES
    )
    assert diagnostic["gateway_failure_category"] == category
    encoded = json.dumps(diagnostic)
    assert KEY not in encoded and MESSAGES[0]["content"] not in encoded


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (True, None),
        (-1, None),
        ("0.01", None),
        (math.inf, None),
        (math.nan, None),
        (10**1000, None),
        (0, 0),
        (0.000012, 0.000012),
    ],
)
def test_reported_cost_is_explicit_finite_nonnegative_and_never_a_bill(value, expected):
    assert gateway_reported_cost({"usage": {"cost": value}}) == expected


def test_native_reported_cost_remains_separate_from_missing_usage_and_model_identity(monkeypatch):
    config = configured()
    monkeypatch.setattr(
        "generation.adapters.open_provider",
        lambda *_args, **_kwargs: Reply(
            completion(config, usage={"cost": 0.000012}, model="qwen/qwen3.8-flash-20260826")
        ),
    )
    result = LLMAdapter(config, api_key=KEY).generate_basic(MESSAGES)
    assert result.error is None and result.usage["cost"] == 0.000012
    assert result.usage["input_tokens"] is None and result.usage["total_tokens"] is None
    monkeypatch.setattr(
        "generation.adapters.open_provider",
        lambda *_args, **_kwargs: Reply(completion(config, model=KEY)),
    )
    mismatch = LLMAdapter(config, api_key=KEY).generate_basic(MESSAGES)
    assert mismatch.error["code"] == "PROVIDER_ROUTE_MODEL_MISMATCH" and mismatch.raw_text == ""
    assert mismatch.model == config.model and KEY not in json.dumps(asdict(mismatch))


@pytest.mark.parametrize(
    "body,category",
    [
        ({}, "provider_response_schema_invalid"),
        (
            {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
            "model_output_empty",
        ),
        (
            {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]},
            "model_output_truncated",
        ),
        (
            {
                "choices": [
                    {"message": {"content": None, "refusal": "blocked"}, "finish_reason": "stop"}
                ]
            },
            "model_content_refusal",
        ),
    ],
)
def test_response_schema_and_model_content_failures_have_distinct_free_observations(
    monkeypatch, body, category
):
    monkeypatch.setattr("generation.adapters.open_provider", lambda *_args, **_kwargs: Reply(body))
    result = LLMAdapter(configured(), api_key=KEY).generate_basic(MESSAGES)
    assert result.error is not None and result.error["retryable"] is False
    assert result.diagnostic["gateway_failure_category"] == category
    assert result.usage["cost"] is None


def test_invalid_json_preserves_the_observed_http200_status(monkeypatch):
    reply = Reply({})
    reply.body = b"not-json"
    monkeypatch.setattr("generation.adapters.open_provider", lambda *_args, **_kwargs: reply)
    result = LLMAdapter(configured(), api_key=KEY).generate_basic(MESSAGES)
    assert result.error["code"] == "PROVIDER_RESPONSE_ERROR"
    assert result.diagnostic["http_status"] == 200
    assert result.diagnostic["gateway_failure_category"] == "provider_response_schema_invalid"
    assert result.usage["cost"] is None


def test_fixed_gateway_timeout_is_uncertain_and_cannot_automatically_retry(monkeypatch):
    calls = []

    def timeout(*args, **_kwargs):
        calls.append(args)
        raise TimeoutError("Synthetic timeout")

    monkeypatch.setattr("generation.adapters.open_provider", timeout)
    result = LLMAdapter(configured(), api_key=KEY).generate_basic(MESSAGES)
    assert len(calls) == 1
    assert result.error["code"] == "PROVIDER_TIMEOUT"
    assert result.error["retryable"] is False and result.error["details"]["uncertain"] is True
    assert result.usage["cost"] is None


@pytest.mark.parametrize(
    "schema_name,code",
    [
        ("synthetic_route", "COMPACT_CHECKER_SCHEMA_UNSUPPORTED"),
        ("compatibility_structured_v2", "COMPACT_STRUCTURED_PROBE_SCHEMA_CHANGED"),
    ],
)
def test_compact_route_rejects_unsupported_structured_requests_before_transport(
    monkeypatch, schema_name, code
):
    config = configured("gemini35_google_vertex_compact_checker_v3")
    calls = []
    monkeypatch.setattr(
        "generation.adapters.open_provider", lambda *args, **kwargs: calls.append(args)
    )
    with pytest.raises(ValueError, match=code):
        payload(config, MESSAGES, SCHEMA, schema_name)
    result = LLMAdapter(config, api_key=KEY).generate(
        MESSAGES, response_schema=SCHEMA, response_schema_name=schema_name
    )
    assert result.error["code"] == "CONFIGURATION_ERROR"
    assert result.request_submitted is False and calls == []
    assert result.usage["cost"] is None
