"""Save/test/activate are separate operations; requests resolve immutable IDs."""

from __future__ import annotations

import hashlib
import json
import math
import time
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.db.base import new_uuid
from generation.types import ModelConfig
from .models import (
    ActiveModelConfiguration,
    ModelActivation,
    ModelConfiguration,
    ModelConnectionTest,
    ModelCredential,
)
from .schemas import ConfigurationSave
from .secrets import decrypt, encrypt, encryption_ready

PREFIX = "model-settings:"
DIAGNOSTICS = {
    "OK": "The saved configuration completed the connection probe.",
    "MOCK_OK": "The explicit mock configuration passed its local check; no live provider was tested.",
    "PROVIDER_AUTH_ERROR": "Provider authentication failed. Check the saved API key and account access.",
    "PROVIDER_AUTHENTICATION_ERROR": "Provider authentication failed. Check the saved API key and account access.",
    "PROVIDER_RATE_LIMITED": "The provider rejected the request because of a rate or quota limit.",
    "PROVIDER_TIMEOUT": "The provider did not complete within the configured timeout.",
    "PROVIDER_CONNECTION_ERROR": "The provider could not be reached. Check the base URL and network.",
    "PROVIDER_NETWORK_ERROR": "The provider could not be reached. Check the base URL and network.",
    "PROVIDER_PROBE_INVALID": "The provider responded, but did not satisfy the required JSON probe contract.",
    "PROVIDER_RESPONSE_ERROR": "The provider response did not match the selected protocol.",
    "PROVIDER_HTTP_ERROR": "The provider rejected the request. Check the protocol, model, endpoint and account access.",
    "PROVIDER_NOT_FOUND": "The provider did not find the configured model or endpoint. Check the base URL and model identity.",
    "PROVIDER_SERVER_ERROR": "The provider reported a server failure. Retry the explicit test later.",
    "MODEL_UNAVAILABLE": "The saved configuration or its deployment encryption key is unavailable.",
    "CONFIGURATION_ERROR": "The saved provider configuration is not supported by this runtime.",
    "CREDENTIAL_REQUIRED": "This provider requires a saved API key before testing.",
    "PROBE_FAILED": "The connection probe failed. Check the configured provider and deployment diagnostics.",
}


def presets():
    definitions = [
        ("openai", "OpenAI", "openai", "https://api.openai.com/v1", True, "json_schema", None),
        ("azure_openai", "Azure OpenAI", "azure_openai", "", True, "json_schema", "api-key"),
        (
            "anthropic",
            "Anthropic",
            "anthropic",
            "https://api.anthropic.com/v1",
            True,
            "prompt",
            "x-api-key",
        ),
        (
            "gemini",
            "Google Gemini",
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta",
            True,
            "json_schema",
            "x-goog-api-key",
        ),
        ("ollama", "Ollama", "ollama", "http://127.0.0.1:11434/v1", False, "json_schema", None),
        (
            "deepseek",
            "DeepSeek compatible endpoint",
            "openai_compatible",
            "https://api.deepseek.com/v1",
            True,
            "json_object",
            None,
        ),
        (
            "custom",
            "Custom compatible endpoint",
            "openai_compatible",
            "",
            False,
            "json_schema",
            None,
        ),
        ("mock", "Explicit authored mock", "mock", None, False, "json_schema", None),
    ]
    return [
        {
            "id": id,
            "name": name,
            "description": "Choose an available model and verify the selected protocol. A preset is not a guarantee of model/account compatibility."
            if provider != "mock"
            else "Deterministic authored local behavior; not a learned model or a live connectivity test.",
            "requires_api_key": required,
            "config": {
                "provider": provider,
                "model": "authored-extractive-v1"
                if provider == "mock"
                else "deepseek-flash"
                if id == "deepseek"
                else "",
                "base_url": base,
                "window_tokens": 16384,
                "max_tokens": 1024,
                "timeout_seconds": 60,
                "temperature": 0,
                "structured_output_mode": mode,
                "auth_header": header,
                "api_version": "2023-06-01" if provider == "anthropic" else None,
                "tokenizer_provider": "estimate",
                "token_count_fallback": "estimate",
                "thinking_enabled": False if id == "deepseek" else None,
            },
        }
        for id, name, provider, base, required, mode, header in definitions
    ]


