"""No provider traffic or usable credentials: formal runtime policy boundaries."""

from types import SimpleNamespace as NS
import pytest
from app.core.exceptions import AppError
from app.modules.model_settings import service, compatibility


@pytest.mark.parametrize(
    "env,mode,allowed",
    [
        ("test", "mock", True),
        ("dev", "mock", True),
        ("demo", "mock", True),
        ("test", "live", False),
        ("production", "live", False),
        ("production", "mock", False),
    ],
)
def test_simulation_policy(env, mode, allowed):
    settings = NS(env=env, model_mode=mode)
    assert service.simulation_allowed(settings) is allowed
    service.require_runtime_provider(settings, "openai_compatible")
    if allowed:
        service.require_runtime_provider(settings, "mock")
    else:
        with pytest.raises(AppError, match="Simulated models are disabled"):
            service.require_runtime_provider(settings, "mock")


def test_save_rejects_simulation_before_database_or_secret_access():
    with pytest.raises(AppError, match="Simulated models are disabled"):
        service.save(
            None, NS(env="production", model_mode="live"), None, NS(config=NS(provider="mock"))
        )


def test_legacy_probe_rejects_simulation_before_secret_or_commit(monkeypatch):
    monkeypatch.setattr(service, "owned", lambda *a, **k: NS(public_config={}))
    monkeypatch.setattr(service, "as_model_config", lambda *a: NS(provider="mock"))
    with pytest.raises(AppError, match="Simulated models are disabled"):
        service.run_legacy_test(None, NS(env="production", model_mode="live"), None, "historical")


def test_activation_rejects_simulation_before_probe_validation_or_mutation(monkeypatch):
    monkeypatch.setattr(service, "owned", lambda *a, **k: NS(public_config={"provider": "mock"}))
    with pytest.raises(AppError, match="Simulated models are disabled"):
        service.activate(None, NS(env="test", model_mode="live"), None, "historical", "old-test", 0)


def test_new_probe_rejects_simulation_before_run_creation(monkeypatch):
    monkeypatch.setattr(service, "owned", lambda *a, **k: NS(public_config={}))
    monkeypatch.setattr(service, "as_model_config", lambda *a: NS(provider="mock"))
    monkeypatch.setattr(compatibility, "latest", lambda *a: None)
    with pytest.raises(AppError, match="Simulated models are disabled"):
        compatibility.run_suite(
            NS(scalar=lambda *a: None), NS(env="test", model_mode="live"), None, "historical"
        )
