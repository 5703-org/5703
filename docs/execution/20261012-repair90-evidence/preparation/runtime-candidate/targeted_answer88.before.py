"""Finite fixture dispatch of one fresh native answer through the normal executor.

This module has no CLI, app imports, environment lookup, or runtime work on import.
The parent owns credential access and transport/cost controls. This library never
scans a worker queue, recovers stale jobs, or retries a request.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from uuid import UUID

MAIN = Path("E:/5703/learning-assistant")
WORKSPACE_ID = "5ef0e22c-45f2-4c72-9ff8-acfee1e6b655"
DATABASE_NAME = "cs30_week10_pair_b_20261009_01"
RELEASE_ID = "4f11bd70-a486-4d16-b216-78cfe499530a"
SOURCE_PATHS = frozenset({
    "generation/service.py", "generation/single_selection_findings_v2.py",
    "generation/adapters.py", "generation/lossless_unit_findings_v1.py",
    "generation/network_policy.py", "generation/openrouter_routes.py",
    "generation/prompts/source_relation_check_v2.txt",
    "generation/prompts/source_relation_generation_v2.txt",
    "generation/providers.py", "generation/types.py", "personalisation/compiler.py",
    "generation/checked.py", "backend/app/core/config.py",
    "backend/app/modules/answering/service.py", "conversation/query_v23.py",
    "conversation/practice_context.py",
})
V2_SOURCE_PATHS = SOURCE_PATHS | {"generation/service.py", "generation/single_selection_findings_v2.py"}


def selected_source_paths(scope):
    """Require the same sixteen-file Main boundary for either explicit output policy."""
    settings = scope.get("expected_settings")
    require(type(settings) is dict, "PHASE88_CHECKER_OUTPUT_VARIANT_CHANGED")
    policy = settings.get("chat_checker_output_policy")
    variant = scope.get("phase88_checker_output_variant")
    if policy == "single_selection_findings_v2":
        require(scope.get("case_id") in {'case10c', 'case07', 'case03r', 'case03', 'case08', 'case05', 'case09', 'case01', 'case06', 'case04r', 'case10b', 'case05r', 'case04', 'case01r', 'case10'}
                and variant == "single_selection_findings_v2"
                and scope.get("phase88_v2_execution_authorized") is True,
                "EXPLICIT_PHASE88_V2_CASE_REQUIRED")
        return V2_SOURCE_PATHS
    require(policy == "lossless_unit_findings_v1" and variant in (None, "lossless_unit_findings_v1")
            and scope.get("phase88_v2_execution_authorized") in (None, False),
            "PHASE88_CHECKER_OUTPUT_VARIANT_CHANGED")
    return SOURCE_PATHS


PUBLIC_SETTINGS = frozenset({
    "env", "model_mode", "llm_provider", "llm_model", "llm_api_base",
    "embedding_provider", "embedding_model", "embedding_revision", "embedding_dimension",
    "chat_retrieval_config", "chat_relevance_gate", "chat_retrieval_cache",
    "chat_source_relation_policy", "chat_checker_schema_policy", "chat_checker_payload_policy", "chat_checker_output_policy", "chat_coverage_query_policy",
    "chat_source_block_policy", "chat_provider_output_policy", "chat_joint_checker_policy",
    "chat_query_preparation_policy", "memory_semantic_policy_file", "local_model_device",
    "request_timeout_seconds", "provider_timeout_seconds", "max_provider_calls",
    "model_window_tokens", "model_output_tokens", "worker_prewarm_retrieval_cache",
    "seed_demo_users", "mock_delay_seconds", "api_v1_prefix", "storage_root",
    "visual_catalog_staging_root", "cors_origins", "feature_flags",
})
REQUIRED_SETTINGS = frozenset({
    "env", "model_mode", "llm_provider", "embedding_provider", "chat_retrieval_config",
    "chat_joint_checker_policy", "chat_source_relation_policy", "chat_checker_schema_policy",
    "chat_query_preparation_policy", "request_timeout_seconds", "max_provider_calls", "chat_checker_output_policy", "chat_checker_payload_policy",
    "local_model_device", "worker_prewarm_retrieval_cache", "seed_demo_users",
})


class TargetGuardError(RuntimeError):
    """A public finite code only; no URL, credential, row content, or raw exception."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise TargetGuardError(code)