def owned(db, configuration_id, actor, *, lock=False):
    query = select(ModelConfiguration).where(
        ModelConfiguration.id == configuration_id,
        ModelConfiguration.workspace_id == actor.workspace_id,
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = db.scalar(query)
    if row is None:
        raise AppError("NOT_FOUND")
    return row


def as_model_config(row):
    return ModelConfig.from_dict({**row.public_config, "configuration_id": PREFIX + row.id})


def resolve_active_model_config(db, settings, workspace_id):
    pointer = db.get(ActiveModelConfiguration, workspace_id)
    if pointer is None or pointer.configuration_id is None:
        return None
    row = db.get(ModelConfiguration, pointer.configuration_id)
    if row is None or row.workspace_id != workspace_id:
        raise AppError("MODEL_UNAVAILABLE", detail="The active model configuration is unavailable.")
    config = as_model_config(row)
    config.validate()
    return config


def resolve_secret(db, settings, configuration_id):
    if not configuration_id.startswith(PREFIX):
        return settings.llm_api_key
    row = db.get(ModelConfiguration, configuration_id[len(PREFIX) :])
    if row is None:
        raise AppError("MODEL_UNAVAILABLE", detail="The frozen model configuration is unavailable.")
    if row.credential_id is None:
        return None
    secret = db.get(ModelCredential, row.credential_id)
    if secret is None or secret.workspace_id != row.workspace_id:
        raise AppError("MODEL_UNAVAILABLE", detail="The frozen model credential is unavailable.")
    return decrypt(settings, secret.ciphertext)


def test_out(row, config):
    return {
        "id": row.id,
        "configuration_id": row.configuration_id,
        "status": row.status,
        "model_mode": "mock" if config.public_config["provider"] == "mock" else "live",
        "diagnostic_code": row.diagnostic_code,
        "message": row.message,
        "latency_ms": row.latency_ms,
        "usage": row.usage,
        "created_at": row.created_at,
    }


def output(db, row, active_id=None):
    latest = db.scalar(
        select(ModelConnectionTest)
        .where(ModelConnectionTest.configuration_id == row.id)
        .order_by(ModelConnectionTest.created_at.desc(), ModelConnectionTest.id.desc())
    )
    return {
        "id": row.id,
        "group_id": row.group_id,
        "revision": row.revision,
        "name": row.name,
        "preset": row.preset,
        "config": row.public_config,
        "config_hash": row.config_hash,
        "has_api_key": row.credential_id is not None,
        "api_key_masked": "********" if row.credential_id else None,
        "created_at": row.created_at,
        "latest_test": test_out(latest, row) if latest else None,
        "active": row.id == active_id,
    }


def state(db, settings, actor):
    active = db.get(ActiveModelConfiguration, actor.workspace_id)
    active_id = active.configuration_id if active else None
    rows = db.scalars(
        select(ModelConfiguration)
        .where(ModelConfiguration.workspace_id == actor.workspace_id)
        .order_by(ModelConfiguration.created_at.desc(), ModelConfiguration.id)
    ).all()
    return {
        "items": [output(db, row, active_id) for row in rows],
        "active_configuration_id": active_id,
        "active_version": active.version if active else 0,
        "source": "database" if active_id else "environment",
        "encryption_ready": encryption_ready(settings),
    }


def save(db, settings, actor, body: ConfigurationSave, previous_id=None):
    previous = owned(db, previous_id, actor, lock=True) if previous_id else None
    if previous:
        successor = db.scalar(
            select(ModelConfiguration.id).where(
                ModelConfiguration.group_id == previous.group_id,
                ModelConfiguration.revision > previous.revision,
            )
        )
        if successor:
            raise AppError(
                "CONFLICT", detail="A newer saved version already exists. Reload before editing."
            )
    values = body.config.model_dump()
    if previous and previous.credential_id and not body.clear_api_key and body.api_key is None:

        def destination(config):
            url = urlsplit(config.get("base_url") or "")
            return config["provider"], url.scheme, url.hostname, url.port

        if destination(previous.public_config) != destination(values):
            raise AppError(
                "VALIDATION_FAILED",
                detail="Replace or explicitly clear the API key when changing provider or destination origin.",
            )
    try:
        ModelConfig.from_dict(values).validate()
    except (TypeError, ValueError):
        raise AppError(
            "VALIDATION_FAILED",
            detail="The selected model configuration is unsupported or invalid.",
        ) from None
    credential_id = previous.credential_id if previous and not body.clear_api_key else None
    if body.api_key is not None:
        credential = ModelCredential(
            workspace_id=actor.workspace_id,
            ciphertext=encrypt(settings, body.api_key.get_secret_value()),
        )
        db.add(credential)
        db.flush()
        credential_id = credential.id
    identity = new_uuid()
    row = ModelConfiguration(
        id=identity,
        workspace_id=actor.workspace_id,
        group_id=previous.group_id if previous else identity,
        revision=previous.revision + 1 if previous else 1,
        previous_id=previous.id if previous else None,
        name=body.name.strip(),
        preset=body.preset,
        public_config=values,
        config_hash=hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        credential_id=credential_id,
        created_by=actor.id,
    )
    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            "CONFLICT",
            detail="A concurrent configuration version was saved. Reload before editing.",
        ) from None
    active = db.get(ActiveModelConfiguration, actor.workspace_id)
    return output(db, row, active.configuration_id if active else None)


