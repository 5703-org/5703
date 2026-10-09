"""Shared durable answer execution with immutable inputs and tail-only revisions."""

from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session, sessionmaker
from app.core.exceptions import AppError
from app.core.logging import trace_id_var
from app.db.base import new_uuid, utcnow
from app.modules.identity.models import User
from app.modules.identity import service as profiles
from app.modules.learning.models import ChatSession
from app.modules.answering.models import *
from app.modules.knowledge.models import ActiveCorpus, Document, CorpusRelease, ReleaseChunk, Chunk
from app.modules.knowledge.service import digest, retrieve
from contracts.models import ChatMessageCreate, ChatResponseV1, MCQResponseV1, EvidenceSnapshot
from conversation.context import select_context
from conversation import (
    query_v14,
    query_v15,
    query_v16,
    query_v17,
    query_v18,
    query_v19,
    query_v20,
    query_v21,
    query_v22,
)
from conversation.query import (
    prepare_query,
    evidence_strategy,
    VERSION as PREPARATION_VERSION,
    LEGACY_VERSION,
)
from conversation.understanding import describe_question
from conversation.requirements import describe_requirements
from conversation.requirements_v4 import (
    VERSION as REQUIREMENTS_V4,
    describe_requirements as describe_requirements_v4,
)
from conversation.practice_context import (
    freeze_policy as freeze_practice_query,
    resolve as resolve_practice_query,
)
from personalisation.compiler import compile_profile
from generation.types import GenerationRequest, ModelConfig, RequestBudget
from generation.service import GenerationService
from generation.token_counting import TokenCounter
from generation.teaching_plan import freeze_generation_policy, build_teaching_plan
from generation.evidence_coverage import assess_evidence_coverage, supplement_once
from generation import (
    teaching_plan_v2,
    coverage_v2,
    teaching_plan_v3,
    teaching_plan_v4,
    teaching_plan_v5,
    teaching_plan_v6,
    teaching_plan_v7,
    teaching_plan_v8,
    teaching_plan_v9,
    teaching_plan_v10,
    coverage_v3,
    coverage_v4,
)
from generation.coverage_query_policy_v1 import (
    base_version_for_source_relation,
    resolve_coverage,
    submission_fields as coverage_query_submission_fields,
    validate_policy as validate_coverage_query_policy,
)
from retrieval.chat import load_policy, rerank_candidates, policy_hash
from retrieval.runtime import resolve_device
from retrieval.relevance import (
    freeze_policy as freeze_relevance_policy,
    screen,
    freeze_selection,
    merge_candidates,
    freeze_facet_fallback,
    facet_fallback,
)
from retrieval.ranking import bm25

ACTIVE = ("queued", "running", "retry_wait")


def _reading_selection_retrieval_query(question, section):
    """Keep generated page-only locations out of semantic retrieval text."""
    prefix = "PDF physical page "
    if section and section.startswith(prefix):
        page = section[len(prefix) :]
        if page and page.isascii() and page.isdigit():
            return question
    return question + "\nTextbook section: " + (section or "selected passage")


def submission_delay_ms(created_at: datetime, started_at: datetime) -> float:
    """Preserve database offsets; naive development timestamps represent UTC."""
    submitted_at = (
        created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
    )
    return max(0.0, (started_at - submitted_at).total_seconds() * 1000)


def owned_session(db, id, actor, lock=False):
    query = select(ChatSession).where(
        ChatSession.id == id, ChatSession.user_id == actor.id, ChatSession.deleted_at.is_(None)
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    session = db.scalar(query)
    if not session:
        raise AppError("NOT_FOUND")
    return session


def active_job(db, session_id):
    return db.scalar(
        select(Job)
        .join(AnswerRequest, AnswerRequest.id == Job.request_id)
        .where(AnswerRequest.session_id == session_id, Job.state.in_(ACTIVE))
    )


def request_owned(db, id, actor):
    req = db.get(AnswerRequest, id)
    if not req or not can_access_owner(db, req.owner_id, actor):
        raise AppError("NOT_FOUND")
    if req.session_id:
        session = db.get(ChatSession, req.session_id)
        if not session or session.deleted_at:
            raise AppError("NOT_FOUND")
    return req


def job_owned(db, id, actor):
    job = db.get(Job, id)
    if not job or not can_access_owner(db, job.owner_id, actor):
        raise AppError("NOT_FOUND")
    return job


def can_access_owner(db, owner_id, actor):
    if owner_id == actor.id:
        return True
    if actor.role.name != "admin":
        return False
    owner = db.get(User, owner_id)
    return bool(owner and owner.workspace_id == actor.workspace_id)


def receipt(db, request, job=None):
    job = job or db.scalar(select(Job).where(Job.request_id == request.id).order_by(Job.created_at))
    return {
        "request_id": request.id,
        "job_id": job.id,
        "user_message_id": request.user_message_id,
        "poll_url": f"/api/v1/jobs/{job.id}",
    }


def idempotent(db, actor_id, route, key, body):
    if not key or len(key) > 128:
        raise AppError(
            "VALIDATION_FAILED", detail="An Idempotency-Key of 1–128 characters is required."
        )
    prior = db.scalar(
        select(AnswerRequest).where(
            AnswerRequest.owner_id == actor_id,
            AnswerRequest.route == route,
            AnswerRequest.idempotency_key == key,
        )
    )
    if prior and prior.body_hash != digest(body):
        raise AppError("IDEMPOTENCY_CONFLICT")
    return prior


def create_snapshot(db, actor_id, session_id, kind, payload):
    value = Snapshot(
        owner_id=actor_id,
        session_id=session_id,
        kind=kind,
        payload=payload,
        content_hash=digest(payload),
    )
    db.add(value)
    db.flush()
    return value


def history_rows(db, session_id):
    messages = db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.sequence)
    ).all()
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "sequence": m.sequence,
            "role": m.role,
            "content": m.content,
            "state": m.state,
            "active_answer_id": m.active_answer_id,
        }
        for m in messages
    ]


def freeze_restatement_context(db, actor, session_id, rows, context, context_hash):
    """Bind a whole-answer restatement to the latest owned completed exchange."""
    value = {
        "version": "completed_answer_restatement_v1",
        "context_snapshot_hash": context_hash,
        "latest_exchange_available": False,
    }
    selected = context.get("messages", [])
    if len(selected) < 2 or not rows:
        return value
    user, assistant = selected[-2:]
    if user.get("role") != "user" or assistant.get("role") != "assistant":
        return value
    if rows[-1]["id"] != assistant.get("message_id"):
        # A later failed, unanswered or excluded turn cannot expose an older answer.
        return value
    answer_id = assistant.get("answer_id")
    if not answer_id:
        return value
    answer = db.scalar(
        select(Answer)
        .join(AnswerRequest, AnswerRequest.id == Answer.request_id)
        .where(
            Answer.id == answer_id,
            Answer.message_id == assistant["message_id"],
            AnswerRequest.owner_id == actor.id,
            AnswerRequest.session_id == session_id,
            AnswerRequest.user_message_id == user["message_id"],
            AnswerRequest.assistant_message_id == assistant["message_id"],
        )
    )
    if answer is None:
        return value
    return {
        **value,
        "user_message_id": user["message_id"],
        "assistant_message_id": assistant["message_id"],
        "answer_id": answer.id,
        "answer_response_type": answer.response.get("response_type"),
        "latest_exchange_available": True,
    }


def restatement_query_history(context, marker):
    """Project only frozen answer-type metadata, leaving the original snapshot intact."""
    history = context.get("messages", [])
    if not history or not isinstance(marker, dict):
        return history
    if (
        marker.get("version") != "completed_answer_restatement_v1"
        or marker.get("context_snapshot_hash") != digest(context)
        or marker.get("assistant_message_id") != history[-1].get("message_id")
        or marker.get("answer_id") != history[-1].get("answer_id")
        or len(history) < 2
        or marker.get("user_message_id") != history[-2].get("message_id")
    ):
        return history
    return [
        *history[:-1],
        {
            **history[-1],
            "answer_response_type": marker.get("answer_response_type"),
            "latest_exchange_available": marker.get("latest_exchange_available") is True,
        },
    ]


def model_config(settings):
    if settings.model_mode == "live" and settings.llm_provider == "mock":
        raise AppError(
            "MODEL_UNAVAILABLE", detail="Select a configured live provider before using live mode."
        )
    return ModelConfig(
        provider="mock" if settings.model_mode == "mock" else settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_api_base or None,
        api_key_env="LLM_API_KEY" if settings.model_mode == "live" else None,
        timeout_seconds=settings.provider_timeout_seconds,
        window_tokens=settings.model_window_tokens,
        max_tokens=settings.model_output_tokens,
    ).to_dict()


def persist_summary(db, session_id, context):
    if not context["summary_id"]:
        return
    existing = db.get(SessionSummary, context["summary_id"])
    if existing:
        # The deterministic ID includes current source revision fingerprints.
        existing.invalidated = False
        return
    db.add(
        SessionSummary(
            id=context["summary_id"],
            session_id=session_id,
            covered_until_sequence=context["covered_until_sequence"],
            source_message_ids=context["token_budget"].get("summary_source_message_ids", []),
            summary_text=context["summary_text"],
            content_hash=context["summary_hash"],
            token_count=context["token_budget"].get("summary_tokens", 0),
            method="extractive-v1",
        )
    )


