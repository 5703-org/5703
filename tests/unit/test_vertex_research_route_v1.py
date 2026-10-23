"""Offline research-route regressions; no real credentials, DNS or provider calls."""

from dataclasses import replace
from unittest.mock import patch

import pytest

from generation.adapters import LLMAdapter
from generation.openrouter_routes import CURRENT_PROFILE_IDS, preferences, resolve
from generation.providers import endpoint, payload, prepare_checker_transport
from generation.types import ModelConfig

PROFILE = "gemini35_google_vertex_high_research_v1"
SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
MESSAGES = [{"role": "user", "content": "Authored offline route fixture."}]


def config():
    return ModelConfig(
        provider="openai_compatible",
        model="google/gemini-3.5-flash-lite",
        base_url="https://openrouter.ai/api/v1",
        temperature=None,
        max_tokens=16384,
        window_tokens=131072,
        openrouter_route_profile=PROFILE,
    )


@pytest.fixture(autouse=True)
def no_credentials_or_sockets(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Offline preflight must not read credentials or open a socket")

    monkeypatch.setattr(LLMAdapter, "_key", forbidden)
    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("socket.getaddrinfo", forbidden)


def test_same_vertex_high_route_is_explicit_and_not_a_current_default():
    value = config()
    value.validate()
    route = resolve(value)
    assert route.reasoning_effort == "high"
    assert route.model == "google/gemini-3.5-flash-lite"
    assert route.provider_slug == "google-vertex/global"
    assert route.checker_transport is None
    assert route.schema_transport is None
    assert PROFILE not in CURRENT_PROFILE_IDS
    assert endpoint(value) == "https://openrouter.ai/api/v1/chat/completions"
    assert preferences(value) == {
        "order": ["google-vertex/global"],
        "only": ["google-vertex/global"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "max_price": {"prompt": 0.3, "completion": 2.5},
    }
    assert prepare_checker_transport(value, MESSAGES, SCHEMA, "offline_atomic") is None
    body = payload(value, MESSAGES, SCHEMA, "offline_atomic")
    assert body["reasoning"] == {"effort": "high"}
    assert body["messages"] == MESSAGES
    assert body["max_tokens"] == 16384
    assert body["response_format"]["json_schema"]["schema"] == SCHEMA


@pytest.mark.parametrize(
    "change",
    [
        {"reasoning_effort": "low"},
        {"thinking_enabled": False},
        {"model": "google/another-model"},
        {"temperature": 0},
        {"base_url": "https://another.example.invalid/v1"},
    ],
)
def test_route_drift_is_rejected_before_credentials(change):
    result = LLMAdapter(replace(config(), **change)).generate(
        MESSAGES, response_schema=SCHEMA, response_schema_name="offline_atomic"
    )
    assert result.request_submitted is False
    assert result.error["code"] == "CONFIGURATION_ERROR"


def test_valid_route_reaches_credential_boundary_only_with_explicit_local_sentinel():
    # The sentinel throws locally before transport. It is not a provider result.
    class CredentialBoundary(Exception):
        pass

    with patch.object(LLMAdapter, "_key", side_effect=CredentialBoundary):
        with pytest.raises(CredentialBoundary):
            LLMAdapter(config()).generate(
                MESSAGES, response_schema=SCHEMA, response_schema_name="offline_atomic"
            )