def canonical(value):
    """Type-sensitive public binding comparison; rejects NaN and non-JSON values."""
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise TargetGuardError("PUBLIC_BINDING_NOT_FINITE_JSON") from None


def utc(value):
    try:
        parsed = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise TargetGuardError("CREATION_TIME_NOT_BOUND") from None
    require(parsed.tzinfo is not None, "CREATION_TIME_NOT_UTC_BOUND")
    return parsed.astimezone(dt.timezone.utc)


def uuid(value):
    try:
        require(type(value) is str and str(UUID(value)) == value, "TARGET_ID_NOT_CANONICAL_UUID")
    except ValueError:
        raise TargetGuardError("TARGET_ID_NOT_CANONICAL_UUID") from None
    return value


def verify_preparation_pins(scope):
    """Historical fresh12 smoke descriptors are never eligible in the new cohort."""
    require(scope.get("case_id") in {'case10c', 'case07', 'case03r', 'case03', 'case08', 'case05', 'case09', 'case01', 'case06', 'case04r', 'case10b', 'case05r', 'case04', 'case01r', 'case10'}
            and scope.get("fresh_preparation_source_pins") is None
            and scope.get("fresh_validation_descriptor_sha256") is None,
            "OLD_SPECIAL_METADATA_FORBIDDEN_IN_DEV89")


def verify_source_pins(scope):
    """Verify the exact Main allowlist bound by the immutable case scope pin."""
    verify_preparation_pins(scope)
    source_paths = selected_source_paths(scope)
    supplied = scope.get("source_pins")
    require(type(supplied) is list, "SOURCE_PIN_BINDING_REQUIRED")
    index = {}
    for row in supplied:
        require(type(row) is dict, "SOURCE_PIN_BINDING_INVALID")
        name = row.get("path")
        require(type(name) is str, "SOURCE_PIN_BINDING_INVALID")
        normalized = name.replace("\\", "/")
        prefix = str(MAIN).replace("\\", "/") + "/"
        require(normalized.casefold().startswith(prefix.casefold()), "MAIN_PUBLIC_PIN_REDIRECTED")
        name = normalized[len(prefix):]
        require(name in source_paths and name not in index, "SOURCE_PIN_BINDING_INVALID")
        path = MAIN / name
        require(not path.is_symlink(), "SOURCE_PATH_REDIRECTED")
        try:
            relative = path.resolve().relative_to(MAIN.resolve()).as_posix()
        except (OSError, ValueError):
            raise TargetGuardError("MAIN_PUBLIC_PIN_REDIRECTED") from None
        require(relative == name, "MAIN_PUBLIC_PIN_REDIRECTED")
        expected_bytes, expected_sha = row.get("bytes"), row.get("sha256")
        require(
            type(expected_bytes) is int and expected_bytes > 0
            and type(expected_sha) is str and len(expected_sha) == 64
            and all(character in "0123456789abcdef" for character in expected_sha),
            "SOURCE_PIN_BINDING_INVALID",
        )
        index[name] = row
    require(index.keys() == source_paths, "REQUIRED_SOURCE_PIN_MISSING")
    for relative, row in index.items():
        expected_bytes, expected_sha = row["bytes"], row["sha256"]
        path = MAIN / relative
        try:
            public_bytes = path.read_bytes()
        except OSError:
            raise TargetGuardError("PUBLIC_SOURCE_UNAVAILABLE") from None
        require(
            len(public_bytes) == expected_bytes
            and hashlib.sha256(public_bytes).hexdigest() == expected_sha,
            "PUBLIC_SOURCE_CHANGED",
        )


