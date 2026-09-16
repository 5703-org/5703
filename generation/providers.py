"""Explicit provider wire protocols, shared by generation and token accounting."""

from __future__ import annotations

import json
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from .types import ModelConfig, ProviderResult, failure


def provider_schema(value, provider="openai"):
    if isinstance(value, dict):
        # Native schema subsets differ. Canonical response validation still runs locally.
        excluded = {"$schema", "title", "uniqueItems"}
        if provider == "anthropic":
            excluded |= {
                "minimum",
                "maximum",
                "minLength",
                "maxLength",
                "pattern",
                "format",
                "minItems",
                "maxItems",
            }
        if provider == "gemini":
            excluded |= {"minLength", "maxLength", "pattern", "const"}
        transformed = {
            k: provider_schema(v, provider) for k, v in value.items() if k not in excluded
        }
        if provider == "gemini" and "const" in value:
            transformed["enum"] = [value["const"]]
        return transformed
    if isinstance(value, list):
        return [provider_schema(v, provider) for v in value]
    return value


def endpoint(config: ModelConfig, *, count=False):
    defaults = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
        "ollama": "http://localhost:11434/v1",
    }
    base = config.base_url or defaults.get(config.provider, "")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
        or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})
    ):
        raise ValueError(
            "Configure HTTPS or loopback HTTP; keep credentials and API version outside the URL"
        )
    path = parsed.path.rstrip("/")
    if config.provider == "anthropic":
        if not path.endswith("/v1"):
            path += "/v1"
        path += "/messages/count_tokens" if count else "/messages"
    elif config.provider == "gemini":
        if not path.endswith(("/v1", "/v1beta")):
            path += "/v1beta"
        path += (
            "/models/"
            + quote(config.model.removeprefix("models/"), safe="-._")
            + (":countTokens" if count else ":generateContent")
        )
    else:
        if count:
            raise ValueError("This protocol has no configured native token-count endpoint")
        if not path.endswith("/chat/completions"):
            path += "/chat/completions"
    query = (
        urlencode({"api-version": config.api_version})
        if config.provider == "azure_openai" and config.api_version
        else ""
    )
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


def headers(config: ModelConfig, key: str | None):
    result = {"Content-Type": "application/json"}
    if config.provider == "anthropic":
        result["anthropic-version"] = config.api_version or "2023-06-01"
    if key:
        default = {
            "anthropic": "x-api-key",
            "gemini": "x-goog-api-key",
            "azure_openai": "api-key",
        }.get(config.provider, "Authorization")
        name = config.auth_header or default
        result[name] = "Bearer " + key if name == "Authorization" else key
    elif config.provider not in {"local", "ollama", "openai_compatible"}:
        raise ValueError("Configured provider credential is unavailable")
    return result


def payload(config: ModelConfig, messages: list[dict], schema: dict, name: str, *, count=False):
    msgs = [dict(message) for message in messages]
    schema = provider_schema(schema, config.provider)
    if config.structured_output_mode in {"prompt", "json_object"}:
        instruction = (
            "\nOUTPUT FORMAT: Return exactly one complete JSON object, never plain prose or Markdown. Prior assistant messages are displayed conversation text; they are not examples of the required output format. Match this JSON schema: "
            + json.dumps(schema, ensure_ascii=False, sort_keys=True)
        )
        system = next((m for m in msgs if m["role"] == "system"), None)
        if system is None:
            msgs.insert(0, {"role": "system", "content": instruction.strip()})
        else:
            system["content"] += instruction
    if config.provider == "anthropic":
        body = {
            "model": config.model,
            "system": "\n\n".join(m["content"] for m in msgs if m["role"] == "system"),
            "messages": [
                {"role": m["role"], "content": m["content"]} for m in msgs if m["role"] != "system"
            ],
        }
        if config.structured_output_mode != "prompt":
            body["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
        if not count:
            body["max_tokens"] = config.max_tokens
            if config.temperature is not None:
                body["temperature"] = config.temperature
        return body
    if config.provider == "gemini":
        generation = {"maxOutputTokens": config.max_tokens}
        if config.temperature is not None:
            generation["temperature"] = config.temperature
        if config.seed is not None:
            generation["seed"] = config.seed
        if config.structured_output_mode != "prompt":
            generation["responseMimeType"] = "application/json"
            if config.structured_output_mode == "json_schema":
                generation["responseJsonSchema"] = schema
        body = {
            "systemInstruction": {
                "parts": [
                    {"text": "\n\n".join(m["content"] for m in msgs if m["role"] == "system")}
                ]
            },
            "contents": [
                {
                    "role": "model" if m["role"] == "assistant" else "user",
                    "parts": [{"text": m["content"]}],
                }
                for m in msgs
                if m["role"] != "system"
            ],
            "generationConfig": generation,
        }
        if count:
            return {
                "generateContentRequest": {
                    "model": "models/" + config.model.removeprefix("models/"),
                    **body,
                }
            }
        return body
    body = {
        "model": config.model,
        "messages": msgs,
        config.token_limit_parameter: config.max_tokens,
    }
    if config.thinking_enabled is not None:
        body["thinking"] = {"type": "enabled" if config.thinking_enabled else "disabled"}
    for key in ("temperature", "seed", "reasoning_effort"):
        if getattr(config, key) is not None:
            body[key] = getattr(config, key)
    if config.structured_output_mode == "json_schema":
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        }
    elif config.structured_output_mode == "json_object":
        body["response_format"] = {"type": "json_object"}
    return body


