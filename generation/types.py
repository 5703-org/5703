"""Transport-neutral configuration and serializable execution accounting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    provider: str = "mock"
    model: str = "authored-extractive-v1"
    base_url: str | None = None
    api_key_env: str | None = None
    window_tokens: int = 16384
    max_tokens: int = 1024
    timeout_seconds: float = 60.0
    temperature: float | None = 0.0
    seed: int | None = None
    token_limit_parameter: str = "max_tokens"
    structured_output_mode: str = "json_schema"
    reasoning_effort: str | None = None
    configuration_id: str = "mock-default-v1"
    api_version: str | None = None
    auth_header: str | None = None
    tokenizer_provider: str = "auto"
    tokenizer_name: str | None = None
    tokenizer_revision: str | None = None
    tokenizer_local_path: str | None = None
    token_count_fallback: str = "estimate"
    thinking_enabled: bool | None = None

    @classmethod
    def from_dict(cls, value: dict | None):
        return cls(**(value or {}))

    def to_dict(self):
        return asdict(self)

    def validate(self):
        if self.thinking_enabled is not None and type(self.thinking_enabled) is not bool:
            raise ValueError("Thinking mode must be a boolean or null")
        if not isinstance(self.provider, str) or not isinstance(self.model, str):
            raise ValueError("Provider and model identities must be strings")
        if any(type(value) is not int for value in (self.window_tokens, self.max_tokens)):
            raise ValueError("Model token limits must be integers")
        if type(self.timeout_seconds) not in (int, float) or not math.isfinite(
            self.timeout_seconds
        ):
            raise ValueError("Provider timeout must be finite")
        if self.temperature is not None and (
            type(self.temperature) not in (int, float) or not math.isfinite(self.temperature)
        ):
            raise ValueError("Temperature must be a finite number or null")
        if any(
            value is not None and not isinstance(value, str)
            for value in (self.base_url, self.api_key_env)
        ):
            raise ValueError("Endpoint and credential environment name must be strings or null")
        if self.provider not in {
            "mock",
            "openai_compatible",
            "openai",
            "local",
            "ollama",
            "azure_openai",
            "anthropic",
            "gemini",
        }:
            raise ValueError("Unsupported provider; configure a compatible transport explicitly")
        if not self.model.strip() or self.window_tokens <= 0 or self.max_tokens <= 0:
            raise ValueError("Model identity and positive token limits are required")
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("Call timeout must be greater than zero and at most 60 seconds")
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be in [0, 2]")
        if self.token_limit_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("Token limit field must be explicitly configured")
        if self.structured_output_mode not in {"json_schema", "json_object", "prompt"}:
            raise ValueError("Unsupported structured output mode")
        if self.auth_header not in {
            None,
            "Authorization",
            "api-key",
            "x-api-key",
            "x-goog-api-key",
        }:
            raise ValueError("Unsupported credential header")
        if self.tokenizer_provider not in {
            "auto",
            "tiktoken",
            "huggingface",
            "estimate",
            "provider",
        }:
            raise ValueError("Unsupported token counter")
        if self.token_count_fallback not in {"estimate", "error"}:
            raise ValueError("Unsupported token counter fallback")
        for value in (
            self.api_version,
            self.tokenizer_name,
            self.tokenizer_revision,
            self.tokenizer_local_path,
        ):
            if value is not None and (
                not isinstance(value, str) or not value.strip() or len(value) > 512
            ):
                raise ValueError("Token counter and API version fields must be bounded strings")


@dataclass
class RequestBudget:
    consumed_calls: int = 0
    active_seconds: float = 0.0
    format_repairs: int = 0
    transient_retries: int = 0
    max_calls: int = 4
    max_active_seconds: float = 180.0

    def __post_init__(self):
        if any(
            type(value) is not int
            for value in (
                self.consumed_calls,
                self.format_repairs,
                self.transient_retries,
                self.max_calls,
            )
        ):
            raise ValueError("Request counters must be integers")
        if any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in (self.active_seconds, self.max_active_seconds)
        ):
            raise ValueError("Active execution accounting must be finite")
        if not 1 <= self.max_calls <= 4 or not 0 < self.max_active_seconds <= 180:
            raise ValueError("Request budgets cannot exceed four calls or 180 active seconds")
        if (
            min(
                self.consumed_calls,
                self.active_seconds,
                self.format_repairs,
                self.transient_retries,
            )
            < 0
        ):
            raise ValueError("Consumed budgets must be nonnegative")

    @classmethod
    def from_dict(cls, value: dict | None):
        return cls(**(value or {}))

    def to_dict(self):
        return asdict(self)

    @property
    def remaining_seconds(self):
        return max(0.0, self.max_active_seconds - self.active_seconds)

    def reserve(self):
        if self.consumed_calls >= self.max_calls or self.remaining_seconds <= 0:
            raise ValueError("BUDGET_EXHAUSTED")
        self.consumed_calls += 1


@dataclass
class GenerationRequest:
    request_id: str
    mode: str
    condition: str
    question: str
    question_id: str = ""
    options: dict[str, str] | None = None
    evidence: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    summary: str | None = None
    profile: dict | None = None
    prepared_query: dict | None = None
    config: ModelConfig = field(default_factory=ModelConfig)


@dataclass
class ProviderResult:
    raw_text: str = ""
    provider: str = "mock"
    model: str = "authored-extractive-v1"
    finish_reason: str | None = None
    provider_request_id: str | None = None
    usage: dict = field(
        default_factory=lambda: {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
            "cost": None,
        }
    )
    latency_ms: int = 0
    error: dict | None = None
    request_submitted: bool | None = None


@dataclass
class GenerationOutcome:
    response: dict | None = None
    error: dict | None = None
    messages: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    timing: dict = field(default_factory=dict)
    provider: str = "mock"
    model: str = "authored-extractive-v1"
    model_mode: str = "mock"
    budget: dict = field(default_factory=dict)
    attempts: list[dict] = field(default_factory=list)
    token_budget: dict = field(default_factory=dict)
    response_origin: str = "model"

    @property
    def succeeded(self):
        return self.response is not None and self.error is None

    def to_dict(self):
        return asdict(self)


def failure(code: str, message: str, *, retryable=False, **details: Any):
    return {"code": code, "message": message, "retryable": retryable, "details": details}