def validate_scope(scope, settings):
    """Pure guards run before any Main import or database connection."""
    require(type(scope) is dict, "ROOT_BINDING_REQUIRED")
    require(scope.get("schema") == "5703_native70_scope_v1", "SCOPE_SCHEMA_MISMATCH")
    require(
        scope.get("status") == "READY_BOUND_FOR_SINGLE_NEW_NATIVE_JOURNEY",
        "ROOT_BINDING_REQUIRED",
    )
    from normal_transport88 import validate_case_scope
    validate_case_scope(scope)
    require(scope.get("prior_question_id") == "Q_NATIVE70", "QUESTION_SCOPE_MISMATCH")
    require(scope.get("fixed_workspace_id") == WORKSPACE_ID, "WORKSPACE_SCOPE_MISMATCH")
    require(scope.get("expected_release_id") == RELEASE_ID, "RELEASE_SCOPE_MISMATCH")
    require(scope.get("transport_guard_verified") is True, "ROOT_TRANSPORT_GUARD_REQUIRED")
    require(
        scope.get("use_profile") is False and scope.get("reading_context") is None
        and scope.get("scan_old_jobs_or_recover_stale") is False
        and scope.get("cleanup_or_delete_rows") is False
        and scope.get("new_databases") == 0 and scope.get("retries") == 0
        and scope.get("paid_judges") == 0
        and scope.get("normal_project_activation_qualified") is False,
        "ISOLATED_NATIVE_SCOPE_MISMATCH",
    )
    start = utc(scope.get("started_at_UTC"))
    require(start <= dt.datetime.now(dt.timezone.utc), "SCOPE_START_IN_FUTURE")
    expected = scope.get("expected_settings")
    require(type(expected) is dict and expected, "SETTINGS_BINDING_REQUIRED")
    require(
        REQUIRED_SETTINGS <= expected.keys() and expected.keys() <= PUBLIC_SETTINGS,
        "PUBLIC_SETTINGS_BINDING_INCOMPLETE",
    )
    require(
        canonical({name: getattr(settings, name, None) for name in expected}) == canonical(expected),
        "SETTINGS_BINDING_MISMATCH",
    )
    selected_source_paths(scope)
    require(settings.env == "test" and settings.model_mode == "live", "ISOLATED_LIVE_MODE_REQUIRED")
    require(settings.max_provider_calls == 4 and settings.request_timeout_seconds == 180
            and settings.chat_checker_output_policy == expected["chat_checker_output_policy"]
            and settings.chat_checker_payload_policy == "lossless_full_checker_tables_v2"
            and settings.chat_source_relation_policy == "source_relation_contract_v2"
            and settings.chat_joint_checker_policy == "typed_joint_v5"
            and settings.chat_checker_schema_policy is None,
            "EXACT_PHASE88_OPT_IN_SETTINGS_REQUIRED")
    require(settings.seed_demo_users is False, "SEED_SIDE_EFFECT_FORBIDDEN")
    require(settings.worker_prewarm_retrieval_cache is False, "WARMUP_MUST_BE_SEPARATE")
    require(getattr(settings, "llm_api_key", None) is None, "ALTERNATE_CREDENTIAL_FORBIDDEN")
    for name in ("expected_model_config", "expected_checker_config"):
        config = scope.get(name)
        require(type(config) is dict and config, "ROLE_CONFIG_BINDING_REQUIRED")
        require(
            config.get("provider") == "openai_compatible"
            and config.get("base_url") == "https://openrouter.ai/api/v1"
            and config.get("api_key_env") is None
            and config.get("auth_header") is None
            and type(config.get("configuration_id")) is str
            and bool(config["configuration_id"]),
            "ROLE_CONFIG_DESTINATION_MISMATCH",
        )
        require(
            type(config.get("max_tokens")) is int and config["max_tokens"] > 0
            and type(config.get("timeout_seconds")) in (int, float)
            and math.isfinite(config["timeout_seconds"])
            and 0 < config["timeout_seconds"] <= 60,
            "ROLE_CONFIG_LIMIT_MISMATCH",
        )
        canonical(config)
    return start


