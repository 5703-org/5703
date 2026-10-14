"""Durable single-owner compatibility suites; no hidden retries or raw content."""

from datetime import timezone
import time
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.db.base import new_uuid, utcnow
from generation import probes
from generation.provider_diagnostics import safe_usage
from .models import ModelCompatibilityRun, ModelCompatibilityStage
from .schemas import CompatibilityInput

MESSAGES = {
    "OK": "The requested live compatibility stages passed; this is not an accuracy evaluation.",
    "MOCK_OK": "The authored mock protocol checks passed. No real provider or semantic checker was tested.",
    "PROBE_RUNNING": "The compatibility suite is running; do not repeat an uncertain submission.",
    "PROBE_UNCERTAIN": "A started compatibility request has no confirmed terminal receipt. It will not be replayed automatically.",
    "CONFIGURATION_ERROR": "The frozen protocol options or input/output reservation failed local validation.",
    "CREDENTIAL_REQUIRED": "This protocol requires a saved credential.",
    "PROBE_FAILED": "A compatibility stage failed. Inspect its safe diagnostic and usage below.",
}


def latest(db, configuration_id, role=None):
    query = select(ModelCompatibilityRun).where(
        ModelCompatibilityRun.configuration_id == configuration_id
    )
    if role:
        query = query.where(ModelCompatibilityRun.role == role)
    return db.scalar(
        query.order_by(ModelCompatibilityRun.created_at.desc(), ModelCompatibilityRun.id.desc())
    )


