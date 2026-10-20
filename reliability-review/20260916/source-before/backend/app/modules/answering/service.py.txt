"""Shared durable answer execution with immutable inputs and tail-only revisions."""

from __future__ import annotations
import hashlib
import json
import time
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session, sessionmaker
from app.core.exceptions import AppError
from app.core.logging import trace_id_var
from app.db.base import new_uuid, utcnow
from app.modules.identity.models import User
from app.modules.identity import service as profiles
from app.modules.learning.models import ChatSession
from app.modules.answering.models import *
from app.modules.knowledge.models import ActiveCorpus, Document, CorpusRelease
from app.modules.knowledge.service import digest, retrieve
from contracts.models import ChatMessageCreate, ChatResponseV1, MCQResponseV1, EvidenceSnapshot
from conversation.context import select_context
from conversation.query import prepare_query, evidence_strategy
from personalisation.compiler import compile_profile
from generation.types import GenerationRequest, ModelConfig, RequestBudget
from generation.service import GenerationService
from generation.token_counting import TokenCounter
from retrieval.chat import load_policy, rerank_candidates, policy_hash

ACTIVE = ("queued", "running", "retry_wait")


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
    session = owned_session(db, session_id, actor, lock=True)
    route = f"/sessions/{session_id}/messages"
    prior = idempotent(db, actor.id, route, key, body.model_dump())
    if prior:
        return receipt(db, prior)
    if session.status != "active":
        raise AppError("CONFLICT", detail="Restore the conversation before sending a message.")
    if active_job(db, session_id):
        raise AppError("SESSION_BUSY")
    from app.modules.model_settings.service import resolve_active_model_config

    selected_config = resolve_active_model_config(db, settings, actor.workspace_id)
    selected_config = selected_config or ModelConfig.from_dict(model_config(settings))
    try:
        selected_config.validate()
        counter = TokenCounter(selected_config)
    except (ValueError, TypeError) as exc:
        raise AppError(
            "MODEL_UNAVAILABLE",
            detail="The configured model or its required local tokenizer is unavailable. Check the saved model settings.",
        ) from exc
    try:
        retrieval_policy = load_policy(getattr(settings, "chat_retrieval_config", None))
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
    pointer = db.get(ActiveCorpus, 1)
    req = AnswerRequest(
        owner_id=actor.id,
        route=route,
        idempotency_key=key,
        body_hash=digest(body.model_dump()),
        mode="interactive_chat",
        response_schema="chat_response_v1",
        session_id=session_id,
        user_message_id=message.id,
        context_snapshot_id=cs.id,
        profile_snapshot_id=ps.id,
        release_id=pointer.release_id if pointer else None,
        command={
            "question": body.content,
            "model_config": selected_config.to_dict(),
            "condition": "E1",
            "retrieval_policy": retrieval_policy,
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
    }
    db.add(req)
    db.flush()
    message.request_id = req.id
    job = Job(request_id=req.id, owner_id=actor.id)
    db.add(job)
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
    if req.session_id:
        owned_session(db, req.session_id, actor, True)
    if not key or len(key) > 128:
        raise AppError("VALIDATION_FAILED")
    previous = db.scalar(
        select(Job).where(Job.request_id == req.id, Job.payload["retry_key"].as_string() == key)
    )
    if previous:
        return receipt(db, req, previous)
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
    owned_session(db, old.session_id, actor, True)
    route = f"/answers/{answer_id}/regenerate"
    prior = idempotent(db, actor.id, route, key, {})
    if prior:
        return receipt(db, prior)
    if not can_regenerate(db, answer):
        raise AppError("REGENERATE_NOT_ALLOWED")
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
        command=dict(old.command),
        budget=fresh_budget,
    )
    db.add(req)
    db.flush()
    job = Job(request_id=req.id, owner_id=actor.id)
    db.add(job)
    db.commit()
    return receipt(db, req, job)


def cancel_job(db, job):
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
        "response": answer.response,
        "evidence": evidence,
        "profile_snapshot": db.get(Snapshot, req.profile_snapshot_id).payload
        if req.profile_snapshot_id
        else None,
        "conversation_snapshot": db.get(Snapshot, req.context_snapshot_id).payload
        if req.context_snapshot_id
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


