"""Owned memory, task and controlled citation endpoints."""

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session
from contracts.http import Envelope
from contracts.learning import (
    MemorySettingsOut,
    MemorySettingsUpdate,
    MemoryOut,
    MemoryEdit,
    MemoryDelete,
    MemoryControlsUpdate,
    MemoryRecordCreate,
    MemoryAssessmentCreate,
    MemorySummaryOut,
    MemoryProcessingOut,
    LearnerStatePreview,
    LearnerStateOut,
    TaskOut,
    ExposureInput,
    ExposureOut,
    PresentationOut,
    CitationView,
)
from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.core.responses import ok
from app.core.exceptions import AppError
from app.core.config import Settings, get_settings
from app.modules.identity.models import User
from app.modules.answering.models import Message, Job
from app.modules.learning.models import ChatSession
from app.modules.answering.router import owned_answer
from app.modules.answering.service import owned_session
from . import memory, memory_v2, sources, tasks
from .models import MemoryEntry, MemoryWriteEvent, LearningTask

router = APIRouter(tags=["learning state"])


@router.get("/me/memory/settings", response_model=Envelope[MemorySettingsOut])
def memory_settings(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    row = memory.settings_for(db, actor.id, lock=True)
    db.commit()
    return ok(memory.settings_out(row))


@router.patch("/me/memory/settings", response_model=Envelope[MemorySettingsOut])
def save_memory_settings(
    body: MemorySettingsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(memory.update_settings(db, actor.id, body))


@router.get("/me/memories", response_model=Envelope[list[MemoryOut]])
def memories(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(
        [
            memory.entry_out(row)
            for row in db.scalars(
                select(MemoryEntry)
                .where(MemoryEntry.owner_id == actor.id, MemoryEntry.status != "deleted")
                .order_by(MemoryEntry.updated_at.desc())
            )
        ]
    )


@router.patch("/me/memories/{memory_id}", response_model=Envelope[MemoryOut])
def edit_memory(
    memory_id: str,
    body: MemoryEdit,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(memory.edit_entry(db, actor.id, memory_id, body))


@router.post("/me/memories", response_model=Envelope[MemoryOut])
def create_memory(
    body: MemoryRecordCreate, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    return ok(memory_v2.create_record(db, actor.id, body))


@router.patch("/me/memories/{memory_id}/controls", response_model=Envelope[MemoryOut])
def memory_controls(
    memory_id: str,
    body: MemoryControlsUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(memory.update_controls(db, actor.id, memory_id, body))


@router.post("/me/memory/assessments", response_model=Envelope[MemoryOut])
def record_assessment(
    body: MemoryAssessmentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(memory_v2.record_assessment(db, actor, body))


@router.get("/me/memory/summary", response_model=Envelope[MemorySummaryOut])
def memory_summary(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(memory_v2.summary(db, actor.id))


@router.get("/me/memory/processing", response_model=Envelope[list[MemoryProcessingOut]])
def memory_processing(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(memory_v2.processing(db, actor.id))


@router.post("/me/memory/preview", response_model=Envelope[LearnerStateOut])
def preview_learner_state(
    body: LearnerStatePreview,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    configuration: Settings = Depends(get_settings),
):
    from personalisation import memory_v5 as selector
    from personalisation.memory_v2 import MemoryPreparationUnavailable
    from personalisation.memory_policy import load_policy, selector_for_policy
    from personalisation.compiler import compile_profile
    from .memory_v3 import source_reader as legacy_source_reader
    from .memory_v4 import source_reader as condition_source_reader
    from .memory_v5 import source_reader as leading_condition_source_reader
    from app.modules.identity import service as profile_service
    from app.modules.model_settings.service import resolve_active_model_config
    from app.modules.answering.service import model_config
    from generation.token_counting import TokenCounter
    from generation.types import ModelConfig

    settings = memory.settings_for(db, actor.id, lock=True)
    memory_v2.expire_entries(db, actor.id)
    enabled = settings.enabled and body.use_profile
    entries = (
        [
            memory.entry_out(row)
            for row in db.scalars(
                select(MemoryEntry).where(
                    MemoryEntry.owner_id == actor.id, MemoryEntry.status == "active"
                )
            )
            if not row.expires_at or memory.aware(row.expires_at) > memory.utcnow()
        ]
        if enabled
        else []
    )
    selection = None
    if enabled:
        try:
            selection_policy = load_policy(
                getattr(configuration, "memory_semantic_policy_file", None)
            )
            selector = selector_for_policy(selection_policy)
            source_reader = (
                leading_condition_source_reader
                if selector.SELECTOR_VERSION == "query_conditioned_memory_v5"
                else condition_source_reader
                if selector.SELECTOR_VERSION == "query_conditioned_memory_v4"
                else legacy_source_reader
            )
        except MemoryPreparationUnavailable as exc:
            raise AppError("MEMORY_POLICY_UNAVAILABLE") from exc
        profile = profile_service.to_profile_out(
            profile_service.get_or_create_profile(db, actor.id)
        ).model_dump()
        profile_policy = compile_profile(profile, use_profile=True, turn_message=body.question)
        selected_config = resolve_active_model_config(
            db, configuration, actor.workspace_id
        ) or ModelConfig.from_dict(model_config(configuration))
        try:
            selection = selector.select(
                entries,
                body.question,
                profile_policy,
                context=None,
                policy=selection_policy,
                source_reader=source_reader(db, actor.id),
                counter=TokenCounter(selected_config),
            )
        except MemoryPreparationUnavailable as exc:
            raise AppError(
                "CONTEXT_LIMIT", detail="Learning-memory preview exceeds its context budget."
            ) from exc
    data = selection.state if selection else {}
    limitations = list(data.get("limitations", []))
    if selection and selection.trace["status"] == "semantic_unavailable_rules_fallback":
        limitations.append(
            "Local semantic matching is unavailable; rule-based scope selection remains active."
        )
    elif selection and selection.trace["status"] == "disabled_rules_only":
        limitations.append(
            "Local semantic matching is disabled; specific scopes require the named concept."
        )
    if selection and selection.trace["status"] == "owned_condition_rules_only":
        limitations.append(
            "Saved preference conditions are checked against their exact owned source. "
            "Uncertain conditions require confirmation; semantic matching is disabled."
        )
    limitations.append(
        "This preview uses the supplied question, saves no memory and submits no answer. "
        "It makes no cloud-model call."
    )
    db.commit()
    return ok(
        {
            "enabled": enabled,
            "policy_version": selector.SELECTOR_VERSION,
            "fields": data.get("fields", []),
            "entries": data.get("entries", []),
            "query_topics": data.get("query_topics", []),
            "excluded": data.get("excluded", []),
            "limitations": limitations,
        }
    )


@router.delete("/me/memories/{memory_id}", response_model=Envelope[dict])
def delete_memory(
    memory_id: str,
    body: MemoryDelete,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(memory.delete_entry(db, actor.id, memory_id, body.version))


@router.post("/me/memories/{memory_id}/undo", response_model=Envelope[dict])
def undo_memory_save(
    memory_id: str,
    body: MemoryDelete,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    """Undo this saved revision by deleting it; never resurrect a hidden deleted body."""
    return ok(memory.delete_entry(db, actor.id, memory_id, body.version))


@router.get("/me/memories/{memory_id}/source", response_model=Envelope[dict])
def memory_source(
    memory_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    entry = memory.entry_owned(db, actor.id, memory_id)
    message = db.get(Message, entry.source_message_id) if entry.source_message_id else None
    session = db.get(ChatSession, message.session_id) if message else None
    if (
        not message
        or not session
        or session.user_id != actor.id
        or session.workspace_id != actor.workspace_id
        or session.deleted_at
    ):
        raise AppError("NOT_FOUND")
    return ok(
        {"message_id": message.id, "session_id": message.session_id, "content": message.content}
    )


def notices(db, owner_id, session_id, source_message_id=None):
    mids = set(
        db.scalars(
            select(Message.id).where(Message.session_id == session_id, Message.role == "user")
        )
    )
    output = []
    for event in db.scalars(
        select(MemoryWriteEvent)
        .where(MemoryWriteEvent.owner_id == owner_id, MemoryWriteEvent.status == "applied")
        .order_by(MemoryWriteEvent.sequence.desc())
    ):
        if (
            event.source_message_id not in mids
            or source_message_id is not None
            and event.source_message_id != source_message_id
        ):
            continue
        for operation in event.operations:
            if operation.get("operation") not in {"ADD", "UPDATE"}:
                continue
            row = db.get(MemoryEntry, operation.get("memory_id"))
            if (
                row
                and row.status == "active"
                and row.version == operation.get("version")
                and not (row.expires_at and memory.aware(row.expires_at) <= memory.utcnow())
            ):
                output.append(
                    {
                        "memory_id": row.id,
                        "version": row.version,
                        "message": "Learning memory saved.",
                        "action": "undo_save",
                        "source_message_id": event.source_message_id,
                    }
                )
    for job in db.scalars(
        select(Job)
        .where(Job.owner_id == owner_id, Job.kind == "memory", Job.state == "succeeded")
        .order_by(Job.created_at.desc())
    ):
        mid = job.payload.get("source_message_id")
        if mid not in mids or source_message_id is not None and mid != source_message_id:
            continue
        for item in job.payload.get("saved", []):
            row = db.get(MemoryEntry, item["memory_id"])
            if row and row.status == "active" and row.version == item["version"]:
                if not any(
                    e["memory_id"] == row.id and e["version"] == row.version for e in output
                ):
                    output.append({**item, "source_message_id": mid})
    return output[:20]


@router.get("/sessions/{session_id}/memory-notices", response_model=Envelope[list[dict]])
def memory_notices(
    session_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    owned_session(db, session_id, actor)
    return ok(notices(db, actor.id, session_id))


@router.get("/sessions/{session_id}/learning-tasks", response_model=Envelope[list[TaskOut]])
def learning_tasks(
    session_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    owned_session(db, session_id, actor)
    return ok(
        [
            tasks.task_out(row)
            for row in db.scalars(
                select(LearningTask)
                .where(LearningTask.owner_id == actor.id, LearningTask.session_id == session_id)
                .order_by(LearningTask.created_at.desc())
            )
        ]
    )


@router.get("/answers/{answer_id}/presentation", response_model=Envelope[PresentationOut])
def presentation(
    answer_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    owned_answer(db, answer_id, actor)
    row = sources.presentation_for(db, answer_id)
    if not row:
        raise AppError("NOT_FOUND")
    return ok(sources.presentation_out(db, row))


@router.get(
    "/answers/{answer_id}/claims/{claim_id}/sources", response_model=Envelope[list[CitationView]]
)
def claim_sources(
    answer_id: str,
    claim_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    owned_answer(db, answer_id, actor)
    row = sources.presentation_for(db, answer_id)
    if not row:
        raise AppError("NOT_FOUND")
    values = [
        sources.citation_view(db, row, v["evidence_id"], claim_id)
        for v in sources.visible_views(db, row)
        if claim_id in v["claim_ids"]
    ]
    if not values:
        raise AppError("NOT_FOUND")
    return ok(values)


@router.post("/answers/{answer_id}/exposures", response_model=Envelope[ExposureOut])
def exposure(
    answer_id: str,
    body: ExposureInput,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(
        sources.record_exposure(
            db, actor, owned_answer(db, answer_id, actor), body, idempotency_key
        )
    )