def submit_chat(db, settings, actor, session_id, body: ChatMessageCreate, key):
    from app.modules.learning_state import memory, tasks

    memory.settings_for(db, actor.id, lock=True)
    session = owned_session(db, session_id, actor, lock=True)
    route = f"/sessions/{session_id}/messages"
    request_body = body.model_dump()
    if body.answer_mode == "textbook":
        # Omitted/default textbook retains the pre-mode idempotency identity.
        request_body.pop("answer_mode")
    for field, default in (
        ("teaching_mode", None),
        ("task_id", None),
        ("task_action", "auto"),
        ("task_version", None),
        ("pending_tutor_question_id", None),
        ("pending_tutor_question_version", None),
        ("turn_role", "auto"),
        ("reading_context", None),
    ):
        if request_body.get(field) == default:
            request_body.pop(field, None)
    prior = idempotent(db, actor.id, route, key, request_body)
    if prior:
        return receipt(db, prior)
    if session.status != "active":
        raise AppError("CONFLICT", detail="Restore the conversation before sending a message.")
    if active_job(db, session_id):
        raise AppError("SESSION_BUSY")
    reading_context = None
    if body.reading_context is not None:
        from app.modules.learning_product.library import freeze_reading_context

        reading_context = freeze_reading_context(db, actor, body.reading_context)
    from app.modules.model_settings.service import (
        resolve_active_model_config,
        resolve_active_checker_model_config,
    )

    selected_config = resolve_active_model_config(db, settings, actor.workspace_id)
    selected_config = selected_config or ModelConfig.from_dict(model_config(settings))
    try:
        selected_config.validate()
        checker_config = resolve_active_checker_model_config(db, settings, actor.workspace_id)
        checker_config = checker_config or replace(
            selected_config, max_tokens=max(selected_config.max_tokens, 4096)
        )
        checker_config.validate()
        counter = TokenCounter(selected_config)
    except (ValueError, TypeError) as exc:
        raise AppError(
            "MODEL_UNAVAILABLE",
            detail="The configured model or its required local tokenizer is unavailable. Check the saved model settings.",
        ) from exc
    try:
        retrieval_policy = (
            load_policy(getattr(settings, "chat_retrieval_config", None))
            if body.answer_mode == "textbook"
            else None
        )
    except (ValueError, OSError, TypeError) as exc:
        raise AppError(
            "SOURCE_UNAVAILABLE", detail="The configured interactive retrieval policy is invalid."
        ) from exc
    rows = history_rows(db, session_id)
    cutoff = max((m["sequence"] for m in rows), default=0)
    profile = profiles.to_profile_out(profiles.get_or_create_profile(db, actor.id)).model_dump()
    policy = compile_profile(profile, use_profile=body.use_profile, turn_message=body.content)
    policy["use_profile"] = body.use_profile
    ps = create_snapshot(db, actor.id, session_id, "profile", policy)
    context = select_context(session_id, rows, cutoff, ps.id, counter=counter).model_dump()
    cs = create_snapshot(db, actor.id, session_id, "conversation", context)
    persist_summary(db, session_id, context)
    message = Message(session_id=session_id, sequence=cutoff + 1, role="user", content=body.content)
    db.add(message)
    db.flush()
    teaching = tasks.resolve_task(db, actor, session, message, body, context)
    if teaching:
        teaching["attempt_history"] = tasks.recent_attempt_feedback(
            db, actor.id, teaching["task_id"]
        )
    from personalisation.memory_v2 import MemoryPreparationUnavailable

    from personalisation.memory_v5 import freeze_policy as freeze_memory_selection
    from personalisation.memory_policy import load_policy as load_memory_selection
    from personalisation.memory_policy import selector_for_policy as memory_selector

    memory_selection_policy = freeze_memory_selection()
    memory_policy_version = memory_selector(memory_selection_policy).SELECTOR_VERSION
    memory_stage = {"status": "ready", "policy_version": memory_policy_version}
    try:
        memory_selection_policy = load_memory_selection(
            getattr(settings, "memory_semantic_policy_file", None)
        )
        memory_policy_version = memory_selector(memory_selection_policy).SELECTOR_VERSION
        memory_stage["policy_version"] = memory_policy_version
        memory_snapshot = memory.freeze_memory(
            db,
            actor.id,
            body.content,
            body.use_profile,
            policy_version=memory_policy_version,
            semantic_policy=memory_selection_policy,
            current_message_id=message.id,
            profile=policy,
            context=context,
            counter=counter,
        )
        if memory_snapshot is None:
            memory_stage["status"] = "disabled"
        else:
            selection_trace = memory_snapshot.payload.get("selection_trace", {})
            memory_stage.update(
                semantic_status=selection_trace.get("status"),
                candidate_count=len(selection_trace.get("candidates", [])),
                selected_count=len(selection_trace.get("selected_ids", [])),
                source_reread_count=len(selection_trace.get("source_rereads", [])),
                semantic_elapsed_ms=selection_trace.get("elapsed_ms"),
            )
    except MemoryPreparationUnavailable as exc:
        # Optional preparation can be unavailable before state is frozen. Revoked
        # snapshots and transaction failures retain their explicit error paths.
        memory_snapshot = None
        memory_stage = {
            "status": "unavailable",
            "policy_version": memory_policy_version,
            "code": exc.code,
        }
    pointer = db.get(ActiveCorpus, 1)
    req = AnswerRequest(
        owner_id=actor.id,
        route=route,
        idempotency_key=key,
        body_hash=digest(request_body),
        mode="interactive_chat",
        response_schema="chat_response_v1",
        session_id=session_id,
        user_message_id=message.id,
        context_snapshot_id=cs.id,
        profile_snapshot_id=ps.id,
        release_id=reading_context["release_id"]
        if reading_context
        else pointer.release_id
        if pointer and body.answer_mode == "textbook"
        else None,
        command={
            "question": body.content,
            "enhancement_version": "learning_enhancement_v1",
            "reliability_policy": "evidence_reliability_v5",
            "requirements_version": "question_requirements_v8"
            if settings.chat_query_preparation_policy == "anchored_reference_v22"
            else "question_requirements_v7"
            if settings.chat_query_preparation_policy == "anchored_reference_v21"
            else "question_requirements_v6"
            if settings.chat_query_preparation_policy == "anchored_reference_v20"
            else "question_requirements_v5"
            if settings.chat_query_preparation_policy
            in {"anchored_reference_v17", "anchored_reference_v18", "anchored_reference_v19"}
            else REQUIREMENTS_V4,
            "generation_policy": teaching_plan_v10.freeze_generation_policy(),
            **coverage_query_submission_fields(
                settings.chat_coverage_query_policy,
                source_relation_policy=settings.chat_source_relation_policy,
                answer_mode=body.answer_mode,
            ),
            **({"reading_context": reading_context} if reading_context else {}),
            "checker_payload_policy": "lossless_checker_tables_v1",
            "joint_checker_policy": settings.chat_joint_checker_policy,
            "provider_output_policy": settings.chat_provider_output_policy,
            "source_relation_policy": settings.chat_source_relation_policy
            if settings.chat_source_relation_policy != "off"
            else None,
            "retrieval_optimization": "validated_release_cache_v1"
            if settings.chat_retrieval_cache
            else None,
            "generation_context_policy": "complementary_context_v2",
            "source_block_policy": settings.chat_source_block_policy,
            "repair_policy": "practice_hint_repair_v5"
            if freeze_practice_query(teaching) and teaching.get("teaching_mode") == "hint"
            else "claim_patch_repair_v3",
            "attribution_strategy": "posthoc_spans",
            "teaching_condition": "T2",
            "teaching_context": teaching,
            **(
                {"practice_query_policy": freeze_practice_query(teaching)}
                if freeze_practice_query(teaching)
                else {}
            ),
            "memory_snapshot_id": memory_snapshot.id if memory_snapshot else None,
            "memory_policy_version": memory_policy_version,
            "memory_selection_policy": memory_selection_policy,
            "memory_stage": memory_stage,
            "checker_config": checker_config.to_dict(),
            "checker_reservation_policy": "explicit_active_checker_or_generator_v2",
            "model_config": selected_config.to_dict(),
            "condition": "E1",
            "answer_mode": body.answer_mode,
            "answer_mode_policy": "explicit_per_request_v1",
            **(
                {
                    "restatement_context": freeze_restatement_context(
                        db, actor, session_id, rows, context, cs.content_hash
                    )
                }
                if settings.chat_query_preparation_policy
                in {
                    "anchored_reference_v16",
                    "anchored_reference_v17",
                    "anchored_reference_v18",
                    "anchored_reference_v19",
                    "anchored_reference_v20",
                    "anchored_reference_v21",
                    "anchored_reference_v22",
                }
                else {}
            ),
            "preparation_version": query_v22.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v22"
            else query_v21.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v21"
            else query_v20.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v20"
            else query_v19.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v19"
            else query_v18.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v18"
            else query_v17.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v17"
            else query_v16.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v16"
            else query_v15.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v15"
            else query_v14.VERSION
            if settings.chat_query_preparation_policy == "anchored_reference_v14"
            else PREPARATION_VERSION,
            "evidence_selection_policy": freeze_selection(retrieval_policy),
            "retrieval_policy": retrieval_policy,
            "local_model_device": settings.local_model_device,
            "relevance_policy": freeze_relevance_policy(retrieval_policy)
            if settings.chat_relevance_gate
            else None,
            "facet_fallback_policy": freeze_facet_fallback(retrieval_policy)
            if settings.chat_relevance_gate
            else None,
        },
        budget=RequestBudget(
            max_calls=settings.max_provider_calls,
            max_active_seconds=settings.request_timeout_seconds,
        ).to_dict(),
    )
    req.trace = {
        "http_trace_id": trace_id_var.get(),
        "retrieval_policy": retrieval_policy,
        "retrieval_policy_hash": policy_hash(retrieval_policy) if retrieval_policy else None,
        "memory_stage": memory_stage,
    }
    db.add(req)
    db.flush()
    message.request_id = req.id
    job = Job(request_id=req.id, owner_id=actor.id)
    db.add(job)
    db.flush()
    if memory_stage["status"] == "ready":
        memory.enqueue_extraction(
            db,
            actor.id,
            message,
            selected_config.to_dict(),
            body.use_profile,
            policy_version=(
                "typed_memory_v5"
                if memory_policy_version == "query_conditioned_memory_v5"
                else "typed_memory_v4"
                if memory_policy_version == "query_conditioned_memory_v4"
                else "typed_memory_v2"
            ),
        )
    if session.title == "New chat":
        session.title = body.content[:100]
    session.updated_at = utcnow()
    session.version += 1
    db.commit()
    return receipt(db, req, job)