def execute_targeted_answer(
    engine, settings, *, scope, browser_receipt, session_id, owner_id, claim_writer,
    owned_lock_connection,
):
    """Claim one brand-new native receipt, then run the unmodified normal executor.

    claim_writer must fsync a non-clobber target record and return
    {"durably_recorded": True} before the database claim is committed. The parent
    separately owns transport accounting for every provider stage. The function
    returns only finite public status/identity fields and never raw errors/auth.
    The parent must acquire and commit the project session advisory lock before
    creating any native session/job, and retain this connection for the entire
    journey. This function verifies ownership; it never acquires/releases it.
    """
    QUESTION = scope["question_text"]
    start = validate_scope(scope, settings)
    verify_source_pins(scope)
    require(type(browser_receipt) is dict, "NEW_BROWSER_RECEIPT_REQUIRED")
    require(callable(claim_writer), "DURABLE_TARGET_CLAIM_WRITER_REQUIRED")
    job_id = uuid(browser_receipt.get("job_id"))
    request_id = uuid(browser_receipt.get("request_id"))
    user_message_id = uuid(browser_receipt.get("user_message_id"))
    session_id, owner_id = uuid(session_id), uuid(owner_id)
    require(
        browser_receipt.get("poll_url") == f"/api/v1/jobs/{job_id}",
        "NEW_BROWSER_RECEIPT_MISMATCH",
    )
    require(engine.dialect.name == "postgresql", "ISOLATED_POSTGRES_REQUIRED")
    require(
        engine.url.drivername == "postgresql+psycopg"
        and engine.url.host == "127.0.0.1" and engine.url.port == 15433
        and engine.url.database == DATABASE_NAME,
        "ISOLATED_ENGINE_IDENTITY_MISMATCH",
    )
    require(
        owned_lock_connection is not None
        and getattr(owned_lock_connection, "engine", None) is engine
        and getattr(owned_lock_connection, "closed", True) is False
        and getattr(owned_lock_connection, "invalidated", True) is False,
        "OWNED_PROJECT_LOCK_CONNECTION_REQUIRED",
    )

    # These imports happen only after public scope, source, and engine guards.
    from app.db.base import new_uuid, utcnow
    from app.modules.answering import service
    from app.modules.answering.models import (
        Answer,
        AnswerRequest,
        Attempt,
        Job,
        Message,
        Snapshot,
    )
    from app.modules.identity.models import User
    from app.modules.learning.models import ChatSession
    from app.modules.learning_state.models import LearningTask
    from sqlalchemy import select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import sessionmaker

    require(engine.url == make_url(settings.database_url), "SETTINGS_ENGINE_IDENTITY_MISMATCH")
    require(
        Path(service.__file__).resolve() == (MAIN / "backend/app/modules/answering/service.py").resolve(),
        "LOADED_EXECUTOR_SOURCE_MISMATCH",
    )
    def verify_owned_project_lock(expected_pid=None):
        # The parent serializes this connection; no other thread may issue SQL
        # on it while this function validates the session-owned lock.
        require(
            not owned_lock_connection.closed and not owned_lock_connection.invalidated
            and owned_lock_connection.engine is engine,
            "OWNED_PROJECT_LOCK_CONNECTION_LOST",
        )
        require(not owned_lock_connection.in_transaction(), "OUTER_LOCK_SQL_NOT_SERIALIZED")
        try:
            observed = owned_lock_connection.execute(text(
                "SELECT current_database() AS database_name, pg_backend_pid() AS backend_pid, "
                "EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' "
                "AND pid = pg_backend_pid() AND classid = 0::oid "
                "AND objid = 5703001::oid AND objsubid = 1 "
                "AND mode = 'ExclusiveLock' AND granted) AS owns_lock"
            )).mappings().one()
            owned_lock_connection.commit()
        except Exception:  # noqa: BLE001 - connection diagnostics may contain credentials.
            raise TargetGuardError("OWNED_PROJECT_LOCK_VALIDATION_FAILED") from None
        require(observed["database_name"] == DATABASE_NAME, "DATABASE_IDENTITY_MISMATCH")
        require(
            type(observed["backend_pid"]) is int and observed["backend_pid"] > 0
            and (expected_pid is None or observed["backend_pid"] == expected_pid)
            and observed["owns_lock"] is True,
            "PARENT_PROJECT_LOCK_NOT_OWNED",
        )
        return observed["backend_pid"]

    lock_backend_pid = verify_owned_project_lock()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    token = None
    with factory() as db:
        session = db.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.user_id == owner_id,
                ChatSession.workspace_id == WORKSPACE_ID,
                ChatSession.status == "active", ChatSession.deleted_at.is_(None),
            ).with_for_update(skip_locked=True)
        )
        require(session is not None and utc(session.created_at) >= start, "SESSION_NOT_NEW_TARGET")
        owner = db.execute(
            select(User.id, User.workspace_id, User.status).where(User.id == owner_id)
        ).one_or_none()
        require(
            owner is not None and owner.workspace_id == WORKSPACE_ID and owner.status == "active",
            "OWNER_WORKSPACE_MISMATCH",
        )
        request = db.scalar(select(AnswerRequest).where(
            AnswerRequest.id == request_id, AnswerRequest.owner_id == owner_id,
            AnswerRequest.session_id == session_id,
        ))
        require(request is not None and utc(request.created_at) >= start, "REQUEST_NOT_NEW_TARGET")
        require(
            request.mode == "interactive_chat" and request.state == "queued"
            and request.route == f"/sessions/{session_id}/messages"
            and request.user_message_id == user_message_id
            and request.assistant_message_id is None and request.regeneration_of is None
            and request.run_id is None and request.item_id is None
            and request.release_id == RELEASE_ID and request.response_schema == "chat_response_v1",
            "REQUEST_TARGET_CONTEXT_MISMATCH",
        )
        session_requests = list(db.scalars(select(AnswerRequest.id).where(
            AnswerRequest.session_id == session_id
        )))
        require(session_requests == [request_id], "SESSION_HAS_OTHER_REQUESTS")
        command = request.command
        require(type(command) is dict and command.get("question") == QUESTION, "REQUEST_QUESTION_MISMATCH")
        require(
            command.get("checker_payload_policy") == settings.chat_checker_payload_policy
            and command.get("checker_output_policy") == settings.chat_checker_output_policy
            and command.get("joint_checker_policy") == settings.chat_joint_checker_policy
            and command.get("source_relation_policy") == settings.chat_source_relation_policy
            and command.get("reliability_policy") == "evidence_reliability_v5",
            "FROZEN_FULL_CHECKER_COMMAND_CHANGED",
        )
        require(
            command.get("answer_mode") == "textbook"
            and command.get("memory_snapshot_id") is None
            and command.get("reading_context") is None,
            "OLD_PRIVATE_OR_READING_CONTEXT_FORBIDDEN",
        )
        memory_stage = command.get("memory_stage")
        require(
            type(memory_stage) is dict and memory_stage.get("status") == "disabled",
            "PRIVATE_MEMORY_PREPARATION_FORBIDDEN",
        )
        restatement = command.get("restatement_context")
        require(
            restatement is None or type(restatement) is dict
            and restatement.get("latest_exchange_available") is False
            and all(restatement.get(name) is None for name in
                    ("user_message_id", "assistant_message_id", "answer_id")),
            "OLD_RESTATEMENT_CONTEXT_FORBIDDEN",
        )
        teaching = command.get("teaching_context")
        require(
            type(teaching) is dict and teaching.get("continuing") is False
            and teaching.get("question") == QUESTION
            and teaching.get("current_problem") == QUESTION
            and teaching.get("current_request") == QUESTION
            and teaching.get("teaching_mode") == "direct"
            and teaching.get("turn_role") == "user_question"
            and teaching.get("delivered_turns") == []
            and teaching.get("disclosure_events") == []
            and teaching.get("practice_context") is None
            and teaching.get("learner_attempt") is None,
            "OLD_TEACHING_CONTEXT_FORBIDDEN",
        )
        task = db.get(LearningTask, teaching.get("task_id"))
        require(
            task is not None and task.owner_id == owner_id and task.session_id == session_id
            and task.initial_message_id == user_message_id and task.question == QUESTION
            and task.state == "active" and task.help_level == 0
            and task.teaching_mode == "direct" and utc(task.created_at) >= start
            and task.pending_tutor_question_id is None
            and task.last_attempt_evaluation is None
            and canonical(task.requirements) == canonical({"original_question": QUESTION}),
            "TEACHING_TASK_NOT_NEW_TARGET",
        )
        require(
            list(db.scalars(select(LearningTask.id).where(LearningTask.session_id == session_id)))
            == [task.id], "SESSION_HAS_OTHER_TEACHING_TASKS",
        )
        require(
            canonical(command.get("model_config")) == canonical(scope["expected_model_config"])
            and canonical(command.get("checker_config")) == canonical(scope["expected_checker_config"]),
            "FROZEN_ROLE_CONFIG_MISMATCH",
        )
        context = db.get(Snapshot, request.context_snapshot_id)
        profile = db.get(Snapshot, request.profile_snapshot_id)
        for snapshot, kind in ((context, "conversation"), (profile, "profile")):
            require(
                snapshot is not None and snapshot.owner_id == owner_id
                and snapshot.session_id == session_id and snapshot.kind == kind
                and utc(snapshot.created_at) >= start,
                "SNAPSHOT_NOT_NEW_TARGET",
            )
        require(
            context.payload.get("session_id") == session_id
            and context.payload.get("messages") == []
            and context.payload.get("cutoff_sequence") == 0
            and context.payload.get("summary_id") is None
            and context.payload.get("summary_hash") is None
            and context.payload.get("covered_until_sequence") is None
            and context.payload.get("summary_text") is None
            and context.payload.get("exclusions") == []
            and profile.payload.get("use_profile") is False,
            "HISTORY_OR_PROFILE_CONTEXT_FORBIDDEN",
        )
        messages = list(db.scalars(select(Message).where(Message.session_id == session_id)))
        require(len(messages) == 1, "SESSION_MESSAGES_NOT_SINGLE_NEW_USER")
        message = messages[0]
        require(
            message.id == user_message_id and message.role == "user" and message.sequence == 1
            and message.content == QUESTION and message.request_id == request_id
            and message.state == "queued" and message.active_answer_id is None
            and utc(message.created_at) >= start,
            "USER_MESSAGE_NOT_NEW_TARGET",
        )
        job = db.scalar(select(Job).where(
            Job.id == job_id, Job.request_id == request_id, Job.owner_id == owner_id,
            Job.kind == "answer", Job.state == "queued",
        ).with_for_update(skip_locked=True))
        require(
            job is not None and utc(job.created_at) >= start and job.execution_token is None
            and job.worker_id is None and type(job.attempts) is int and job.attempts == 0
            and job.stage == "queued" and job.answer_id is None and job.error is None,
            "JOB_NOT_UNCLAIMED_NEW_TARGET",
        )
        require(
            list(db.scalars(select(Job.id).where(Job.request_id == request_id))) == [job_id]
            and db.scalar(select(Answer.id).where(Answer.request_id == request_id)) is None
            and db.scalar(select(Attempt.id).where(Attempt.job_id == job_id)) is None,
            "REQUEST_HAS_PRIOR_EXECUTION_ROWS",
        )
        require(
            request.budget.get("consumed_calls") == 0 and request.budget.get("active_seconds") == 0
            and request.budget.get("max_calls") == settings.max_provider_calls
            and request.budget.get("max_active_seconds") == settings.request_timeout_seconds,
            "REQUEST_BUDGET_NOT_FRESH",
        )
        token = new_uuid()
        durable = claim_writer({
            "schema": "5703_native70_target_claim_v1",
            "state": "VALIDATED_NEW_TARGET_PENDING_COMMIT",
            "question_id": scope["question_id"], "job_id": job_id, "request_id": request_id,
            "session_id": session_id, "user_message_id": user_message_id,
            "execution_token_sha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "execution_token_plaintext_exported": False,
            "provider_execution_started": False,
            "source_pins_verified": True, "old_jobs_selected": 0,
        })
        require(type(durable) is dict and durable.get("durably_recorded") is True, "TARGET_CLAIM_NOT_DURABLE")
        job.state = "running"
        job.execution_token = token
        job.worker_id = "native70-targeted-fixture:interactive"
        job.attempts += 1
        job.updated_at = utcnow()
        db.commit()
    try:
        verify_source_pins(scope)
        verify_owned_project_lock(lock_backend_pid)
        service.execute_answer(engine, settings, job_id, token)
    except Exception as exc:  # noqa: BLE001 - normal executor failures retain this owned job.
        # Preserve the fresh request and its trace. No retry or old-job mutation.
        with factory() as db:
            initial = db.get(Job, job_id)
            request = db.get(AnswerRequest, request_id)
            require(
                initial is not None and initial.request_id == request_id
                and request is not None and request.session_id == session_id
                and request.owner_id == owner_id,
                "TERMINAL_TARGET_IDENTITY_CHANGED",
            )
            service.lock_request_session(db, request)
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job.state == "running" and job.execution_token == token:
                service.fail_job(db, job, {
                    "code": "NATIVE70_EXECUTION_STOPPED",
                    "message": "The bounded native fixture execution stopped. Preserve records before review.",
                    "details": {"uncertain_external_execution": True},
                })
                db.commit()
        code = exc.code if isinstance(exc, TargetGuardError) else "NORMAL_EXECUTOR_RAISED"
        return {"status": "STOPPED_PRESERVE_NEW_ROWS", "stop_code": code, "job_id": job_id,
                "request_id": request_id, "old_jobs_selected": 0, "automatic_retries": 0}
    verify_owned_project_lock(lock_backend_pid)
    with factory() as db:
        job = db.get(Job, job_id)
        require(job is not None and job.request_id == request_id, "RESULT_TARGET_IDENTITY_CHANGED")
        return {"status": "TARGET_EXECUTOR_RETURNED", "job_id": job_id, "request_id": request_id,
                "job_state": job.state, "answer_id": job.answer_id,
                "old_jobs_selected": 0, "automatic_retries": 0}
