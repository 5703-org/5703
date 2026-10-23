"""Existing native provider wire contracts remain unchanged by the Haiku policy."""

import copy
import json

import pytest

from generation.openrouter_routes import prepare_schema_wire
from generation.types import ModelConfig


@pytest.mark.parametrize(
    "provider,model,base",
    [
        ("deepseek", "deepseek-chat", "https://api.deepseek.com"),
        ("google", "synthetic-google", "https://generativelanguage.googleapis.com"),
        ("openai", "synthetic-openai", "https://api.openai.com/v1"),
        ("anthropic", "synthetic-anthropic", "https://api.anthropic.com"),
        ("openai_compatible", "synthetic-compatible", "https://synthetic.example/v1"),
    ],
)
def test_non_gateway_wire_preserves_original_contract(provider, model, base):
    config = ModelConfig(provider=provider, model=model, base_url=base)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["evidence"],
        "properties": {
            "evidence": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string", "minLength": 1},
            }
        },
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Synthetic question."}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "synthetic", "strict": True, "schema": copy.deepcopy(schema)},
        },
    }
    before = json.dumps(body, separators=(",", ":")).encode()
    wire, metadata = prepare_schema_wire(config, body, schema)
    assert wire is body
    assert json.dumps(wire, separators=(",", ":")).encode() == before
    assert metadata == {}
    assert schema["properties"]["evidence"]["maxItems"] == 8