def _safe_usage(value):
    if not isinstance(value, dict):
        return {}
    return {
        key: number
        for key in ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens", "cost")
        if (number := value.get(key)) is None
        or type(number) in (int, float)
        and math.isfinite(number)
        and number >= 0
    }


def run_test(db, settings, actor, configuration_id):
    row = owned(db, configuration_id, actor)
    config = as_model_config(row)
    # Release the read transaction before a bounded network call. The immutable
    # record and credential reference remain pinned throughout this probe.
    secret = None
    started = time.monotonic()
    code, usage = "PROBE_FAILED", {}
    try:
        secret = resolve_secret(db, settings, config.configuration_id)
        db.commit()
        if config.provider in {"openai", "azure_openai", "anthropic", "gemini"} and not secret:
            code = "CREDENTIAL_REQUIRED"
        else:
            from generation.adapters import test_connection

            result = test_connection(config, api_key=secret)
            usage = _safe_usage(result.usage)
            if result.error:
                supplied = result.error.get("code")
                code = supplied if supplied in DIAGNOSTICS else "PROBE_FAILED"
                status = result.error.get("details", {}).get("http_status")
                if type(status) is int and supplied == "PROVIDER_HTTP_ERROR":
                    if status in {401, 403}:
                        code = "PROVIDER_AUTH_ERROR"
                    elif status == 429:
                        code = "PROVIDER_RATE_LIMITED"
                    elif status == 404:
                        code = "PROVIDER_NOT_FOUND"
                    elif 500 <= status <= 599:
                        code = "PROVIDER_SERVER_ERROR"
            elif result.raw_text == '{"ok":true}':
                code = "MOCK_OK" if config.provider == "mock" else "OK"
            else:
                code = "PROVIDER_PROBE_INVALID"
    except AppError as error:
        code = error.code if error.code in DIAGNOSTICS else "PROBE_FAILED"
    except Exception:
        # Exception messages, response bodies and request headers may contain
        # credentials. Store only our finite diagnostic catalog.
        code = "PROBE_FAILED"
    finally:
        secret = None
    test = ModelConnectionTest(
        configuration_id=row.id,
        status="passed" if code in {"OK", "MOCK_OK"} else "failed",
        diagnostic_code=code,
        message=DIAGNOSTICS[code],
        latency_ms=int((time.monotonic() - started) * 1000),
        usage=usage,
        tested_by=actor.id,
    )
    owned(db, configuration_id, actor, lock=True)
    db.add(test)
    db.commit()
    return test_out(test, row)


def _active_locked(db, workspace_id):
    pointer = db.scalar(
        select(ActiveModelConfiguration)
        .where(ActiveModelConfiguration.workspace_id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if pointer is None:
        try:
            with db.begin_nested():
                db.add(ActiveModelConfiguration(workspace_id=workspace_id, version=0))
                db.flush()
        except IntegrityError:
            pass
        pointer = db.scalar(
            select(ActiveModelConfiguration)
            .where(ActiveModelConfiguration.workspace_id == workspace_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    return pointer


def activate(db, settings, actor, configuration_id, test_id, expected_active_version):
    row = owned(db, configuration_id, actor, lock=True) if configuration_id else None
    if row:
        result = db.get(ModelConnectionTest, test_id)
        latest = db.scalar(
            select(ModelConnectionTest)
            .where(ModelConnectionTest.configuration_id == row.id)
            .order_by(ModelConnectionTest.created_at.desc(), ModelConnectionTest.id.desc())
        )
        if (
            result is None
            or result.configuration_id != row.id
            or result.status != "passed"
            or latest is None
            or latest.id != result.id
        ):
            raise AppError(
                "CONFLICT",
                detail="Activation requires the latest passing test for this exact saved version.",
            )
        resolve_secret(db, settings, PREFIX + row.id)
    pointer = _active_locked(db, actor.workspace_id)
    if pointer.version != expected_active_version:
        raise AppError("CONFLICT", detail="The active model changed. Reload before activating.")
    db.add(
        ModelActivation(
            workspace_id=actor.workspace_id,
            previous_id=pointer.configuration_id,
            configuration_id=row.id if row else None,
            test_id=test_id if row else None,
            active_version=pointer.version + 1,
            activated_by=actor.id,
        )
    )
    pointer.configuration_id = row.id if row else None
    pointer.version += 1
    db.commit()
    return state(db, settings, actor)