def tail_user(db, session_id):
    return db.scalar(
        select(Message)
        .where(Message.session_id == session_id, Message.role == "user")
        .order_by(Message.sequence.desc())
    )


def can_retry(db, req):
    if req.trace.get("memory_revoked"):
        return False
    try:
        validate_learning_context(db, req)
    except AppError:
        return False
    if req.mode != "interactive_chat":
        return False
    if req.state not in ("error", "cancelled") or req.regeneration_of:
        return False
    if req.session_id:
        session = db.get(ChatSession, req.session_id)
        tail = tail_user(db, req.session_id)
        if (
            not session
            or session.status != "active"
            or session.deleted_at
            or not tail
            or tail.id != req.user_message_id
            or active_job(db, req.session_id)
        ):
            return False
    if db.scalar(select(Answer.id).where(Answer.request_id == req.id)):
        return False
    budget = RequestBudget.from_dict(req.budget)
    return budget.consumed_calls < budget.max_calls and budget.remaining_seconds > 0


def retry(db, actor, request_id, key):
    req = request_owned(db, request_id, actor)
    if req.command.get("enhancement_version"):
        from app.modules.learning_state.memory import settings_for

        settings_for(db, actor.id, lock=True)
    if req.session_id:
        owned_session(db, req.session_id, actor, True)
    if not key or len(key) > 128:
        raise AppError("VALIDATION_FAILED")
    previous = db.scalar(
        select(Job).where(Job.request_id == req.id, Job.payload["retry_key"].as_string() == key)
    )
    if previous:
        return receipt(db, req, previous)
    validate_learning_context(db, req, lock=True)
    if not can_retry(db, req):
        raise AppError("RETRY_NOT_ALLOWED")
    req.state = "queued"
    if req.user_message_id:
        db.get(Message, req.user_message_id).state = "queued"
    job = Job(request_id=req.id, owner_id=actor.id, payload={"retry_key": key})
    db.add(job)
    db.commit()
    return receipt(db, req, job)


def can_regenerate(db, answer):
    req = db.get(AnswerRequest, answer.request_id)
    if req.trace.get("memory_revoked"):
        return False
    if not req.session_id:
        return False
    session = db.get(ChatSession, req.session_id)
    tail = tail_user(db, req.session_id)
    message = db.get(Message, answer.message_id)
    return bool(
        session
        and session.status == "active"
        and not session.deleted_at
        and tail
        and tail.id == req.user_message_id
        and message
        and message.active_answer_id == answer.id
        and not active_job(db, req.session_id)
    )


def regenerate(db, actor, answer_id, key):
    answer = db.get(Answer, answer_id)
    if not answer:
        raise AppError("NOT_FOUND")
    old = request_owned(db, answer.request_id, actor)
    if old.command.get("enhancement_version"):
        from app.modules.learning_state.memory import settings_for

        settings_for(db, actor.id, lock=True)
    owned_session(db, old.session_id, actor, True)
    route = f"/answers/{answer_id}/regenerate"
    prior = idempotent(db, actor.id, route, key, {})
    if prior:
        return receipt(db, prior)
    if not can_regenerate(db, answer):
        raise AppError("REGENERATE_NOT_ALLOWED")
    frozen_command = dict(old.command)
    if old.command.get("enhancement_version"):
        from app.modules.learning_state import memory, tasks

        memory.read_snapshot(db, old.owner_id, old.command.get("memory_snapshot_id"))
        frozen_command["teaching_context"] = tasks.refresh_disclosures(
            db, old.owner_id, old.command["teaching_context"]
        )
    fresh_budget = RequestBudget(
        max_calls=old.budget.get("max_calls", 4),
        max_active_seconds=old.budget.get("max_active_seconds", 180),
    ).to_dict()
    req = AnswerRequest(
        owner_id=actor.id,
        route=route,
        idempotency_key=key,
        body_hash=digest({}),
        mode=old.mode,
        response_schema=old.response_schema,
        session_id=old.session_id,
        user_message_id=old.user_message_id,
        assistant_message_id=answer.message_id,
        context_snapshot_id=old.context_snapshot_id,
        profile_snapshot_id=old.profile_snapshot_id,
        release_id=old.release_id,
        config_id=old.config_id,
        regeneration_of=answer.id,
        command=frozen_command,
        budget=fresh_budget,
    )
    db.add(req)
    db.flush()
    job = Job(request_id=req.id, owner_id=actor.id)
    db.add(job)
    db.commit()
    return receipt(db, req, job)


