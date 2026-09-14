"""Administration endpoints: capability discovery + outbox inspection.

The capabilities API lets the frontend show only what actually exists -
no hardcoded dead buttons (Spec K09, K17, 1.1).
"""

from __future__ import annotations

from contracts.http import Envelope
from contracts.http import CapabilitiesOut
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_flags, require_roles
from app.core.feature_flags import FeatureFlags
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from app.platform_core.models import OutboxEvent
from app.platform_core.registry import CONTRACT_VERSION, registry
from app.core.config import Settings, get_settings

router = APIRouter(tags=["administration"])


@router.get("/capabilities", response_model=Envelope[CapabilitiesOut])
def capabilities(
    flags: FeatureFlags = Depends(get_flags),
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from app.modules.knowledge.models import (
        ActiveCorpus,
        CorpusRelease,
        ReleaseChunk,
        Chunk,
        Document,
    )
    from app.modules.experiment.models import ExperimentRun, ExperimentItem, TeachingStudyRecord
    from app.modules.experiment.bridge import environment, experiment_model_config
    from app.core.exceptions import AppError
    from app.modules.answering.service import model_config
    from app.modules.model_settings.service import resolve_active_model_config, resolve_secret
    from app.modules.knowledge.models import Configuration
    from generation.types import ModelConfig

    pointer = db.get(ActiveCorpus, 1)
    reasons = []
    if not pointer or not pointer.release_id:
        reasons.append("No active corpus. An administrator must publish a corpus first.")
    elif not db.scalar(
        select(Chunk.id)
        .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            ReleaseChunk.release_id == pointer.release_id,
            Document.active.is_(True),
            Document.revoked.is_(False),
        )
        .limit(1)
    ):
        reasons.append("The active corpus has no currently available sources.")
    corpus_reasons = list(reasons)
    model_mode = settings.model_mode

    def configured(config):
        config.validate()
        if config.provider == "mock":
            return True
        secret = resolve_secret(db, settings, config.configuration_id)
        valid = bool(config.base_url) and (
            config.provider not in {"openai", "azure_openai", "anthropic", "gemini"} or bool(secret)
        )
        secret = None
        return valid

    try:
        effective = resolve_active_model_config(db, settings, actor.workspace_id)
        effective = effective or ModelConfig.from_dict(model_config(settings))
        model_mode = "mock" if effective.provider == "mock" else "live"
        if not configured(effective):
            reasons.append("The selected live provider is not configured.")
    except (AppError, ValueError, TypeError):
        reasons.append("The selected model configuration or credential is unavailable.")
    evaluation_reasons = [
        "A frozen evaluator dataset/run with pending items is required. This does not block chat."
    ]
    for run in db.scalars(
        select(ExperimentRun)
        .join(User, ExperimentRun.owner_id == User.id)
        .where(
            ExperimentRun.state.in_(("frozen", "running")),
            User.workspace_id == actor.workspace_id,
        )
    ):
        pending = db.scalar(
            select(ExperimentItem.id)
            .where(
                ExperimentItem.run_id == run.id,
                ExperimentItem.state == "pending",
                ExperimentItem.command.is_not(None),
            )
            .limit(1)
        )
        pending = pending or db.scalar(
            select(TeachingStudyRecord.id)
            .where(TeachingStudyRecord.run_id == run.id, TeachingStudyRecord.state == "pending")
            .limit(1)
        )
        if not pending or not run.manifest:
            continue
        try:
            actual = environment(
                db, settings, run.configuration_id, workspace_id=actor.workspace_id
            )
            configuration = (
                db.get(Configuration, run.configuration_id) if run.configuration_id else None
            )
            selected = ModelConfig.from_dict(
                experiment_model_config(
                    settings, configuration, db=db, workspace_id=actor.workspace_id
                )
            )
            if not configured(selected):
                raise AppError("MODEL_UNAVAILABLE")
        except (AppError, ValueError, TypeError):
            evaluation_reasons = [
                "The frozen experiment has an unavailable model or configuration."
            ]
            continue
        if actual != run.manifest.get("environment"):
            evaluation_reasons = [
                "The frozen experiment environment has changed; create and freeze a new run."
            ]
            continue
        if run.condition != "E0" and corpus_reasons:
            evaluation_reasons = list(corpus_reasons)
            continue
        evaluation_reasons = []
        break
    return ok(
        {
            "model_mode": model_mode,
            "chat_ready": not reasons,
            "evaluation_ready": not evaluation_reasons,
            "missing_reasons": {"chat": reasons, "evaluation": evaluation_reasons},
            "providers": registry.list(),
            "feature_flags": flags.as_dict(),
            "contract_versions": [
                {"name": "GenerationRequest", "version": CONTRACT_VERSION},
                {"name": "RetrievalRequest", "version": CONTRACT_VERSION},
                {"name": "ParserResult", "version": CONTRACT_VERSION},
                {"name": "DomainEvent", "version": CONTRACT_VERSION},
            ],
        }
    )


@router.get("/admin/events", response_model=Envelope[list[dict]])
def list_events(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    events = db.scalars(
        select(OutboxEvent).order_by(OutboxEvent.created_at.desc()).limit(100)
    ).all()
    return ok(
        [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_version": e.event_version,
                "status": e.status,
                "attempts": e.attempts,
                "trace_id": e.trace_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
    )