def _number(value):
    return value if type(value) is int and value >= 0 else None


def decode_response(decoded, result: ProviderResult, *, count=False):
    if not isinstance(decoded, dict):
        raise ValueError("Provider envelope must be an object")
    provider = result.provider
    if count:
        value = _number(decoded.get("totalTokens" if provider == "gemini" else "input_tokens"))
        if value is None:
            raise ValueError("Missing provider token count")
        result.usage["input_tokens"] = value
        result.finish_reason = "token_count"
        return
    result.model = decoded.get("model", decoded.get("modelVersion", result.model))
    if not isinstance(result.model, str):
        raise ValueError("Invalid provider model identity")
    result.provider_request_id = result.provider_request_id or decoded.get(
        "id", decoded.get("responseId")
    )
    refusal = False
    if provider == "anthropic":
        blocks = decoded.get("content")
        if not isinstance(blocks, list):
            raise ValueError("Missing content blocks")
        content = "".join(
            b["text"]
            for b in blocks
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)
        )
        reason = decoded.get("stop_reason")
        finish = {
            "end_turn": "stop",
            "max_tokens": "length",
            "model_context_window_exceeded": "length",
        }.get(reason, reason)
        refusal = reason == "refusal"
        usage = decoded.get("usage") or {}
        for key in ("input_tokens", "output_tokens"):
            result.usage[key] = _number(usage.get(key))
        # Cache tokens are input too; absent counters are zero only for this documented breakdown.
        for key in ("cache_creation_input_tokens", "cache_read_input_tokens"):
            if key in usage:
                value = _number(usage[key])
                result.usage["input_tokens"] = (
                    result.usage["input_tokens"] + value
                    if result.usage["input_tokens"] is not None and value is not None
                    else None
                )
        if result.usage["input_tokens"] is not None and result.usage["output_tokens"] is not None:
            result.usage["total_tokens"] = (
                result.usage["input_tokens"] + result.usage["output_tokens"]
            )
    elif provider == "gemini":
        candidates = decoded.get("candidates") or []
        if not candidates and (decoded.get("promptFeedback") or {}).get("blockReason"):
            result.error = failure("PROVIDER_REFUSAL", "The provider declined this request")
            return
        choice = candidates[0]
        parts = choice.get("content", {}).get("parts", [])
        content = "".join(
            p["text"]
            for p in parts
            if isinstance(p, dict) and not p.get("thought") and isinstance(p.get("text"), str)
        )
        reason = choice.get("finishReason")
        finish = {"STOP": "stop", "MAX_TOKENS": "length"}.get(reason, reason)
        refusal = reason in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
        usage = decoded.get("usageMetadata") or {}
        for dest, source in (
            ("input_tokens", "promptTokenCount"),
            ("output_tokens", "candidatesTokenCount"),
            ("total_tokens", "totalTokenCount"),
            ("reasoning_tokens", "thoughtsTokenCount"),
        ):
            result.usage[dest] = _number(usage.get(source))
    else:
        choice = decoded["choices"][0]
        content = choice["message"].get("content")
        finish = choice.get("finish_reason")
        refusal = bool(choice["message"].get("refusal")) or finish == "content_filter"
        usage = decoded.get("usage") or {}
        if isinstance(usage, dict):
            for dest, source in (
                ("input_tokens", "prompt_tokens"),
                ("output_tokens", "completion_tokens"),
                ("total_tokens", "total_tokens"),
            ):
                result.usage[dest] = _number(usage.get(source))
            details = usage.get("completion_tokens_details") or {}
            result.usage["reasoning_tokens"] = (
                _number(details.get("reasoning_tokens")) if isinstance(details, dict) else None
            )
    result.finish_reason = finish
    if refusal:
        result.error = failure("PROVIDER_REFUSAL", "The provider declined this request")
    elif finish == "length":
        result.raw_text = content if isinstance(content, str) else ""
        result.error = failure("OUTPUT_TRUNCATED", "Provider output reached its token limit")
    elif not isinstance(content, str):
        result.error = failure("PROVIDER_RESPONSE_ERROR", "Provider message content must be text")
    elif not content.strip():
        result.error = failure(
            "EMPTY_RESPONSE",
            "Provider returned empty content",
            retryable=True,
            content_characters=len(content),
        )
    elif finish not in {"stop", None}:
        result.error = failure("PROVIDER_RESPONSE_ERROR", "Provider did not finish a text response")
    else:
        result.raw_text = content