def reconcile_cancelled_request(db, job):
    """Reconcile a terminal cancellation only when it is still the latest job.

    The caller serializes session mutation before locking the job. No retry,
    published answer, frozen input or consumed budget is replaced.
    """
    if job.state != "cancelled" or job.kind != "answer" or not job.request_id:
        return False
    req = db.scalar(
        select(AnswerRequest)
        .where(AnswerRequest.id == job.request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not req
        or req.mode != "interactive_chat"
        or req.state not in {"queued", "processing", "cancelled"}
    ):
        return False
    latest = db.scalar(
        select(Job.id)
        .where(Job.request_id == req.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(1)
    )
    if latest != job.id or db.scalar(
        select(Job.id).where(Job.request_id == req.id, Job.id != job.id, Job.state.in_(ACTIVE))
    ):
        return False
    if job.answer_id or db.scalar(select(Answer.id).where(Answer.request_id == req.id)):
        return False
    message = (
        db.get(Message, req.user_message_id)
        if req.user_message_id and not req.regeneration_of
        else None
    )
    if (
        req.state == "cancelled"
        and (message is None or message.state == "cancelled")
        and job.stage == "cancelled"
        and job.execution_token is None
    ):
        return False
    previous = {
        "job_id": job.id,
        "request_state_before": req.state,
        "message_state_before": message.state if message else None,
        "job_stage_before": job.stage,
        "execution_token_cleared": job.execution_token is not None,
        "recorded_at": utcnow().isoformat(),
        "reason": "explicit_cancelled_request_reconciliation",
    }
    history = list(req.trace.get("terminal_state_reconciliation", []))
    req.trace = {**req.trace, "terminal_state_reconciliation": history + [previous]}
    req.state = "cancelled"
    if message:
        message.state = "cancelled"
    job.stage = "cancelled"
    job.execution_token = None
    db.flush()
    return True


def cancel_job(db, job):
    if job.state == "cancelled":
        reconcile_cancelled_request(db, job)
        return job
    if job.state not in ACTIVE:
        return job
    job.state = "cancelled"
    job.stage = "cancelled"
    job.execution_token = None
    if job.request_id:
        req = db.get(AnswerRequest, job.request_id)
        req.state = "cancelled"
        if req.user_message_id and not req.regeneration_of:
            db.get(Message, req.user_message_id).state = "cancelled"
    from app.modules.knowledge.service import mark_operation_interrupted

    error = {"code": "CANCELLED", "message": "The operation was cancelled.", "details": {}}
    mark_operation_interrupted(db, job, error)
    if job.kind == "teaching":
        from app.modules.experiment.bridge import interrupt_teaching

        interrupt_teaching(db, job, error)
    db.flush()
    return job


def job_out(db, job):
    req = db.get(AnswerRequest, job.request_id) if job.request_id else None
    return {
        "id": job.id,
        "request_id": job.request_id or job.id,
        "state": job.state,
        "stage": job.stage,
        "error": job.error,
        "answer_id": job.answer_id,
        "can_retry": can_retry(db, req) if req else False,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def answer_out(db, answer):
    req = db.get(AnswerRequest, answer.request_id)
    evidence = []
    for e in db.scalars(
        select(Evidence).where(Evidence.answer_id == answer.id).order_by(Evidence.evidence_id)
    ):
        doc = db.get(Document, e.document_id)
        if doc and not doc.revoked:
            evidence.append(e.payload)
        # Revoked evidence remains retrievable only as explicit 410 through the evidence endpoint.
    from app.modules.learning_state import sources, tasks
    from app.modules.learning_state.models import LearningTask

    presentation = sources.presentation_for(db, answer.id)
    controlled_hint = presentation and presentation.payload.get("teaching_mode") == "hint"
    learning_task = (
        db.get(LearningTask, presentation.task_id)
        if presentation and presentation.task_id
        else None
    )
    return {
        "id": answer.id,
        "request_id": req.id,
        "job_id": answer.job_id,
        "message_id": answer.message_id,
        "mode": req.mode,
        "response_schema": answer.response_schema,
        "status": "refused"
        if answer.response.get("response_type") == "refusal" or answer.response.get("refused")
        else "clarification"
        if answer.response.get("response_type") == "clarification"
        else "answered",
        "model_mode": answer.model_mode,
        "answer_mode": req.command.get("answer_mode", "textbook"),
        "source_provenance": "benchmark_protocol"
        if req.mode != "interactive_chat"
        else "model_general_knowledge_unverified"
        if req.command.get("answer_mode", "textbook") == "general_knowledge"
        else "textbook_evidence",
        "response": answer.response,
        "evidence": [] if controlled_hint else evidence,
        "presentation": sources.presentation_out(db, presentation) if presentation else None,
        "attribution": sources.public_attribution(db, presentation) if presentation else None,
        "teaching_mode": presentation.payload.get("teaching_mode", "direct")
        if presentation
        else "direct",
        "task_id": presentation.task_id if presentation else None,
        "learning_task": tasks.task_out(learning_task) if learning_task else None,
        "help_level": presentation.payload.get("help_level", 0) if presentation else 0,
        "memory_notices": [],
        "answer_completeness": req.trace.get("token_budget", {}).get("answer_completeness"),
        "reading_context": {
            key: value
            for key, value in req.command.get("reading_context", {}).items()
            if key not in {"allowed_chunk_ids", "selected_chunk_ids"}
        }
        or None,
        "profile_snapshot": db.get(Snapshot, req.profile_snapshot_id).payload
        if req.profile_snapshot_id and not controlled_hint
        else None,
        "conversation_snapshot": db.get(Snapshot, req.context_snapshot_id).payload
        if req.context_snapshot_id and not controlled_hint
        else None,
        "timing": answer.timing,
        "can_regenerate": can_regenerate(db, answer),
    }


def messages_page(db, session_id, after, limit):
    rows = list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session_id, Message.sequence > after)
            .order_by(Message.sequence)
            .limit(limit + 1)
        )
    )
    items = []
    for m in rows[:limit]:
        a = db.get(Answer, m.active_answer_id) if m.active_answer_id else None
        items.append(
            {
                "id": m.id,
                "session_id": m.session_id,
                "sequence": m.sequence,
                "role": m.role,
                "content": m.content,
                "state": m.state,
                "active_answer_id": m.active_answer_id,
                "answer": answer_out(db, a) if a else None,
                "request_id": m.request_id,
                "created_at": m.created_at.isoformat(),
            }
        )
    job = active_job(db, session_id)
    latest = db.scalar(
        select(Job)
        .join(AnswerRequest, AnswerRequest.id == Job.request_id)
        .where(AnswerRequest.session_id == session_id)
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    return {
        "items": items,
        "next_after_sequence": items[-1]["sequence"] if len(rows) > limit else None,
        "active_job_id": job.id if job else None,
        "latest_job_id": latest.id if latest else None,
    }


class ExecutionCancelled(Exception):
    pass


def inherited_candidates(db, release_id, rows):
    """Validate saved evidence against this request's pinned release and live visibility."""
    from app.modules.learning_state.sources import exact_evidence

    release = db.get(CorpusRelease, release_id) if release_id else None
    eligible, excluded = [], []
    for item in rows:
        chunk = db.get(Chunk, item["chunk_id"])
        doc = db.get(Document, item["asset_id"])
        membership = db.get(ReleaseChunk, (release_id, item["chunk_id"])) if release_id else None
        reason = None
        if not doc or not doc.active or doc.revoked:
            reason = "source_unavailable"
        elif (
            not release or release.state not in ("active", "retired", "validated") or not membership
        ):
            reason = "outside_frozen_release"
        elif (
            not chunk
            or chunk.document_id != item["asset_id"]
            or chunk.processing_id != item["processing_id"]
            or not exact_evidence(chunk, item)
        ):
            reason = "source_identity_mismatch"
        if reason:
            excluded.append({"chunk_id": item["chunk_id"], "reason": reason})
        else:
            eligible.append(dict(item))
    return eligible, {
        "release_id": release_id,
        "available_count": len(rows),
        "eligible_count": len(eligible),
        "eligible_chunk_ids": [row["chunk_id"] for row in eligible],
        "excluded": excluded,
        "rescored_chunk_ids": [],
    }


def validate_learning_context(db, req, *, lock=False):
    """Fence every provider stage and publication against revoked private context."""
    if not req.command.get("enhancement_version") or req.mode != "interactive_chat":
        return None
    from app.modules.learning_state import memory, tasks

    reading = req.command.get("reading_context")
    if reading:
        from app.modules.learning_product.library import validate_reading_context

        if reading["release_id"] != req.release_id:
            raise AppError(
                "EVIDENCE_UNAVAILABLE", detail="Reading and request release identities differ."
            )
        validate_reading_context(db, db.get(User, req.owner_id), reading)

    memory.settings_for(db, req.owner_id, lock=lock)
    tasks.validate_task(db, req.owner_id, req.command.get("teaching_context"))
    return memory.read_snapshot(db, req.owner_id, req.command.get("memory_snapshot_id"))


def safe_prompt_trace(messages, memory_context):
    if not memory_context:
        return messages
    return [
        {
            "role": item.get("role"),
            "content_sha256": hashlib.sha256(str(item.get("content", "")).encode()).hexdigest(),
            "character_count": len(str(item.get("content", ""))),
            "redacted": "memory_context",
        }
        for item in messages
    ]


def lock_request_session(db, req, *, skip_locked=False):
    """Acquire the parent session before a job or its FK-linked writes.

    Cancellation, archive and final publication already serialize on this
    row. Preparation and provider callbacks must follow the same order.
    Ownership and frozen request identity remain the caller's responsibility.
    """
    if req.session_id:
        with db.no_autoflush:
            return db.scalar(
                select(ChatSession)
                .where(ChatSession.id == req.session_id)
                .with_for_update(skip_locked=skip_locked)
                .execution_options(populate_existing=True)
            )
    return None


def execute_answer(engine, settings, job_id, token, *, decision_shadow_binding=None):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    start = time.perf_counter()
    with factory() as db:
        initial_job = db.get(Job, job_id)
        req = db.get(AnswerRequest, initial_job.request_id)
        memory_context = validate_learning_context(db, req, lock=True)
        lock_request_session(db, req)
        job = db.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job.execution_token != token or job.state != "running":
            return
        if req.mode != "interactive_chat":
            from app.modules.experiment.bridge import validate_request_environment

            try:
                validate_request_environment(db, settings, req)
            except AppError as exc:
                fail_job(
                    db,
                    job,
                    {
                        "code": exc.code,
                        "message": exc.detail or "Frozen environment changed.",
                        "details": {},
                    },
                )
                db.commit()
                return
        req.state = "processing"
        if req.command.get("reliability_policy") in {
            "evidence_reliability_v3",
            "evidence_reliability_v4",
            "evidence_reliability_v5",
        }:
            started_at = utcnow()
            req.trace = {
                **req.trace,
                "worker_started_at": started_at.isoformat(),
                "submission_to_worker_start_ms": submission_delay_ms(job.created_at, started_at),
            }
        job.stage = "preparing"
        if req.user_message_id and not req.regeneration_of:
            db.get(Message, req.user_message_id).state = "processing"
        context = (
            db.get(Snapshot, req.context_snapshot_id).payload if req.context_snapshot_id else {}
        )
        policy = (
            db.get(Snapshot, req.profile_snapshot_id).payload if req.profile_snapshot_id else None
        )
        history = context.get("messages", [])
        question = req.command["question"]
        answer_mode = req.command.get("answer_mode", "textbook")
        initial_active_seconds = req.budget.get("active_seconds", 0)
        query_started = time.perf_counter()
        active_query_preparer = (
            query_v22.prepare_query
            if req.command.get("preparation_version") == query_v22.VERSION
            else query_v21.prepare_query
            if req.command.get("preparation_version") == query_v21.VERSION
            else query_v20.prepare_query
            if req.command.get("preparation_version") == query_v20.VERSION
            else query_v19.prepare_query
            if req.command.get("preparation_version") == query_v19.VERSION
            else query_v18.prepare_query
            if req.command.get("preparation_version") == query_v18.VERSION
            else query_v17.prepare_query
            if req.command.get("preparation_version") == query_v17.VERSION
            else query_v16.prepare_query
            if req.command.get("preparation_version") == query_v16.VERSION
            else query_v15.prepare_query
            if req.command.get("preparation_version") == query_v15.VERSION
            else query_v14.prepare_query
            if req.command.get("preparation_version") == query_v14.VERSION
            else prepare_query
        )
        prepared = (
            active_query_preparer(
                question,
                restatement_query_history(context, req.command.get("restatement_context"))
                if req.command.get("preparation_version")
                in {
                    query_v16.VERSION,
                    query_v17.VERSION,
                    query_v18.VERSION,
                    query_v19.VERSION,
                    query_v20.VERSION,
                    query_v21.VERSION,
                    query_v22.VERSION,
                }
                else history,
                context.get("summary_text"),
                version=req.command.get("preparation_version", LEGACY_VERSION),
            ).model_dump()
            if req.mode == "interactive_chat"
            else None
        )
        teaching_context = req.command.get("teaching_context")
        current_core = req.command.get("reliability_policy") == "evidence_reliability_v5"
        reading_context = req.command.get("reading_context")
        allowed_chunk_ids = reading_context.get("allowed_chunk_ids") if reading_context else None
        scope_options = (
            {"allowed_chunk_ids": allowed_chunk_ids} if allowed_chunk_ids is not None else {}
        )
        if (
            reading_context
            and reading_context.get("selection")
            and prepared
            and (
                not prepared["needs_clarification"]
                or prepared.get("fallback_reason") == "missing_referent"
            )
        ):
            # The exact passage stays in generator context. The embedding query
            # uses its section anchor rather than truncating an 8,000-char quote.
            prepared = {
                **prepared,
                "standalone_query": _reading_selection_retrieval_query(
                    question, reading_context.get("section")
                ),
                "needs_clarification": False,
                "intent": "factual",
                "topic_relation": "new_topic",
                "fallback_reason": "verified_reading_selection",
            }
        if (
            teaching_context
            and teaching_context.get("continuing")
            and (
                teaching_context.get("requested_help") in {"more_hint", "full_explanation"}
                or teaching_context.get("turn_role") == "learner_attempt"
            )
        ):
            prepared = active_query_preparer(
                teaching_context["current_problem"],
                [],
                version=req.command.get("preparation_version", LEGACY_VERSION),
            ).model_dump()
        selection_policy = (
            req.command.get("evidence_selection_policy") if req.mode == "interactive_chat" else None
        )
        try:
            practice_query = (
                resolve_practice_query(
                    question,
                    prepared,
                    teaching_context,
                    policy=req.command.get("practice_query_policy"),
                    preparation_version=req.command.get("preparation_version", LEGACY_VERSION),
                )
                if req.mode == "interactive_chat" and prepared
                else None
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise AppError(
                "SOURCE_UNAVAILABLE",
                detail="The frozen public practice query context is unavailable.",
            ) from exc
        if practice_query:
            prepared = practice_query[0]
        understanding = (
            practice_query[1]
            if practice_query
            else (
                query_v22.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v8"
                and prepared
                and prepared.get("preparation_version") == query_v22.VERSION
                else query_v21.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v7"
                and prepared
                and prepared.get("preparation_version") == query_v21.VERSION
                else query_v20.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v6"
                and prepared
                and prepared.get("preparation_version") == query_v20.VERSION
                else query_v19.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v5"
                and prepared
                and prepared.get("preparation_version") == query_v19.VERSION
                else query_v18.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v5"
                and prepared
                and prepared.get("preparation_version") == query_v18.VERSION
                else query_v17.describe_requirements
                if current_core
                and req.command.get("requirements_version") == "question_requirements_v5"
                and prepared
                and prepared.get("preparation_version") == query_v17.VERSION
                else query_v16.describe_requirements
                if current_core
                and req.command.get("requirements_version") == REQUIREMENTS_V4
                and prepared
                and prepared.get("preparation_version") == query_v16.VERSION
                else query_v15.describe_requirements
                if current_core
                and req.command.get("requirements_version") == REQUIREMENTS_V4
                and prepared.get("preparation_version") == query_v15.VERSION
                else query_v14.describe_requirements
                if current_core
                and req.command.get("requirements_version") == REQUIREMENTS_V4
                and prepared.get("preparation_version") == query_v14.VERSION
                else describe_requirements_v4
                if current_core and req.command.get("requirements_version") == REQUIREMENTS_V4
                else describe_requirements
                if current_core
                else describe_question
            )(
                teaching_context["current_problem"]
                if teaching_context and teaching_context.get("turn_role") == "learner_attempt"
                else question,
                prepared,
                restatement_query_history(context, req.command.get("restatement_context"))
                if prepared.get("preparation_version")
                in {
                    query_v18.VERSION,
                    query_v19.VERSION,
                    query_v20.VERSION,
                    query_v21.VERSION,
                    query_v22.VERSION,
                }
                else history,
            )
            if prepared and selection_policy
            else None
        )
        generation_policy = (
            req.command.get("generation_policy") if req.mode == "interactive_chat" else None
        )
        distributed_coverage = bool(
            current_core
            and isinstance(generation_policy, dict)
            and generation_policy.get("version")
            in {
                teaching_plan_v3.VERSION,
                teaching_plan_v4.VERSION,
                teaching_plan_v5.VERSION,
                teaching_plan_v6.VERSION,
                teaching_plan_v7.VERSION,
                teaching_plan_v8.VERSION,
                teaching_plan_v9.VERSION,
                teaching_plan_v10.VERSION,
            }
        )
        active_teaching_plan = (
            teaching_plan_v10
            if distributed_coverage
            and generation_policy.get("version") == teaching_plan_v10.VERSION
            else teaching_plan_v9
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v9.VERSION
            else teaching_plan_v8
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v8.VERSION
            else teaching_plan_v7
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v7.VERSION
            else teaching_plan_v6
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v6.VERSION
            else teaching_plan_v5
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v5.VERSION
            else teaching_plan_v4
            if distributed_coverage and generation_policy.get("version") == teaching_plan_v4.VERSION
            else teaching_plan_v3
            if distributed_coverage
            else teaching_plan_v2
        )
        active_coverage = (
            coverage_v4
            if distributed_coverage
            and req.command.get("source_relation_policy")
            in {"source_relation_contract_v1", "source_relation_contract_v2"}
            else coverage_v3
            if distributed_coverage
            else coverage_v2
        )
        frozen_coverage_query_policy = req.command.get("coverage_query_policy")
        if frozen_coverage_query_policy is not None:
            frozen_coverage_query_policy = validate_coverage_query_policy(
                frozen_coverage_query_policy,
                base_version=base_version_for_source_relation(
                    req.command.get("source_relation_policy")
                ),
            )
            active_coverage = resolve_coverage(
                frozen_coverage_query_policy,
                active_coverage,
                mode=req.mode,
                condition=req.command.get("condition", "E1"),
                answer_mode=answer_mode,
                enhancement_version=req.command.get("enhancement_version"),
                reliability_policy=req.command.get("reliability_policy"),
                generation_policy=generation_policy,
            )
        if (
            current_core
            and understanding
            and understanding["rewrite_audit"]["fallback_to_original"]
        ):
            prepared = {
                **prepared,
                "standalone_query": understanding["standalone_query"],
                "fallback_reason": "critical_condition_preserved",
            }
        planning_started = time.perf_counter()
        progress_plan = (
            (active_teaching_plan.build_teaching_plan if current_core else build_teaching_plan)(
                question,
                teaching_context,
                understanding,
                policy=generation_policy,
                answer_mode=answer_mode,
            )
            if generation_policy
            and req.command.get("reliability_policy")
            in {"evidence_reliability_v4", "evidence_reliability_v5"}
            else None
        )
        planning_ms = (time.perf_counter() - planning_started) * 1000
        context_coverage = None
        query_preparation_ms = (time.perf_counter() - query_started) * 1000
        retrieval_ms = 0.0
        retrieval_execution = {
            "policy": None,
            "scope": "stored legacy or benchmark retrieval configuration",
        }
        evidence = []
        candidates = []
        inherited_trace = None
        strategy = evidence_strategy(question, prepared)
        if reading_context and reading_context.get("selected_chunk_ids"):
            from app.modules.learning_product.library import selected_reading_evidence

            candidates = selected_reading_evidence(db, db.get(User, req.owner_id), reading_context)
            strategy = "retrieve_and_reuse"
        if answer_mode == "general_knowledge" and req.mode == "interactive_chat":
            strategy = "general_knowledge_no_textbook_retrieval"
        if (
            prepared
            and answer_mode == "textbook"
            and strategy in ("reuse_only", "retrieve_and_reuse")
            and prepared["topic_relation"] == "same_topic"
            and prepared["referenced_message_ids"]
            and not prepared["needs_clarification"]
        ):
            # Reuse the answer paired with the resolved user turn, never simply
            # the last answer in a history that may contain another topic.
            referenced = set(prepared["referenced_message_ids"])
            old_id = None
            for index, prior in enumerate(history[:-1]):
                if prior["role"] == "user" and prior["message_id"] in referenced:
                    following = history[index + 1]
                    if following["role"] == "assistant":
                        old_id = following.get("answer_id")
            if old_id:
                old_answer = db.get(Answer, old_id)
                for item in db.scalars(
                    select(Evidence)
                    .where(Evidence.answer_id == old_id)
                    .order_by(Evidence.evidence_id)
                ):
                    doc = db.get(Document, item.document_id)
                    cited_ids = set(old_answer.response.get("citations", []))
                    if (
                        (allowed_chunk_ids is None or item.payload["chunk_id"] in allowed_chunk_ids)
                        and item.evidence_id in cited_ids
                        and (selection_policy or (doc and doc.active and not doc.revoked))
                    ):
                        candidates.append(
                            {
                                **item.payload,
                                "inherited_from": {
                                    "request_id": old_answer.request_id,
                                    "evidence_id": item.evidence_id,
                                },
                            }
                        )
        if selection_policy:
            candidates, inherited_trace = inherited_candidates(db, req.release_id, candidates)
        condition = req.command.get("condition", "E1")
        req.trace = {
            **req.trace,
            "prepared_query": prepared,
            "understanding": understanding,
            "evidence_strategy": strategy,
            "answer_mode": answer_mode,
            **(
                {
                    "reading_context": {
                        key: value
                        for key, value in reading_context.items()
                        if key not in {"allowed_chunk_ids", "selected_chunk_ids"}
                    },
                    "reading_scope_chunk_count": len(allowed_chunk_ids or []),
                }
                if reading_context
                else {}
            ),
            **(
                {"generation_policy": generation_policy, "progress_plan": progress_plan}
                if progress_plan
                else {}
            ),
            "source_provenance": "benchmark_protocol"
            if req.mode != "interactive_chat"
            else "model_general_knowledge_unverified"
            if answer_mode == "general_knowledge"
            else "textbook_evidence",
            "retrieval_execution": {**retrieval_execution, "inherited_evidence": inherited_trace}
            if inherited_trace is not None
            else retrieval_execution,
        }
        # Preparing inputs may invoke local embedding/reranker models. Release
        # the job lock before those calls so Stop remains immediately usable.
        db.commit()
        if (
            condition != "E0"
            and answer_mode == "textbook"
            and req.release_id
            and (not candidates or strategy == "retrieve_and_reuse")
            and not (
                selection_policy
                and strategy == "reuse_only"
                and inherited_trace["available_count"]
                and not candidates
            )
            and not (
                prepared and (prepared["needs_clarification"] or prepared["intent"] == "social")
            )
        ):
            query = prepared["standalone_query"] if prepared else question
            retrieval_started = time.perf_counter()
            frozen_policy = (
                req.command.get("retrieval_policy") if req.mode == "interactive_chat" else None
            )
            requested_device = (
                req.command.get("local_model_device", "recorded")
                if req.mode == "interactive_chat"
                else "recorded"
            )
            benchmark_query_runtime = None
            if req.mode in {"benchmark_openqa", "benchmark_mcq"}:
                from generation import benchmark_query_runtime_v1 as benchmark_runtime

                benchmark_query_runtime = req.command.get(benchmark_runtime.COMMAND_FIELD)
                requested_device = benchmark_runtime.requested_device(req.command)
            runtime_options = {}
            release = db.get(CorpusRelease, req.release_id)
            needs_learned_device = bool(frozen_policy) or (
                release and release.configuration.get("embedding_provider") == "e5"
            )
            if requested_device != "recorded" and (
                needs_learned_device or requested_device == "cpu"
            ):
                try:
                    runtime_options["runtime_device"] = resolve_device(requested_device)
                except (ValueError, RuntimeError) as exc:
                    raise AppError("SOURCE_UNAVAILABLE", detail=str(exc)) from exc
            req.trace = {
                **req.trace,
                "local_model_execution": {
                    "requested_device": requested_device,
                    "resolved_device": runtime_options.get("runtime_device"),
                    "scope": "query embedding; frozen benchmark runtime V1; corpus unchanged"
                    if benchmark_query_runtime is not None
                    else "query embedding and interactive reranking; corpus unchanged",
                    **(
                        {"benchmark_query_runtime_policy": benchmark_query_runtime}
                        if benchmark_query_runtime is not None
                        else {}
                    ),
                },
            }
            db.commit()
            retrieval_trace = {}
            cache_options = (
                {"cache_scope": req.owner_id, "execution_trace": retrieval_trace}
                if req.command.get("retrieval_optimization") == "validated_release_cache_v1"
                else {}
            )
            retrieved = retrieve(
                db,
                query or question,
                req.release_id,
                variant=frozen_policy["retriever"]
                if frozen_policy
                else req.command.get("retriever"),
                top_k=frozen_policy["candidate_count"]
                if frozen_policy
                else req.command.get("top_k"),
                **runtime_options,
                **cache_options,
                **scope_options,
            )
            merge_trace = None
            if selection_policy:
                retrieved, merge_trace = merge_candidates(retrieved, candidates, selection_policy)
            if frozen_policy:
                try:
                    retrieved, retrieval_execution = rerank_candidates(
                        query or question, retrieved, frozen_policy, **runtime_options
                    )
                except (ValueError, RuntimeError, OSError, ImportError) as exc:
                    raise AppError(
                        "SOURCE_UNAVAILABLE",
                        detail="The frozen local reranker or its input is unavailable. No fallback was substituted.",
                    ) from exc
            elif selection_policy and candidates:
                retrieved = (
                    bm25(query or question, retrieved, k=len(retrieved)) if retrieved else []
                )
                retrieval_execution = {
                    "policy": selection_policy,
                    "scope": "current-query BM25 over bounded union; no learned reranker configured",
                }
            if merge_trace is not None:
                retrieval_execution["candidate_merge"] = merge_trace
                inherited_trace["rescored_chunk_ids"] = [
                    row["chunk_id"] for row in retrieved if row.get("inherited_from")
                ]
                # Old scores never bypass the current-query ranking/screening.
                candidates = []
            if cache_options:
                retrieval_execution["retrieval_stages"] = retrieval_trace
            whole_rows = list(retrieved)
            relevance_policy = (
                req.command.get("relevance_policy") if req.mode == "interactive_chat" else None
            )
            if relevance_policy:
                retrieved, relevance_trace = screen(query or question, retrieved, relevance_policy)
                # Legacy commands require fresh retrieval. New commands use
                # the rescored union, so prior citations never bypass screening.
                relevance_trace["unconfirmed_inherited_chunk_ids"] = [
                    chunk_id
                    for chunk_id in (
                        inherited_trace["eligible_chunk_ids"]
                        if inherited_trace is not None
                        else [item["chunk_id"] for item in candidates]
                    )
                    if chunk_id not in {row["chunk_id"] for row in retrieved}
                ]
                candidates = []
                retrieval_execution["relevance_gate"] = relevance_trace
                # Optional shadow capture; never consumes model/repair work.
                if decision_shadow_binding is not None:
                    try:
                        if (
                            decision_shadow_binding.enabled is True
                            and decision_shadow_binding.observer.enabled is True
                        ):
                            from generation.decision_shadow_hook_v1 import TrustedHookBinding

                            if type(decision_shadow_binding) is TrustedHookBinding:
                                decision_shadow_binding.try_record_a3()
                    except Exception:
                        pass
            fallback_policy = (
                req.command.get("facet_fallback_policy")
                if req.mode == "interactive_chat"
                and not generation_policy
                and prepared["preparation_version"]
                in {
                    "conversation_preparer_v9",
                    "conversation_preparer_v10",
                    "conversation_preparer_v11",
                    "conversation_preparer_v12",
                    "conversation_preparer_v13",
                }
                else None
            )
            if fallback_policy:
                fallback_started = time.perf_counter()

                def checkpoint(phase, fallback_trace):
                    # Shared elapsed budget includes the original screen and
                    # every local fallback stage. No lock spans model execution.
                    state = db.execute(
                        select(Job.state, Job.execution_token).where(Job.id == job_id)
                    ).one()
                    if state.state != "running" or state.execution_token != token:
                        db.rollback()
                        raise ExecutionCancelled()
                    active = initial_active_seconds + time.perf_counter() - start
                    current_budget = RequestBudget.from_dict(req.budget)
                    current_budget.active_seconds = active
                    req.budget = current_budget.to_dict()
                    fallback_trace["elapsed_ms"] = round(
                        (time.perf_counter() - fallback_started) * 1000, 3
                    )
                    fallback_trace["stage"] = phase
                    exhausted = active >= current_budget.max_active_seconds
                    if exhausted:
                        fallback_trace["reason"] = "budget_exhausted"
                    req.trace = {
                        **req.trace,
                        "retrieval_execution": {
                            **retrieval_execution,
                            "facet_fallback": fallback_trace,
                        },
                    }
                    db.commit()
                    if exhausted:
                        raise AppError(
                            "BUDGET_EXHAUSTED",
                            detail="The frozen active-time budget expired during local facet retrieval.",
                        )

                def retrieve_facet(facet_query, limit):
                    facet_trace = {}
                    facet_options = (
                        {"cache_scope": req.owner_id, "execution_trace": facet_trace}
                        if cache_options
                        else {}
                    )
                    rows = retrieve(
                        db,
                        facet_query,
                        req.release_id,
                        variant=frozen_policy["retriever"],
                        top_k=limit,
                        **runtime_options,
                        **facet_options,
                        **scope_options,
                    )
                    if facet_options:
                        retrieval_trace.setdefault("facet_retrievals", []).append(facet_trace)
                    return rows

                def rerank_facet(facet_query, rows):
                    try:
                        ranked, _ = rerank_candidates(
                            facet_query, rows, frozen_policy, **runtime_options
                        )
                        return ranked
                    except (ValueError, RuntimeError, OSError, ImportError) as exc:
                        raise AppError(
                            "SOURCE_UNAVAILABLE",
                            detail="The frozen local facet reranker or its input is unavailable. No substitute model was used.",
                        ) from exc

                retrieved, fallback_trace, final_selection = facet_fallback(
                    understanding,
                    whole_rows,
                    retrieved,
                    fallback_policy,
                    frozen_policy,
                    relevance_policy,
                    retrieve_facet=retrieve_facet,
                    rerank_facet=rerank_facet,
                    checkpoint=checkpoint,
                )
                fallback_trace["elapsed_ms"] = round(
                    (time.perf_counter() - fallback_started) * 1000, 3
                )
                retrieval_execution["facet_fallback"] = fallback_trace
                retrieval_execution["final_selection"] = final_selection
            if generation_policy and progress_plan:
                supplement_started = time.perf_counter()

                def coverage_checkpoint(phase, supplement_trace):
                    state = db.execute(
                        select(Job.state, Job.execution_token).where(Job.id == job_id)
                    ).one()
                    if state.state != "running" or state.execution_token != token:
                        db.rollback()
                        raise ExecutionCancelled()
                    active = initial_active_seconds + time.perf_counter() - start
                    current_budget = RequestBudget.from_dict(req.budget)
                    current_budget.active_seconds = active
                    req.budget = current_budget.to_dict()
                    supplement_trace["elapsed_ms"] = round(
                        (time.perf_counter() - supplement_started) * 1000, 3
                    )
                    supplement_trace["stage"] = phase
                    exhausted = active >= current_budget.max_active_seconds
                    if exhausted:
                        supplement_trace["reason"] = "budget_exhausted"
                    req.trace = {
                        **req.trace,
                        "retrieval_execution": {
                            **retrieval_execution,
                            "coverage_supplement": supplement_trace,
                        },
                    }
                    db.commit()
                    if exhausted:
                        raise AppError(
                            "BUDGET_EXHAUSTED",
                            detail="The frozen active-time budget expired during targeted context retrieval.",
                        )

                def retrieve_requirement(target_query, limit):
                    target_trace = {}
                    rows = retrieve(
                        db,
                        target_query,
                        req.release_id,
                        variant=frozen_policy["retriever"]
                        if frozen_policy
                        else req.command.get("retriever"),
                        top_k=limit,
                        **runtime_options,
                        **scope_options,
                        **(
                            {"cache_scope": req.owner_id, "execution_trace": target_trace}
                            if cache_options
                            else {}
                        ),
                    )
                    if cache_options:
                        retrieval_trace["coverage_retrieval"] = target_trace
                    return rows

                def rank_requirement(target_query, rows):
                    if not frozen_policy:
                        return rows
                    try:
                        ranked, _ = rerank_candidates(
                            target_query, rows, frozen_policy, **runtime_options
                        )
                        return ranked
                    except (ValueError, RuntimeError, OSError, ImportError) as exc:
                        raise AppError(
                            "SOURCE_UNAVAILABLE",
                            detail="The frozen targeted context reranker is unavailable.",
                        ) from exc

                def screen_requirement(target_query, rows):
                    return (
                        screen(target_query, rows, relevance_policy)
                        if relevance_policy
                        else (rows, {"reason": "screening_disabled"})
                    )

                retrieved, context_coverage, supplement_trace = (
                    active_coverage.supplement_once if current_core else supplement_once
                )(
                    query or question,
                    retrieved,
                    understanding,
                    generation_policy,
                    retrieve=retrieve_requirement,
                    rerank=rank_requirement,
                    screen=screen_requirement,
                    checkpoint=coverage_checkpoint,
                )
                supplement_trace["elapsed_ms"] = round(
                    (time.perf_counter() - supplement_started) * 1000, 3
                )
                retrieval_execution["coverage_supplement"] = supplement_trace
            retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
            fresh_ids = {item["chunk_id"] for item in retrieved}
            candidates = retrieved + [
                item for item in candidates if item["chunk_id"] not in fresh_ids
            ]
        for i, item in enumerate(candidates, 1):
            evidence.append(
                {
                    k: v
                    for k, v in {
                        **item,
                        "evidence_id": f"ev_{i:03}",
                        "context_order": i,
                        "inherited_from": item.get("inherited_from"),
                    }.items()
                    if k in EvidenceSnapshot.model_fields
                }
            )
        if generation_policy and answer_mode == "textbook":
            context_coverage = (
                active_coverage.assess_evidence_coverage
                if current_core
                else assess_evidence_coverage
            )((prepared or {}).get("standalone_query") or question, evidence, understanding)
        if (
            req.regeneration_of
            and answer_mode == "textbook"
            and not evidence
            and prepared
            and prepared["intent"] not in ("social", "clarification")
        ):
            raise AppError(
                "SOURCE_UNAVAILABLE",
                detail="The original question no longer has available supporting sources.",
            )
        memory_context = validate_learning_context(db, req, lock=True)
        lock_request_session(db, req)
        job = db.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job.execution_token != token or job.state != "running":
            raise ExecutionCancelled()
        input_preparation_ms = (time.perf_counter() - start) * 1000
        stage_timing = {
            "preparation_ms": round(max(0, input_preparation_ms - retrieval_ms), 3),
            "query_preparation_ms": round(query_preparation_ms, 3),
            "retrieval_ms": round(retrieval_ms, 3),
            **({"teaching_plan_ms": round(planning_ms, 3)} if progress_plan else {}),
        }
        if "submission_to_worker_start_ms" in req.trace:
            stage_timing["submission_to_worker_start_ms"] = req.trace[
                "submission_to_worker_start_ms"
            ]
        req.trace = {
            **req.trace,
            "prepared_query": prepared,
            "understanding": understanding,
            **(
                {"progress_plan": progress_plan, "context_coverage": context_coverage}
                if progress_plan
                else {}
            ),
            "evidence_strategy": strategy,
            "retrieval_execution": retrieval_execution,
            "retrieval_candidates": candidates,
            "evidence_selection": {
                "candidate_count": len(candidates),
                "candidate_chunk_ids": [item["chunk_id"] for item in candidates],
                "submitted_count": 0,
                "submitted_evidence_ids": [],
                "submitted_chunk_ids": [],
                "cited_count": 0,
                "cited_evidence_ids": [],
                "excluded_evidence": [],
            },
            "preparation_ms": round(input_preparation_ms, 3),
            "stage_timing": stage_timing,
        }
        if inherited_trace is not None:
            req.trace = {
                **req.trace,
                "retrieval_execution": {
                    **retrieval_execution,
                    "inherited_evidence": inherited_trace,
                },
            }
        budget = RequestBudget.from_dict(req.budget)
        budget.active_seconds = initial_active_seconds + time.perf_counter() - start
        req.budget = budget.to_dict()
        job.stage = "generating"
        from app.modules.learning_state.sources import source_map

        mapping = (
            source_map(db, req, evidence)
            if req.command.get("enhancement_version") and evidence
            else {}
        )
        generation_request = GenerationRequest(
            request_id=req.id,
            mode=req.mode,
            condition=condition,
            question=question,
            question_id=req.command.get("question_id", ""),
            options=req.command.get("options"),
            evidence=evidence,
            history=history,
            summary=context.get("summary_text"),
            profile=policy,
            prepared_query=prepared,
            understanding=understanding,
            config=ModelConfig.from_dict(req.command["model_config"]),
            answer_mode=answer_mode,
            enhancement_version=req.command.get("enhancement_version"),
            attribution_strategy=req.command.get("attribution_strategy", "posthoc_spans"),
            teaching_condition=req.command.get("teaching_condition", "T2"),
            teaching_context=teaching_context,
            memory_context=memory_context,
            source_map=mapping,
            checker_config=ModelConfig.from_dict(req.command["checker_config"])
            if req.command.get("checker_config")
            else None,
            reliability_policy=req.command.get("reliability_policy", "legacy_joint_v1"),
            generation_context_policy=req.command.get("generation_context_policy"),
            source_block_policy=req.command.get("source_block_policy", "legacy_source_blocks_v1"),
            repair_policy=req.command.get("repair_policy"),
            source_relation_policy=req.command.get("source_relation_policy"),
            joint_checker_policy=req.command.get("joint_checker_policy", "typed_joint_v5"),
            provider_output_policy=req.command.get("provider_output_policy", "strict_v1"),
            generation_policy=generation_policy,
            checker_payload_policy=req.command.get(
                "checker_payload_policy", "legacy_fragment_table_v1"
            ),
            teaching_plan=progress_plan,
            evidence_coverage=context_coverage,
            coverage_query_policy=frozen_coverage_query_policy,
            reading_context=reading_context,
        )
        db.commit()

    def attempt_event(event):
        with factory() as db:
            request_row = db.get(AnswerRequest, generation_request.request_id)
            validate_learning_context(db, request_row, lock=True)
            lock_request_session(db, request_row)
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.execution_token != token or job.state != "running":
                raise ExecutionCancelled()
            req = db.get(AnswerRequest, job.request_id)
            req.budget = event.get("budget", req.budget)
            if event.get("stage") in {
                "generation",
                "joint_check",
                "semantic_repair",
                "joint_recheck",
                "generation_format_repair",
                "checker_contract_repair",
            }:
                job.stage = event["stage"]
            job.updated_at = utcnow()
            count = db.scalar(
                select(func.count()).select_from(Attempt).where(Attempt.job_id == job_id)
            )
            safe_event = dict(event)
            if generation_request.memory_context:
                for field in (
                    "messages",
                    "model_messages",
                    "prompt",
                    "raw_response",
                    "raw_text",
                    "response",
                ):
                    safe_event.pop(field, None)
                if isinstance(safe_event.get("diagnostic"), dict):
                    safe_event["diagnostic"] = {
                        **safe_event["diagnostic"],
                        "message": None,
                        "message_redacted": True,
                    }
                safe_event["memory_entry_versions"] = [
                    {"id": e["id"], "version": e["version"]}
                    for e in generation_request.memory_context.get("entries", [])
                ]
            db.add(Attempt(job_id=job_id, sequence=count + 1, payload=safe_event))
            db.commit()

    from app.modules.model_settings.service import resolve_secret

    with factory() as secret_db:
        api_key = resolve_secret(secret_db, settings, generation_request.config.configuration_id)
        checker_key = (
            resolve_secret(secret_db, settings, generation_request.checker_config.configuration_id)
            if generation_request.checker_config
            else None
        )
    generation_started = time.perf_counter()
    if generation_request.config.provider == "mock" and settings.mock_delay_seconds:
        time.sleep(settings.mock_delay_seconds)
    generation_service = None
    try:
        generation_service = GenerationService(api_key=api_key, checker_api_key=checker_key)
        if decision_shadow_binding is not None:
            try:
                if (
                    decision_shadow_binding.enabled is True
                    and decision_shadow_binding.observer.enabled is True
                ):
                    from generation.decision_shadow_hook_v1 import TrustedHookBinding

                    if type(decision_shadow_binding) is TrustedHookBinding:
                        generation_service.__dict__["_decision_shadow_binding"] = (
                            decision_shadow_binding
                        )
            except Exception:
                pass
        result = generation_service.generate(generation_request, budget, on_attempt=attempt_event)
    finally:
        if generation_service is not None:
            try:
                generation_service.__dict__.pop("_decision_shadow_binding", None)
            except Exception:
                pass
        generation_service = None
        api_key = None
        checker_key = None
    stage_timing["generation_wall_ms"] = round((time.perf_counter() - generation_started) * 1000, 3)
    with factory() as db:
        # All session mutations acquire session before job; match archive/delete
        # so simultaneous completion and cancellation cannot form a lock cycle.
        request_row = db.get(AnswerRequest, generation_request.request_id)
        validate_learning_context(db, request_row, lock=True)
        if request_row.session_id:
            db.scalar(
                select(ChatSession)
                .where(ChatSession.id == request_row.session_id)
                .with_for_update()
            )
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job.execution_token != token or job.state != "running":
            return
        req = db.get(AnswerRequest, job.request_id)
        validate_learning_context(db, req, lock=True)
        req.budget = result.budget
        req.trace = {
            **req.trace,
            "model_messages": safe_prompt_trace(result.messages, generation_request.memory_context),
            "stage_usage": result.stage_usage,
            "usage": result.usage,
            "token_budget": result.token_budget,
            **{
                key: result.token_budget[key]
                for key in (
                    "coverage_estimate",
                    "evidence_packing",
                    "citation_audit",
                    "teaching_plan",
                    "progress_plan",
                    "context_coverage",
                    "answer_completeness",
                    "claim_support",
                    "progress_display",
                )
                if key in result.token_budget
            },
            "evidence_selection": {
                "candidate_count": len(candidates),
                "candidate_chunk_ids": [item["chunk_id"] for item in candidates],
                "submitted_count": len(result.evidence),
                "submitted_evidence_ids": [item["evidence_id"] for item in result.evidence],
                "submitted_chunk_ids": [item["chunk_id"] for item in result.evidence],
                "cited_count": len((result.response or {}).get("citations", [])),
                "cited_evidence_ids": (result.response or {}).get("citations", []),
                "excluded_evidence": result.token_budget.get("excluded_evidence", []),
            },
            "response_origin": result.response_origin,
            "stage_timing": stage_timing,
        }
        if req.mode != "interactive_chat":
            from app.modules.experiment.bridge import validate_request_environment

            try:
                validate_request_environment(db, settings, req)
            except AppError as exc:
                fail_job(
                    db,
                    job,
                    {
                        "code": exc.code,
                        "message": exc.detail or "Frozen environment changed.",
                        "details": {},
                    },
                )
                db.commit()
                return
        from app.modules.learning_state.sources import persist_private_records

        if req.command.get("enhancement_version"):
            persist_private_records(db, req, result)
        if result.error:
            fail_job(db, job, result.error)
            db.commit()
            return
        if req.session_id:
            session = db.scalar(
                select(ChatSession).where(ChatSession.id == req.session_id).with_for_update()
            )
            if session.status != "active" or session.deleted_at:
                cancel_job(db, job)
                db.commit()
                return
        if (
            req.command.get("retrieval_optimization") == "validated_release_cache_v1"
            and db.bind.dialect.name == "postgresql"
        ):
            from app.modules.knowledge.cache import publication_fence

            publication_fence(db)
        for ev in result.evidence:
            doc = db.get(Document, ev["asset_id"], populate_existing=True)
            if not doc or not doc.active or doc.revoked:
                fail_job(
                    db,
                    job,
                    {
                        "code": "SOURCE_UNAVAILABLE",
                        "message": "A selected source became unavailable.",
                        "details": {},
                    },
                )
                db.commit()
                return
        if req.regeneration_of and result.response.get("response_type") == "refusal":
            fail_job(
                db,
                job,
                {
                    "code": "REGENERATION_FAILED",
                    "message": "A supported replacement could not be produced. Your previous answer is preserved.",
                    "details": {},
                },
            )
            db.commit()
            return
        publication_started = time.perf_counter()
        message = None
        if req.session_id:
            message = (
                db.get(Message, req.assistant_message_id) if req.assistant_message_id else None
            )
            if message is None:
                sequence = (
                    db.scalar(
                        select(func.max(Message.sequence)).where(
                            Message.session_id == req.session_id
                        )
                    )
                    or 0
                ) + 1
                message = Message(
                    session_id=req.session_id,
                    sequence=sequence,
                    role="assistant",
                    content=result.response["answer_text"],
                    state="completed",
                )
                db.add(message)
                db.flush()
            req.assistant_message_id = message.id
        answer = Answer(
            request_id=req.id,
            job_id=job.id,
            message_id=message.id if message else None,
            response_schema=req.response_schema,
            response=result.response,
            model_mode=result.model_mode,
            timing={
                **result.timing,
                **stage_timing,
                "total_ms": round((time.perf_counter() - start) * 1000, 3),
                "timing_scope": "worker_execution_before_answer_insert_v1",
            },
        )
        db.add(answer)
        db.flush()
        from app.modules.learning_state import sources, tasks

        sources.persist_result(db, req, answer, result)
        tasks.publish_task(db, req.command.get("teaching_context"), result=result)
        selected = {}
        for item in result.evidence:
            EvidenceSnapshot.model_validate(item)
            e = Evidence(
                answer_id=answer.id,
                evidence_id=item["evidence_id"],
                document_id=item["asset_id"],
                chunk_id=item["chunk_id"],
                payload=item,
            )
            db.add(e)
            db.flush()
            selected[item["evidence_id"]] = e.id
        for cid in result.response["citations"]:
            db.add(Citation(answer_id=answer.id, evidence_id=selected[cid]))
        if message:
            message.active_answer_id = answer.id
            message.content = result.response["answer_text"]
            message.state = "completed"
            message.request_id = req.id
            db.get(Message, req.user_message_id).state = "completed"
            if req.regeneration_of:
                db.execute(
                    update(SessionSummary)
                    .where(SessionSummary.session_id == req.session_id)
                    .values(invalidated=True)
                )
        req.state = (
            "refused"
            if result.response.get("response_type") == "refusal" or result.response.get("refused")
            else "clarification"
            if result.response.get("response_type") == "clarification"
            else "answered"
        )
        job.state = "succeeded"
        job.stage = "complete"
        job.answer_id = answer.id
        job.execution_token = None
        if req.command.get("reliability_policy") in {
            "evidence_reliability_v3",
            "evidence_reliability_v4",
            "evidence_reliability_v5",
        }:
            answer.timing = {
                **answer.timing,
                "publication_before_commit_ms": round(
                    (time.perf_counter() - publication_started) * 1000, 3
                ),
                "worker_before_commit_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        db.commit()


def fail_job(db, job, error):
    failed_stage = job.stage
    job.state = "failed"
    job.stage = "failed"
    job.error = {
        "code": error["code"],
        "message": error["message"],
        "details": error.get("details", {}),
    }
    job.execution_token = None
    if job.request_id:
        req = db.get(AnswerRequest, job.request_id)
        if req.command.get("reliability_policy") in {
            "evidence_reliability_v3",
            "evidence_reliability_v4",
            "evidence_reliability_v5",
        }:
            trace = {**req.trace, "failure_stage": failed_stage, "failed_at": utcnow().isoformat()}
            if trace.get("worker_started_at"):
                trace["worker_to_failure_ms"] = max(
                    0.0,
                    (utcnow() - datetime.fromisoformat(trace["worker_started_at"])).total_seconds()
                    * 1000,
                )
            req.trace = trace
        req.state = "error"
        if req.user_message_id and not req.regeneration_of:
            db.get(Message, req.user_message_id).state = "error"