def execute_answer(engine, settings, job_id, token):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    start = time.perf_counter()
    with factory() as db:
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        req = db.get(AnswerRequest, job.request_id)
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
        query_started = time.perf_counter()
        prepared = (
            prepare_query(question, history, context.get("summary_text")).model_dump()
            if req.mode == "interactive_chat"
            else None
        )
        query_preparation_ms = (time.perf_counter() - query_started) * 1000
        retrieval_ms = 0.0
        retrieval_execution = {
            "policy": None,
            "scope": "stored legacy or benchmark retrieval configuration",
        }
        evidence = []
        candidates = []
        strategy = evidence_strategy(question, prepared)
        if (
            prepared
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
                    if doc and doc.active and not doc.revoked and item.evidence_id in cited_ids:
                        candidates.append(
                            {
                                **item.payload,
                                "inherited_from": {
                                    "request_id": old_answer.request_id,
                                    "evidence_id": item.evidence_id,
                                },
                            }
                        )
        condition = req.command.get("condition", "E1")
        # Preparing inputs may invoke local embedding/reranker models. Release
        # the job lock before those calls so Stop remains immediately usable.
        db.commit()
        if (
            condition != "E0"
            and req.release_id
            and (not candidates or strategy == "retrieve_and_reuse")
            and not (
                prepared and (prepared["needs_clarification"] or prepared["intent"] == "social")
            )
        ):
            query = prepared["standalone_query"] if prepared else question
            retrieval_started = time.perf_counter()
            frozen_policy = (
                req.command.get("retrieval_policy") if req.mode == "interactive_chat" else None
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
            )
            if frozen_policy:
                try:
                    retrieved, retrieval_execution = rerank_candidates(
                        query or question, retrieved, frozen_policy
                    )
                except (ValueError, RuntimeError, OSError, ImportError) as exc:
                    raise AppError(
                        "SOURCE_UNAVAILABLE",
                        detail="The frozen local reranker or its input is unavailable. No fallback was substituted.",
                    ) from exc
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
        if (
            req.regeneration_of
            and not evidence
            and prepared
            and prepared["intent"] not in ("social", "clarification")
        ):
            raise AppError(
                "SOURCE_UNAVAILABLE",
                detail="The original question no longer has available supporting sources.",
            )
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
        }
        req.trace = {
            **req.trace,
            "prepared_query": prepared,
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
        budget = RequestBudget.from_dict(req.budget)
        budget.active_seconds += time.perf_counter() - start
        req.budget = budget.to_dict()
        job.stage = "generating"
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
            config=ModelConfig.from_dict(req.command["model_config"]),
        )
        db.commit()

    def attempt_event(event):
        with factory() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.execution_token != token or job.state != "running":
                raise ExecutionCancelled()
            req = db.get(AnswerRequest, job.request_id)
            req.budget = event.get("budget", req.budget)
            job.updated_at = utcnow()
            count = db.scalar(
                select(func.count()).select_from(Attempt).where(Attempt.job_id == job_id)
            )
            db.add(Attempt(job_id=job_id, sequence=count + 1, payload=event))
            db.commit()

    from app.modules.model_settings.service import resolve_secret

    with factory() as secret_db:
        api_key = resolve_secret(secret_db, settings, generation_request.config.configuration_id)
    generation_started = time.perf_counter()
    if generation_request.config.provider == "mock" and settings.mock_delay_seconds:
        time.sleep(settings.mock_delay_seconds)
    try:
        result = GenerationService(api_key=api_key).generate(
            generation_request, budget, on_attempt=attempt_event
        )
    finally:
        api_key = None
    stage_timing["generation_wall_ms"] = round((time.perf_counter() - generation_started) * 1000, 3)
    with factory() as db:
        # All session mutations acquire session before job; match archive/delete
        # so simultaneous completion and cancellation cannot form a lock cycle.
        request_row = db.get(AnswerRequest, generation_request.request_id)
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
        req.budget = result.budget
        req.trace = {
            **req.trace,
            "model_messages": result.messages,
            "usage": result.usage,
            "token_budget": result.token_budget,
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
        for ev in result.evidence:
            doc = db.get(Document, ev["asset_id"])
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
        db.commit()


def fail_job(db, job, error):
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
        req.state = "error"
        if req.user_message_id and not req.regeneration_of:
            db.get(Message, req.user_message_id).state = "error"
