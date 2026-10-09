"""Pure scripted grading wiring; no DB, provider or semantic quality measurement."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from threading import Event
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
import app.db.models  # Register ORM types without creating a database.
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.learning_product import (
    grading,
    practice_assessment as assessment,
    service,
    tutoring,
)
from app.modules.learning_product.models import (
    LearningRecord,
    PracticeAttempt,
    PracticeItem,
    ReviewEntry,
    StudyGoal,
    StudyUnit,
)
from contracts.study import AttemptInput, AttemptOut, PracticeResponse
from generation.types import ModelConfig, ProviderResult


class Ledger:
    """In-memory transaction seam exercising real submission/finalizer code."""

    def __init__(self):
        self.rows = {}
        self.commits = 0
        self.locked = False

    def add(self, row):
        if getattr(row, "id", None) is None:
            row.id = str(uuid4())
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(timezone.utc)
        if getattr(row, "version", None) is None:
            row.version = 1
        self.rows.setdefault(type(row), {})[row.id] = row

    def get(self, kind, identity):
        return self.rows.get(kind, {}).get(identity)

    def scalars(self, query):
        kind = query.column_descriptions[0]["entity"]
        rows = list(self.rows.get(kind, {}).values())
        for key, value in query.compile().params.items():
            name = key.rsplit("_", 1)[0]
            rows = [row for row in rows if getattr(row, name) == value]
        if kind == PracticeAttempt:
            rows.sort(key=lambda row: (row.created_at, row.id), reverse=True)
        if query.column_descriptions[0]["name"] == "section_id":
            return [row.section_id for row in rows]
        return rows

    def scalar(self, query):
        rows = self.scalars(query)
        return rows[0] if rows else None

    def flush(self):
        pass

    def commit(self):
        self.commits += 1
        self.locked = False

    def rollback(self):
        self.locked = False

    def expire_all(self):
        pass

    def refresh(self, *args, **kwargs):
        pass


@pytest.fixture
def scope(monkeypatch):
    db = Ledger()
    actor = NS(id="owner", workspace_id="workspace", status="active")
    source_text = "The authored source states that photosynthesis uses light energy, rather than sound, to produce stored chemical energy."
    item = NS(
        id="item",
        workspace_id="workspace",
        item_revision=2,
        version=4,
        state="published",
        content_hash="a" * 64,
        source=dict(
            document_id="book",
            release_id="release",
            processing_id="processing",
            source_unit_id="unit",
            text_hash="b" * 64,
            start=0,
            end=len(source_text),
        ),
        public_payload=dict(
            kind="short",
            prompt="Explain the energy input.",
            title="Authored source exercise",
            concepts=["photosynthesis"],
            conditions=["Use the authored source."],
            options=[],
        ),
        private_rubric=dict(
            acceptable_answers=["Light supplies energy."],
            required_points=[dict(id="PRIVATE_KEY_POINT_CANARY", terms=["light energy"])],
            forbidden_terms=[],
            explanation="PRIVATE_SOLUTION_CANARY",
            hints=["PRIVATE_HINT_CANARY"],
        ),
        validation={"section_id": "section"},
    )
    progress = NS(
        id="progress",
        owner_id=actor.id,
        item_id=item.id,
        version=0,
        current_step=1,
        help_level=1,
        state="awaiting_attempt",
        full_explanation=False,
        shown_hints=["Already disclosed hint"],
        tutor_task_id=None,
    )
    goal = NS(
        id="goal",
        owner_id=actor.id,
        document_id="book",
        release_id="release",
        state="active",
        version=3,
    )
    db.rows[PracticeItem] = {item.id: item}
    db.rows[StudyGoal] = {goal.id: goal}
    db.rows[StudyUnit] = {
        "section-unit": NS(id="section-unit", goal_id=goal.id, section_id="section")
    }
    calls, memories, synchronizations = [], [], []

    def lock_owner(_db, _actor):
        if _actor.id != actor.id or actor.status != "active":
            raise AppError("FORBIDDEN")
        db.locked = True
        return actor

    def practice_item(_db, _actor, identity, admin=False):
        if (
            identity != item.id
            or _actor.workspace_id != item.workspace_id
            or item.state != "published"
        ):
            raise AppError("NOT_FOUND")
        if getattr(item, "revoked", False):
            raise AppError("SOURCE_UNAVAILABLE")
        return item

    def owned(_db, kind, identity, _actor, lock=False):
        row = db.get(kind, identity)
        if not row or row.owner_id != _actor.id:
            raise AppError("NOT_FOUND")
        return row

    monkeypatch.setattr(service, "lock_owner", lock_owner)
    monkeypatch.setattr(service, "practice_item", practice_item)
    monkeypatch.setattr(service, "owned", owned)
    monkeypatch.setattr(service, "get_progress", lambda *args: progress)
    monkeypatch.setattr(
        service, "record_practice_memory", lambda *args, **kwargs: memories.append(kwargs)
    )
    monkeypatch.setattr(
        tutoring,
        "synchronize",
        lambda *args: synchronizations.append((progress.current_step, progress.state)),
    )
    monkeypatch.setattr(tutoring, "linked_task", lambda *args: None)
    monkeypatch.setattr(
        assessment.library,
        "validate_locator",
        lambda *args: (None, None, NS(cleaned_text=source_text)),
    )
    config = ModelConfig(
        provider="openai_compatible",
        model="scripted-test-only",
        configuration_id="model-settings:test",
        tokenizer_provider="estimate",
        window_tokens=32000,
        max_tokens=4096,
        timeout_seconds=0.1,
    )
    monkeypatch.setattr(assessment, "resolve_active_checker_model_config", lambda *args: config)
    monkeypatch.setattr(assessment, "resolve_secret", lambda *args: None)
    monkeypatch.setattr(
        assessment,
        "workspace_document",
        lambda *args, **kwargs: NS(active=True, revoked=getattr(item, "revoked", False)),
    )
    state = NS(
        db=db,
        actor=actor,
        item=item,
        progress=progress,
        goal=goal,
        calls=calls,
        memories=memories,
        synchronizations=synchronizations,
        config=config,
        source_text=source_text,
        verdict="correct",
        mutation=None,
        judgment_change=None,
        raw=None,
        provider_error=None,
        finish_reason="stop",
    )

    def generate(adapter, messages, **kwargs):
        assert not db.locked and db.commits >= 1
        assert any(
            row.kind == "practice_assessment_started" for row in db.rows[LearningRecord].values()
        )
        calls.append(messages)
        data = json.loads(messages[1]["content"])
        assert "PRIVATE_SOLUTION_CANARY" not in str(data)
        assert "PRIVATE_HINT_CANARY" not in str(data)
        assert "PRIVATE_KEY_POINT_CANARY" not in str(data)
        if state.mutation:
            state.mutation()
        value = judgment(data, state.verdict)
        if state.judgment_change:
            value = state.judgment_change(data, value)
        return ProviderResult(
            raw_text=state.raw if state.raw is not None else json.dumps(value),
            provider=config.provider,
            model=config.model,
            request_submitted=True,
            error=state.provider_error,
            finish_reason=state.finish_reason,
        )

    monkeypatch.setattr(assessment.LLMAdapter, "generate", generate)
    return state


def judgment(data, verdict="correct"):
    points = [point["id"] for point in data["criteria"]["required_points"]]
    return dict(
        binding_hash=data["binding_hash"],
        outcome=verdict,
        source_sufficient=True,
        rubric_supported=True,
        contradiction_present=verdict == "incorrect",
        conditions_preserved=True,
        covered_point_ids=points if verdict == "correct" else [],
        missing_point_ids=[] if verdict == "correct" else points,
        source_spans=[dict(start=0, end=len(data["source_passage"]))],
        response_spans=[dict(start=0, end=len(data["learner_text"]))],
    )


def submit(scope, text="Plants turn incoming sunlight into stored energy.", **changes):
    body = dict(
        idempotency_key="receipt-key",
        expected_version=scope.progress.version,
        response=dict(text=text),
    )
    body.update(changes)
    return service.submit_attempt(
        scope.db, scope.actor, scope.item.id, AttemptInput.model_validate(body), NS()
    )


@pytest.mark.parametrize(
    "text",
    [
        "Light energy is present, but only sound drives this process.",
        "Light energy is only an output, never the energy input.",
        "Light energy can be mentioned; the actual input is heat alone.",
        "Light energy supplies nothing; sound supplies all stored chemical energy.",
        "The leaf receives light energy but uses it solely to destroy every product.",
        "Light energy is relevant vocabulary; no conversion to stored energy occurs.",
        "The term light energy describes the process, which converts chemical energy into light exclusively.",
        "Light energy is a matching phrase; this process works using sound instead.",
    ],
    ids=[f"authored-contradiction-{number}" for number in range(1, 9)],
)
def test_eight_contradictions_cannot_pass_by_keyword_coverage(scope, text):
    scope.verdict = "incorrect"
    receipt = submit(scope, text)
    assert receipt["feedback"]["outcome"] == "pending_review"
    assert receipt["assessment"]["status"] == "applied"
    assert receipt["assessment"]["feedback"]["outcome"] == "incorrect"
    assert scope.progress.state == "awaiting_attempt"
    assert scope.progress.current_step == 1
    assert scope.db.scalar(__import__("sqlalchemy").select(ReviewEntry)).correct_count == 0


@pytest.mark.parametrize(
    "text",
    [
        "Plants turn incoming sunlight into stored energy.",
        "Sound is not the energy source; sunlight supplies it.",
    ],
)
def test_scripted_valid_paraphrases_and_negative_statements_apply_once(scope, text):
    body = AttemptInput(
        idempotency_key="stable", expected_version=0, response=PracticeResponse(text=text)
    )
    receipt = service.submit_attempt(scope.db, scope.actor, "item", body, NS())
    AttemptOut.model_validate(receipt)
    assert receipt["feedback"]["outcome"] == "pending_review"
    assert receipt["assessment"]["feedback"]["outcome"] == "correct"
    assert scope.progress.state == "completed" and scope.progress.version == 2
    assert len(scope.calls) == len(scope.memories) == 1
    replay = service.submit_attempt(scope.db, scope.actor, "item", body, NS())
    assert replay == receipt and len(scope.calls) == 1 and len(scope.memories) == 1
    reservation = scope.db.get(LearningRecord, assessment.operation_id(receipt["id"])).details
    assessment.finish(scope.db, scope.actor, receipt["id"], reservation, None, {})
    assert len(scope.memories) == 1 and scope.progress.version == 2


@pytest.mark.parametrize(
    "failure", ["unconfigured", "mock", "provider", "schema", "truncated", "uncertain", "cancelled"]
)
def test_failed_assessments_preserve_progress_and_have_no_grade_side_effects(
    scope, monkeypatch, failure
):
    if failure in ("unconfigured", "mock"):
        monkeypatch.setattr(
            assessment,
            "resolve_active_checker_model_config",
            lambda *args: None if failure == "unconfigured" else ModelConfig(),
        )
    elif failure in ("provider", "cancelled"):
        scope.provider_error = {
            "code": "CANCELLED" if failure == "cancelled" else "PROVIDER_HTTP_ERROR",
            "message": "PRIVATE_PROVIDER_CANARY",
        }
    elif failure == "schema":
        scope.raw = '{"answer":"PRIVATE_OUTPUT_CANARY"}'
    elif failure == "truncated":
        scope.finish_reason = "length"
    elif failure == "uncertain":
        scope.verdict = "uncertain"
    scope.progress.state = "completed"
    before = deepcopy(vars(scope.progress))
    receipt = submit(scope)
    assert receipt["assessment"]["status"] == "pending_review"
    assert receipt["assessment"]["feedback"]["outcome"] == "pending_review"
    assert vars(scope.progress) == dict(before, version=before["version"] + 1)
    assert not scope.memories and not scope.db.rows.get(ReviewEntry)
    assert len(scope.calls) == (0 if failure in ("unconfigured", "mock") else 1)
    public = json.dumps(
        [assessment.public_record_details(row) for row in scope.db.rows[LearningRecord].values()]
    )
    assert "PRIVATE_" not in public and "source_passage" not in public.replace(
        "source_passage_hash", ""
    )


@pytest.mark.parametrize(
    "change", ["progress", "help", "source", "item", "owner", "workspace", "goal"]
)
def test_late_results_cannot_overwrite_changed_authority(scope, change):
    mutations = {
        "progress": lambda: setattr(scope.progress, "version", scope.progress.version + 1),
        "help": lambda: setattr(scope.progress, "help_level", 2),
        "source": lambda: setattr(scope.item, "revoked", True),
        "item": lambda: setattr(scope.item, "item_revision", 3),
        "owner": lambda: setattr(scope.actor, "status", "deactivated"),
        "workspace": lambda: setattr(scope.actor, "workspace_id", "elsewhere"),
        "goal": lambda: setattr(scope.goal, "state", "paused"),
    }
    scope.mutation = mutations[change]
    receipt = submit(scope, goal_id="goal")
    assert receipt["assessment"]["status"] == "superseded"
    assert scope.progress.state == "awaiting_attempt" and scope.progress.current_step == 1
    assert not scope.memories and not scope.db.rows.get(ReviewEntry)


def test_unknown_or_forged_schema_fields_and_spans_fail_closed(scope):
    data = json.loads(scope.calls[0][1]["content"]) if scope.calls else None
    # A committed submission supplies the exact binding for isolated schema probes.
    receipt = submit(scope)
    data = json.loads(scope.calls[0][1]["content"])
    prepared = assessment.Prepared(
        scope.config,
        scope.calls[0],
        {},
        data["binding_hash"],
        data["source_passage"],
        data["learner_text"],
        {"P01"},
        {},
    )
    original = judgment(data)
    for altered in (
        dict(original, binding_hash="0" * 64),
        dict(original, raw_feedback="PRIVATE_OUTPUT_CANARY"),
        dict(original, source_spans=[dict(start=0, end=len(data["source_passage"]) + 1)]),
        dict(original, contradiction_present=True),
        dict(original, conditions_preserved=False),
        dict(original, covered_point_ids=["PRIVATE_KEY_POINT_CANARY"]),
        dict(original, source_sufficient="true"),
    ):
        with pytest.raises(ValueError):
            assessment.validate_judgment(json.dumps(altered), prepared)
    assert receipt["assessment"]["feedback"]["semantic_correctness_verified"] is None


def test_new_preparation_supplies_complete_unicode_context_and_schema(scope, monkeypatch):
    source = "A vessel's volume is 2 m³; temperature must remain fixed, not increase."
    response = "The volume is 2 m³; the temperature does not increase."
    monkeypatch.setattr(
        assessment.library,
        "validate_locator",
        lambda *args: (None, None, NS(cleaned_text=source)),
    )
    prepared = assessment.prepare(
        scope.db,
        NS(),
        scope.actor,
        scope.item,
        NS(id="unicode-attempt", response=dict(text=response)),
        scope.progress,
        {"reservation": "test-only"},
    )
    data = json.loads(prepared.messages[1]["content"])
    assert data["source_passage"] == source and data["learner_text"] == response
    assert data["assessment_context_ranges"] == {
        "source_spans": [dict(start=0, end=71)],
        "response_spans": [dict(start=0, end=54)],
    }
    assert prepared.metadata["span_grounding_version"] == "complete_assessment_context_v2"
    assert prepared.metadata["assessment_schema_name"] == "practice_judgment_v2"
    assert prepared.metadata["schema_hash"] == assessment.digest(prepared.schema)
    for field, end in (("source_spans", 71), ("response_spans", 54)):
        schema = prepared.schema["properties"][field]
        assert schema["maxItems"] == 1
        assert schema["items"]["properties"]["start"]["enum"] == [0]
        assert schema["items"]["properties"]["end"]["enum"] == [end]
        assert schema["items"]["additionalProperties"] is False
    reservation = dict(data)
    reservation.pop("binding_hash")
    assert prepared.binding_hash == assessment.digest(reservation)
    assert assessment.VERSION == "practice_model_assessment_v1"


@pytest.mark.parametrize(
    "failure",
    [
        "negation_tail",
        "condition_tail",
        "source_word",
        "source_prefix",
        "duplicate",
        "empty",
        "bounds",
    ],
)
def test_incomplete_or_invalid_v2_context_keeps_work_pending_without_grade_effects(scope, failure):
    response = "Light energy enters; sound is absent; only the stated conditions apply."

    def alter(data, value):
        if failure == "negation_tail":
            value["response_spans"] = [dict(start=0, end=data["learner_text"].index("absent"))]
        elif failure == "condition_tail":
            value["response_spans"] = [dict(start=0, end=data["learner_text"].index("; only"))]
        elif failure == "source_word":
            value["source_spans"] = [dict(start=1, end=len(data["source_passage"]))]
        elif failure == "source_prefix":
            value["source_spans"] = [dict(start=0, end=15)]
        elif failure == "duplicate":
            value["response_spans"] *= 2
        elif failure == "empty":
            value["source_spans"] = value["response_spans"] = [dict(start=0, end=0)]
        else:
            value["response_spans"] = [dict(start=0, end=len(data["learner_text"]) + 1)]
        return value

    scope.judgment_change = alter
    receipt = submit(scope, response)
    assert receipt["feedback"]["outcome"] == "pending_review"
    assert receipt["assessment"]["status"] == "pending_review"
    assert receipt["assessment"]["feedback"]["outcome"] == "pending_review"
    assert scope.progress.current_step == 1 and scope.progress.state == "awaiting_attempt"
    assert not scope.memories and not scope.db.rows.get(ReviewEntry)
    assert len(scope.calls) == 1
    saved = scope.db.get(PracticeAttempt, receipt["id"])
    assert saved.response["text"] == response


@pytest.mark.parametrize("version", [None, "", "unrecognized_context_v3"])
def test_unknown_explicit_span_version_does_not_take_the_legacy_path(scope, version):
    submit(scope)
    data = json.loads(scope.calls[0][1]["content"])
    prepared = assessment.Prepared(
        scope.config,
        scope.calls[0],
        {},
        data["binding_hash"],
        data["source_passage"],
        data["learner_text"],
        {"P01"},
        dict(span_grounding_version=version, assessment_schema_name="practice_judgment_v2"),
    )
    with pytest.raises(ValueError, match="Unknown assessment span contract"):
        assessment.validate_judgment(json.dumps(judgment(data)), prepared)


def test_historical_missing_span_version_retains_original_bounded_validation(scope):
    submit(scope)
    data = json.loads(scope.calls[0][1]["content"])
    prepared = assessment.Prepared(
        scope.config,
        scope.calls[0],
        {},
        data["binding_hash"],
        data["source_passage"],
        data["learner_text"],
        {"P01"},
        {},
    )
    value = judgment(data)
    value["response_spans"] = [dict(start=0, end=6)]
    assert assessment.validate_judgment(json.dumps(value), prepared)["outcome"] == "correct"
    prepared.metadata = dict(
        span_grounding_version="complete_assessment_context_v2",
        assessment_schema_name="practice_judgment_v2",
    )
    with pytest.raises(ValueError, match="complete supplied context"):
        assessment.validate_judgment(json.dumps(value), prepared)


def test_uncertain_v2_with_empty_support_stays_pending(scope):
    def unsupported(data, value):
        return dict(
            value,
            outcome="uncertain",
            source_sufficient=False,
            source_spans=[],
            response_spans=[],
        )

    scope.judgment_change = unsupported
    receipt = submit(scope)
    assert receipt["assessment"]["status"] == "pending_review"
    assert scope.progress.current_step == 1 and not scope.memories
    assert not scope.db.rows.get(ReviewEntry)


def test_history_projects_span_contract_identity_without_context_payload(scope):
    receipt = submit(scope)
    reservation = scope.db.get(LearningRecord, assessment.operation_id(receipt["id"]))
    details = assessment.public_record_details(reservation)
    assert details["span_grounding_version"] == "complete_assessment_context_v2"
    assert details["assessment_schema_name"] == "practice_judgment_v2"
    assert "assessment_context_ranges" not in details
    assert "source_passage" not in details and "learner_text" not in details


def test_numeric_and_choice_rules_never_call_the_model(scope):
    scope.item.public_payload["kind"] = "numeric"
    scope.item.private_rubric = dict(numeric=dict(value=2, unit="m"), explanation="PRIVATE_NUMERIC")
    receipt = submit(scope, response=dict(value=200, unit="cm"))
    assert receipt["feedback"]["outcome"] == "correct" and receipt["assessment"] is None
    assert not scope.calls


def test_existing_review_due_time_and_error_signal_survive_pending(scope, monkeypatch):
    previous = ReviewEntry(
        id="review",
        owner_id="owner",
        item_id="item",
        attempt_count=4,
        correct_count=2,
        due_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        error_categories=["prior_error"],
        scheduling_reason="Prior assessed error",
        version=7,
    )
    scope.db.add(previous)
    before = deepcopy(vars(previous))
    monkeypatch.setattr(assessment, "resolve_active_checker_model_config", lambda *args: None)
    submit(scope)
    assert previous.due_at == before["due_at"] and previous.correct_count == 2
    assert (
        previous.error_categories == ["prior_error"]
        and previous.scheduling_reason == "Prior assessed error"
    )
    assert previous.attempt_count == 5 and not scope.memories


def test_scope_is_checked_before_reservation_or_call(scope):
    outsider = NS(id="other", workspace_id="workspace", status="active")
    with pytest.raises(AppError):
        service.submit_attempt(
            scope.db,
            outsider,
            "item",
            AttemptInput(
                idempotency_key="other", expected_version=0, response=PracticeResponse(text="Light")
            ),
            NS(),
        )
    assert not scope.calls and not scope.db.rows.get(PracticeAttempt)


def test_timeout_returns_pending_and_ignores_the_late_transport(scope, monkeypatch):
    started, release = Event(), Event()
    config = ModelConfig(**dict(scope.config.to_dict(), timeout_seconds=0.01))
    monkeypatch.setattr(assessment, "resolve_active_checker_model_config", lambda *args: config)
    original = assessment.LLMAdapter.generate

    def slow(adapter, messages, **kwargs):
        started.set()
        release.wait(0.5)
        return original(adapter, messages, **kwargs)

    monkeypatch.setattr(assessment.LLMAdapter, "generate", slow)
    receipt = submit(scope)
    release.set()
    assert started.is_set() and receipt["assessment"]["status"] == "pending_review"
    assert scope.progress.state == "awaiting_attempt" and not scope.memories


def test_generic_history_allowlist_drops_prompts_inputs_provider_and_source(scope):
    row = NS(
        kind="practice_attempt",
        details=dict(
            item_id="item",
            outcome="pending_review",
            private_rubric="PRIVATE_KEY",
            raw_prompt="PRIVATE_PROMPT",
            learner_input="PRIVATE_INPUT",
            provider_output="PRIVATE_PROVIDER",
            source_text="PRIVATE_SOURCE",
        ),
    )
    assert assessment.public_record_details(row) == dict(item_id="item", outcome="pending_review")


def test_tutor_uses_applied_feedback_and_retains_submission_receipt():
    initial = grading.pending_feedback()
    result = dict(
        outcome="correct",
        message="Server-authored model result",
        grading_method="model_assessment_v1",
    )
    attempt = dict(feedback=initial, assessment=dict(status="applied", feedback=result))
    visible = tutoring.tutor_attempt(attempt)
    assert visible["feedback"] == result and visible["submission_feedback"] == initial
    assert attempt["feedback"] == initial
    assert tutoring.tutor_attempt(dict(feedback=initial)) == dict(feedback=initial)


def test_linked_goal_pause_without_body_goal_blocks_application(scope, monkeypatch):
    from app.modules.learning_product import goal_tutoring

    binding = dict(
        version=goal_tutoring.VERSION,
        goal_id="goal",
        item_id="item",
        item_revision=2,
        progress_id="progress",
        section_id="section",
        source=scope.item.source,
    )
    task = NS(
        id="task",
        owner_id="owner",
        session_id="session",
        state="active",
        version=3,
        exposure_epoch=2,
        requirements={goal_tutoring.KEY: binding},
        current_step=1,
        help_level=0,
    )
    scope.progress.tutor_task_id = "task"
    monkeypatch.setattr(tutoring, "linked_task", lambda *args: task)
    monkeypatch.setattr(goal_tutoring, "goal_binding", lambda *args: binding)
    scope.mutation = lambda: setattr(scope.goal, "state", "paused")
    receipt = submit(scope)
    assert receipt["assessment"]["status"] == "superseded"
    assert scope.progress.state == "awaiting_attempt" and not scope.memories


def test_actual_provider_cancellation_stays_pending_without_thread_exception(scope, monkeypatch):
    from asyncio import CancelledError

    def cancelled(*args, **kwargs):
        raise CancelledError("PRIVATE_CANCELLATION_CANARY")

    monkeypatch.setattr(assessment.LLMAdapter, "generate", cancelled)
    receipt = submit(scope)
    assert receipt["assessment"]["status"] == "pending_review"
    assert scope.progress.state == "awaiting_attempt" and not scope.memories
    assert "PRIVATE_CANCELLATION" not in str(receipt)


def test_actual_application_cancellation_uses_rollback_pending_terminal(scope, monkeypatch):
    from asyncio import CancelledError

    calls = []

    def cancelled_once(db, actor, attempt_id, reservation, feedback, diagnostic):
        calls.append(feedback)
        if len(calls) == 1:
            raise CancelledError()
        assert feedback is None and diagnostic["reason"] == "application_failed"
        return {"feedback": grading.pending_feedback()}

    monkeypatch.setattr(assessment, "finish", cancelled_once)
    receipt = submit(scope)
    assert receipt["feedback"]["outcome"] == "pending_review"
    assert len(calls) == 2 and calls[0]["outcome"] == "correct" and calls[1] is None
    assert scope.progress.state == "awaiting_attempt" and not scope.memories
