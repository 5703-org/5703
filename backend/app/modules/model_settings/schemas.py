"""Public configuration DTOs: credentials are write-only and never serialised back."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from contracts.models import Contract


class ModelValues(Contract):
    provider: Literal[
        "mock",
        "openai",
        "openai_compatible",
        "local",
        "ollama",
        "azure_openai",
        "anthropic",
        "gemini",
    ]
    model: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, max_length=2048)
    window_tokens: int = Field(default=16384, ge=2048, le=2000000)
    max_tokens: int = Field(default=1024, ge=1, le=1024)
    timeout_seconds: float = Field(default=60, gt=0, le=60, allow_inf_nan=False)
    temperature: float | None = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    seed: int | None = None
    token_limit_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    structured_output_mode: Literal["json_schema", "json_object", "prompt"] = "json_schema"
    reasoning_effort: str | None = Field(default=None, max_length=30)
    thinking_enabled: bool | None = None
    api_version: str | None = Field(default=None, max_length=50)
    auth_header: Literal["Authorization", "api-key", "x-api-key", "x-goog-api-key"] | None = None
    tokenizer_provider: Literal["auto", "tiktoken", "huggingface", "estimate", "provider"] = (
        "estimate"
    )
    tokenizer_name: str | None = Field(default=None, max_length=200)
    tokenizer_revision: str | None = Field(default=None, max_length=100)
    tokenizer_local_path: str | None = Field(default=None, max_length=1024)
    token_count_fallback: Literal["estimate", "error"] = "estimate"

    @field_validator("model")
    @classmethod
    def model_identity(cls, value):
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("A nonblank model identity without control characters is required.")
        return value.strip()

    @field_validator("base_url")
    @classmethod
    def safe_base_url(cls, value):
        if value is None:
            return value
        try:
            url = urlsplit(value)
            valid_port = url.port
        except ValueError:
            raise ValueError("Use an HTTP(S) base URL with a valid host and port.") from None
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or any(char.isspace() for char in value)
        ):
            raise ValueError("Base URL must be HTTP(S), without credentials, query or fragment.")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_protocol(self):
        if self.provider != "mock" and not self.base_url:
            raise ValueError("A base URL is required for a non-mock provider.")
        if self.max_tokens >= self.window_tokens:
            raise ValueError("Output tokens must be smaller than the model context window.")
        return self


class ConfigurationSave(Contract):
    name: str = Field(min_length=1, max_length=120)
    preset: str = Field(default="custom", min_length=1, max_length=60)
    config: ModelValues
    api_key: SecretStr | None = Field(default=None, max_length=8192)
    clear_api_key: bool = False

    @model_validator(mode="after")
    def key_action(self):
        if not self.name.strip():
            raise ValueError("A configuration name is required.")
        if self.api_key is not None:
            secret = self.api_key.get_secret_value()
            if not secret.strip() or any(ord(char) < 32 for char in secret):
                raise ValueError("API key must be nonblank and contain no control characters.")
            if self.clear_api_key:
                raise ValueError("Replace and clear cannot be requested together.")
        return self


class ConnectionTestOut(Contract):
    id: str
    configuration_id: str
    status: Literal["passed", "failed"]
    model_mode: Literal["mock", "live"]
    diagnostic_code: str
    message: str
    latency_ms: int
    usage: dict
    created_at: datetime


class ModelConfigurationOut(Contract):
    id: str
    group_id: str
    revision: int
    name: str
    preset: str
    config: ModelValues
    config_hash: str
    has_api_key: bool
    api_key_masked: str | None
    created_at: datetime
    latest_test: ConnectionTestOut | None
    active: bool


class ModelSettingsState(Contract):
    items: list[ModelConfigurationOut]
    active_configuration_id: str | None
    active_version: int
    source: Literal["database", "environment"]
    encryption_ready: bool


class ActivationInput(Contract):
    test_id: str
    expected_active_version: int = Field(ge=0)


class EnvironmentInput(Contract):
    expected_active_version: int = Field(ge=0)


class ProviderPreset(Contract):
    id: str
    name: str
    description: str
    requires_api_key: bool
    config: dict