def output(db, run, config):
    stages = db.scalars(
        select(ModelCompatibilityStage)
        .where(ModelCompatibilityStage.run_id == run.id)
        .order_by(ModelCompatibilityStage.started_at, ModelCompatibilityStage.id)
    ).all()
    status = run.status
    age = (utcnow() - run.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    if status == "running" and age > 195:
        status = "uncertain"
    code = "PROBE_UNCERTAIN" if status == "uncertain" else run.diagnostic_code
    usages = [
        stage.result_json.get("usage", {})
        for stage in stages
        if stage.status not in {"not_run", "started"}
    ]
    names = {key for item in usages for key in item}
    usage = {
        key: sum(item[key] for item in usages)
        if usages and all(type(item.get(key)) in (int, float) for item in usages)
        else None
        for key in names
    }
    return {
        "id": run.id,
        "configuration_id": run.configuration_id,
        "status": status,
        "model_mode": "mock" if config.public_config["provider"] == "mock" else "live",
        "diagnostic_code": code,
        "message": MESSAGES.get(code, MESSAGES["PROBE_FAILED"]),
        "latency_ms": sum(stage.result_json.get("latency_ms", 0) for stage in stages),
        "usage": usage,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "test_version": run.test_version,
        "role": run.role,
        "tier": run.tier,
        "network_label": run.network_label,
        "activation_eligible": (
            _project_pass_error(db, config, run, run.role, stages=stages) is None
        ),
        "project_passed": status == "passed"
        and any(stage.tier == "project" and stage.status == "passed" for stage in stages),
        "budget": {
            "max_calls": 3 if run.tier == "all" else 1,
            "max_active_seconds": 180,
            "reserved_attempts": sum(
                stage.status not in {"not_run"}
                and stage.metadata_json.get("transport_reserved", False)
                for stage in stages
            ),
            "automatic_retries": 0,
        },
        "stages": [
            {
                "id": stage.id,
                "tier": stage.tier,
                "status": stage.status,
                "started_at": stage.started_at,
                "completed_at": stage.completed_at,
                "metadata": stage.metadata_json,
                **stage.result_json,
            }
            for stage in stages
        ],
    }


def run_suite(db, settings, actor, configuration_id, body=None, idempotency_key=None):
    from .service import owned, as_model_config, resolve_secret

    body = body or CompatibilityInput()
    config_row = owned(db, configuration_id, actor, lock=True)
    key = idempotency_key or new_uuid()
    if not 1 <= len(key) <= 128 or not key.isascii() or any(ord(c) < 33 for c in key):
        raise AppError("VALIDATION_FAILED", detail="Use a bounded ASCII idempotency key.")
    body_hash = probes.digest(body.model_dump())
    existing = db.scalar(
        select(ModelCompatibilityRun).where(
            ModelCompatibilityRun.configuration_id == configuration_id,
            ModelCompatibilityRun.idempotency_key == key,
        )
    )
    if existing:
        if existing.input_hash != body_hash:
            raise AppError(
                "CONFLICT", detail="This test key already identifies different probe options."
            )
        return output(db, existing, config_row)
    current = latest(db, configuration_id)
    if current and output(db, current, config_row)["status"] == "running":
        raise AppError(
            "CONFLICT",
            detail="A compatibility suite is already running for this saved configuration.",
        )
    config = as_model_config(config_row)
    run = ModelCompatibilityRun(
        configuration_id=configuration_id,
        tested_by=actor.id,
        idempotency_key=key,
        input_hash=body_hash,
        role=body.role,
        tier=body.tier,
        network_label=body.network_label,
        config_hash=config_row.config_hash,
        test_version=probes.VERSION,
    )
    db.add(run)
    try:
        db.commit()  # Durable suite receipt before any transport.
    except IntegrityError:
        db.rollback()
        raise AppError(
            "CONFLICT",
            detail="This compatibility test was concurrently submitted. Reload its history.",
        ) from None
    tiers = ["basic", "structured", "project"] if body.tier == "all" else [body.tier]
    started = time.monotonic()
    blocked = False
    for tier in tiers:
        stage = ModelCompatibilityStage(
            run_id=run.id, tier=tier, status="not_run" if blocked else "started"
        )
        db.add(stage)
        if blocked:
            stage.completed_at = utcnow()
            stage.result_json = {
                "diagnostic_code": "PREVIOUS_STAGE_FAILED",
                "latency_ms": 0,
                "usage": {},
                "diagnostic": {
                    "stage": "configuration",
                    "message": "Not attempted because an earlier stage failed.",
                    "request_submitted": False,
                },
            }
            db.commit()
            continue
        db.commit()
        secret = None
        reserved = False
        try:
            prepared = probes.description(config, tier, body.role)
            secret = resolve_secret(db, settings, config.configuration_id)
            if config.provider in {"openai", "azure_openai", "anthropic", "gemini"} and not secret:
                raise AppError("CREDENTIAL_REQUIRED")
            remaining = 180 - (time.monotonic() - started)
            if remaining <= 0:
                raise ValueError("Probe suite active budget exhausted")
            stage.metadata_json = {
                **prepared["metadata"],
                "transport_reserved": config.provider != "mock",
                "timeout_seconds": min(config.timeout_seconds, remaining),
            }
            db.commit()  # Committed before transport: a crash can never erase a potential charge.
            reserved = config.provider != "mock"
            result = probes.run(
                prepared, api_key=secret, timeout_seconds=min(config.timeout_seconds, remaining)
            )
            code = (
                result.error.get("code", "PROBE_FAILED")
                if result.error
                else "MOCK_OK"
                if config.provider == "mock"
                else "OK"
            )
            if code == "PROVIDER_HTTP_ERROR":
                status_code = result.diagnostic.get("http_status")
                code = {
                    401: "PROVIDER_AUTH_ERROR",
                    403: "PROVIDER_AUTH_ERROR",
                    404: "PROVIDER_NOT_FOUND",
                    429: "PROVIDER_RATE_LIMITED",
                }.get(
                    status_code,
                    "PROVIDER_SERVER_ERROR"
                    if type(status_code) is int and status_code >= 500
                    else code,
                )
            stage.status = (
                "uncertain"
                if result.error and result.error.get("details", {}).get("uncertain")
                else "failed"
                if result.error
                else "passed"
            )
            stage.result_json = {
                "diagnostic_code": code,
                "latency_ms": result.latency_ms,
                "usage": safe_usage(result.usage),
                "diagnostic": result.diagnostic,
                "provider": config.provider,
                "model": config.model,
                "request_submitted": result.request_submitted,
            }
        except (ValueError, TypeError, AppError) as error:
            from generation.capabilities import CapabilityError

            stage.status = "uncertain" if reserved else "failed"
            stage.result_json = {
                "diagnostic_code": error.code
                if isinstance(error, AppError) and error.code == "CREDENTIAL_REQUIRED"
                else "CONFIGURATION_ERROR",
                "latency_ms": 0,
                "usage": {},
                "diagnostic": {
                    "stage": "configuration",
                    "message": "Frozen configuration, credentials or token reservation could not be validated; sensitive details were omitted.",
                    "request_submitted": reserved,
                },
            }
            if isinstance(error, CapabilityError):
                stage.result_json["diagnostic"].update(
                    provider_error_parameter=error.parameter, message=str(error)
                )
        except Exception:
            stage.status = "uncertain" if reserved else "failed"
            stage.result_json = {
                "diagnostic_code": "PROBE_UNCERTAIN" if reserved else "PROBE_FAILED",
                "latency_ms": 0,
                "usage": {},
                "diagnostic": {
                    "stage": "network",
                    "message": "The stage did not obtain a usable receipt; raw exception text was omitted.",
                    "request_submitted": reserved,
                },
            }
        finally:
            secret = None
        stage.completed_at = utcnow()
        db.commit()
        if stage.status != "passed":
            blocked = True
            run.status = "uncertain" if stage.status == "uncertain" else "failed"
            run.diagnostic_code = stage.result_json["diagnostic_code"]
            db.commit()
    if not blocked:
        run.status = "passed"
        run.diagnostic_code = "MOCK_OK" if config.provider == "mock" else "OK"
    run.completed_at = utcnow()
    db.commit()
    return output(db, run, config_row)


def _project_pass_error(db, config_row, run, role, *, stages=None):
    """Share the exact activation gate with read-only receipt projections."""
    last = latest(db, config_row.id, role)
    if (
        not run
        or not last
        or run.id != last.id
        or run.configuration_id != config_row.id
        or run.config_hash != config_row.config_hash
        or run.role != role
        or run.test_version != probes.VERSION
    ):
        return f"Activation requires the latest passing {role} project test for this exact saved configuration."
    if stages is None:
        stages = db.scalars(
            select(ModelCompatibilityStage).where(ModelCompatibilityStage.run_id == run.id)
        ).all()
    if run.status != "passed" or not any(
        stage.tier == "project" and stage.status == "passed" for stage in stages
    ):
        return f"Activation requires the latest passing {role} project test for this exact saved configuration."
    from .service import as_model_config

    stage = db.scalar(
        select(ModelCompatibilityStage).where(
            ModelCompatibilityStage.run_id == run.id, ModelCompatibilityStage.tier == "project"
        )
    )
    try:
        current = probes.description(as_model_config(config_row), "project", role)["metadata"]
    except (ValueError, TypeError):
        return "The saved project probe is incompatible with the current runtime contract."
    if stage is None or any(
        stage.metadata_json.get(key) != current[key]
        for key in (
            "schema_hash",
            "prompt_hash",
            "configuration_hash",
            "capability_hash",
            "reserved_output_tokens",
            "effective_parameters",
        )
    ):
        return "The project schema or probe policy changed. Test this exact version again before activation."
    return None


def require_project_pass(db, config_row, probe_id, role):
    run = db.get(ModelCompatibilityRun, probe_id) if probe_id else None
    error = _project_pass_error(db, config_row, run, role)
    if error is not None:
        raise AppError("CONFLICT", detail=error)
    return run
