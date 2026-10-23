"""Read-only practice prerequisites against synthetic SQLite; no provider transport."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.administration.router import capabilities
from app.modules.learning_product import practice_assessment, practice_capability
from app.modules.model_settings.models import ActiveModelConfiguration
from contracts.http import CapabilitiesOut
from generation.types import ModelConfig
from test_retry_hint_capability209 import (
    no_external_io as no_external_io,
    save_checker,
    scope as scope,
)


def local_checker(**changes):
    return ModelConfig(
        provider="local",
        model="synthetic-practice-checker",
        base_url="http://127.0.0.1:19999/v1",
        **changes,
    )


def test_environment_only_live_checker_does_not_claim_saved_practice_readiness(scope):
    scope.settings.model_mode = "live"
    scope.settings.llm_provider = "local"
    scope.settings.llm_model = "synthetic-environment-checker"
    scope.settings.llm_api_base = "http://127.0.0.1:19999/v1"
    status = practice_capability.practice_assessment_capability(
        scope.db, scope.settings, "workspace"
    )
    assert status["practice_assessment_ready"] is False
    assert "saved" in status["practice_assessment_unavailable_reason"].lower()
    assert not scope.db.new and not scope.db.dirty


def test_answer_only_selection_is_not_practice_ready_and_is_not_mutated(scope):
    save_checker(scope, local_checker())
    pointer = scope.db.get(ActiveModelConfiguration, "workspace")
    pointer.activation_scope = "answer_only"
    pointer.checker_configuration_id = None
    scope.db.commit()
    before = (
        pointer.version,
        pointer.configuration_id,
        pointer.checker_configuration_id,
        pointer.activation_scope,
    )
    status = practice_capability.practice_assessment_capability(
        scope.db, scope.settings, "workspace"
    )
    assert status["practice_assessment_ready"] is False
    assert status["practice_assessment_unavailable_reason"]
    assert before == (
        pointer.version,
        pointer.configuration_id,
        pointer.checker_configuration_id,
        pointer.activation_scope,
    )
    assert not scope.db.new and not scope.db.dirty


@pytest.mark.parametrize(
    "config",
    [
        ModelConfig(),
        local_checker(window_tokens=2048),
        local_checker(tokenizer_provider="provider", token_count_fallback="error"),
        local_checker(
            tokenizer_provider="huggingface",
            tokenizer_local_path=str(Path(__file__).parent / "absent-practice-tokenizer"),
            token_count_fallback="error",
        ),
    ],
)
def test_unusable_local_checker_is_not_practice_ready(scope, config):
    save_checker(scope, config)
    status = practice_capability.practice_assessment_capability(
        scope.db, scope.settings, "workspace"
    )
    assert status["practice_assessment_ready"] is False
    assert status["practice_assessment_unavailable_reason"]
    assert not scope.db.new and not scope.db.dirty


def test_saved_unauthenticated_local_checker_is_ready_with_actual_capped_output(scope):
    # Hint output may reserve 8,192; actual practice reserves at most 4,096.
    # Reuse the exact practice config rather than misusing broader hint readiness.
    save_checker(scope, local_checker(max_tokens=8192, window_tokens=8192))
    config = practice_capability.assessment_model_config(scope.db, scope.settings, "workspace")
    assert config.max_tokens == 4096 and config.configuration_id == "model-settings:checker"
    assert scope.settings.llm_api_key is None
    assert practice_capability.practice_assessment_capability(
        scope.db, scope.settings, "workspace"
    ) == {"practice_assessment_ready": True, "practice_assessment_unavailable_reason": None}
    assert not scope.db.new and not scope.db.dirty


def test_capability_route_exports_actual_practice_status_separately_from_chat(scope):
    save_checker(scope, local_checker())
    result = capabilities(
        flags=SimpleNamespace(as_dict=lambda: {}),
        actor=scope.actor,
        db=scope.db,
        settings=scope.settings,
    )
    status = CapabilitiesOut.model_validate(result["data"])
    assert status.practice_assessment_ready is True
    assert status.practice_assessment_unavailable_reason is None
    assert status.chat_ready is False  # Missing corpus must not disguise checker readiness.
    assert not scope.db.new and not scope.db.dirty


def test_prepare_uses_the_same_saved_checker_resolution_as_capability(scope, monkeypatch):
    selected = []
    config = replace(local_checker(), configuration_id="synthetic-selected-checker")

    def resolve(db, settings, workspace):
        selected.append((db, settings, workspace))
        return config

    monkeypatch.setattr(practice_capability, "assessment_model_config", resolve)
    monkeypatch.setattr(
        practice_assessment.library,
        "validate_locator",
        lambda *args: (_ for _ in ()).throw(AppError("SOURCE_UNAVAILABLE")),
    )
    item = SimpleNamespace(source={})
    with pytest.raises(AppError, match="SOURCE_UNAVAILABLE"):
        practice_assessment.prepare(scope.db, scope.settings, scope.actor, item, None, None, {})
    assert selected == [(scope.db, scope.settings, "workspace")]
