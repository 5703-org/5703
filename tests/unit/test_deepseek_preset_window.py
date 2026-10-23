"""New official-preset working limits without database or provider access."""

from copy import deepcopy
import socket
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine

from app.modules.model_settings.schemas import ModelValues
from app.modules.model_settings.service import as_model_config, presets
from generation.adapters import LLMAdapter
from generation.capabilities import VERSION, defaults
from generation.providers import payload
from generation.types import ModelConfig


@pytest.fixture(autouse=True)
def forbid_database_and_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("OFFLINE_PRESET_DATABASE_OR_TRANSPORT_FORBIDDEN")

    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(LLMAdapter, "_call", forbidden)
    for name in ("create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, forbidden)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, forbidden)


def test_known_deepseek_draft_materializes_complete_unchanged_wire_contract():
    selected = next(row for row in presets() if row["id"] == "deepseek")
    public = ModelValues.model_validate(selected["config"]).model_dump()
    public["capability_version"] = VERSION
    public["capabilities"] = defaults(public["provider"], public["model"], public["base_url"])
    config = ModelConfig.from_dict(public)
    config.validate()
    body = payload(config, [{"role": "user", "content": "Authored preset fixture."}], {}, "fixture")
    assert config.window_tokens == 32768 and config.max_tokens == 1024
    assert config.tokenizer_provider == "estimate" and config.token_count_fallback == "estimate"
    assert body["model"] == "deepseek-flash"
    assert body["max_tokens"] == 1024 and body["thinking"] == {"type": "disabled"}
    assert body["response_format"] == {"type": "json_object"}
    assert (
        config.provider == "openai_compatible" and config.base_url == "https://api.deepseek.com/v1"
    )
    assert "application working window" in selected["description"]
    assert "Saved revisions retain their existing limits" in selected["description"]


@pytest.mark.parametrize("window_tokens", [16384, 32768])
def test_existing_saved_deepseek_window_is_resolved_without_preset_migration(window_tokens):
    saved = {
        "provider": "openai_compatible",
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com/v1",
        "window_tokens": window_tokens,
        "max_tokens": 1024,
        "structured_output_mode": "json_object",
        "thinking_enabled": False,
    }
    before = deepcopy(saved)
    config = as_model_config(SimpleNamespace(id="authored-saved-revision", public_config=saved))
    config.validate()
    assert saved == before
    assert config.window_tokens == window_tokens
    assert config.configuration_id == "model-settings:authored-saved-revision"


def test_unknown_compatible_model_and_generic_defaults_remain_16384():
    values = ModelValues(
        provider="openai_compatible",
        model="authored-unknown-model",
        base_url="https://provider.example.invalid/v1",
    )
    config = ModelConfig.from_dict(values.model_dump())
    config.validate()
    assert config.window_tokens == ModelConfig().window_tokens == 16384
    assert (
        next(row for row in presets() if row["id"] == "custom")["config"]["window_tokens"] == 16384
    )


def test_preset_selection_cannot_mutate_another_draft_or_saved_limit():
    first = next(row for row in presets() if row["id"] == "deepseek")
    first["config"]["window_tokens"] = 16384
    second = next(row for row in presets() if row["id"] == "deepseek")
    assert second["config"]["window_tokens"] == 32768
    assert (
        next(row for row in presets() if row["id"] == "openai_luna")["config"]["window_tokens"]
        == 65536
    )
