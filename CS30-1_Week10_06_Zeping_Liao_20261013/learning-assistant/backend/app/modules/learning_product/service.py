"""Transactional learning workflows with owner checks and durable revision fences."""

import datetime as dt
from collections import Counter
from uuid import uuid4
from sqlalchemy import select
from app.core.exceptions import AppError
from app.db.base import utcnow
from app.modules.identity.models import User
from app.modules.answering.models import Answer, AnswerRequest, Citation, Evidence
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
)
from app.modules.learning.models import ChatSession
from contracts.study import PracticeRubric
from . import library, grading
from .models import (
    ReadingPosition,
    StudyGoal,
    StudyUnit,
    PracticeItem,
    PracticeProgress,
    PracticeAttempt,
    ReviewEntry,
    StudyNote,
    LearningRecord,
)


def stamp(value):
    return value.isoformat()


def lock_owner(db, actor):
    row = db.scalar(select(User).where(User.id == actor.id).with_for_update(of=User))
    if row is None or row.status != "active":
        raise AppError("FORBIDDEN")
    return row


def owned(db, model, object_id, actor, lock=False):
    query = select(model).where(model.id == object_id, model.owner_id == actor.id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AppError("NOT_FOUND")
    return row


def cas(row, expected):
    if (row.version if row else 0) != expected:
        raise AppError("CONFLICT", detail="This learning record changed. Refresh before saving.")


def event(db, actor, kind, object_id, **details):
    db.add(LearningRecord(owner_id=actor.id, kind=kind, object_id=object_id, details=details))


def position_out(row):
    return dict(
        id=row.id,
        source=row.source,
        char_offset=row.char_offset,
        version=row.version,
        updated_at=stamp(row.updated_at),
    )


def save_position(db, actor, body):
    lock_owner(db, actor)
    _, _, unit = library.validate_locator(db, actor, body.source)
    if body.char_offset > len(unit.cleaned_text):
        raise AppError("VALIDATION_FAILED", detail="The reading offset exceeds the source unit.")
    row = db.scalar(
        select(ReadingPosition)
        .where(
            ReadingPosition.owner_id == actor.id,
            ReadingPosition.document_id == body.source.document_id,
        )
        .with_for_update()
    )
    cas(row, body.expected_version)
    if row is None:
        row = ReadingPosition(
            owner_id=actor.id,
            document_id=body.source.document_id,
            source=body.source.model_dump(),
            char_offset=body.char_offset,
        )
        db.add(row)
    else:
        row.source, row.char_offset = body.source.model_dump(), body.char_offset
        row.version += 1
    db.flush()
    event(
        db,
        actor,
        "reading_position",
        row.id,
        document_id=row.document_id,
        source_unit_id=unit.id,
        char_offset=row.char_offset,
        learning_claim="reading_only",
    )
    return position_out(row)


def create_goal(db, actor, body):
    lock_owner(db, actor)
    release, _, _ = library.book_data(db, actor, body.document_id)
    choices = library.sections(db, actor, body.document_id, release_id=release.id)
    chosen = set(body.section_ids)
    if len(chosen) != len(body.section_ids) or not chosen <= {c["id"] for c in choices}:
        raise AppError(
            "VALIDATION_FAILED", detail="Choose distinct sections from the current textbook."
        )
    goal = StudyGoal(
        owner_id=actor.id,
        title=body.title,
        document_id=body.document_id,
        release_id=release.id,
        depth=body.depth,
    )
    db.add(goal)
    db.flush()
    previous = None
    for index, section in enumerate(c for c in choices if c["id"] in chosen):
        row = StudyUnit(
            goal_id=goal.id,
            section_id=section["id"],
            title=section["title"],
            ordinal=index,
            concepts=section["concepts"],
            prerequisites=[previous] if previous else [],
        )
        db.add(row)
        db.flush()
        previous = row.id
    event(
        db,
        actor,
        "goal_created",
        goal.id,
        units=len(chosen),
        prerequisite_origin="section_order_suggestion",
    )
    return goal_out(db, actor, goal)


def goal_out(db, actor, goal):
    from . import relations

    attempts = list(
        db.scalars(
            select(PracticeAttempt).where(
                PracticeAttempt.owner_id == actor.id, PracticeAttempt.goal_id == goal.id
            )
        )
    )
    unit_results = []
    for unit in db.scalars(
        select(StudyUnit).where(StudyUnit.goal_id == goal.id).order_by(StudyUnit.ordinal)
    ):
        linked = []
        for attempt in attempts:
            item = db.get(PracticeItem, attempt.item_id)
            if item and item.validation.get("section_id") == unit.section_id:
                linked.append(attempt)
        assessed = [(a, effective_attempt_feedback(db, a)) for a in linked]
        graded = [(a, f) for a, f in assessed if f["outcome"] != "pending_review"]
        correct = sum(f["outcome"] == "correct" for _, f in graded)
        latest = max(graded, key=lambda pair: (pair[0].created_at, pair[0].id)) if graded else None
        review = bool(latest and latest[1]["outcome"] != "correct")
        status = (
            "needs_review"
            if review
            else "practised"
            if linked
            else "read"
            if unit.read
            else "not_started"
        )
        unit_results.append(
            dict(
                id=unit.id,
                section_id=unit.section_id,
                title=unit.title,
                concepts=unit.concepts,
                prerequisite_unit_ids=unit.prerequisites,
                read=unit.read,
                attempts=len(linked),
                correct_attempts=correct,
                graded_attempts=len(graded),
                pending_attempts=len(linked) - len(graded),
                needs_review=review,
                status=status,
                recommended_action="review"
                if review
                else "try_related"
                if graded
                else "practise"
                if unit.read or linked
                else "read",
            )
        )
    return dict(
        id=goal.id,
        title=goal.title,
        document_id=goal.document_id,
        release_id=goal.release_id,
        depth=goal.depth,
        status=goal.state,
        version=goal.version,
        units=unit_results,
        reviewed_relations=relations.for_goal(db, actor, goal, unit_results),
    )


def update_goal(db, actor, goal_id, body):
    goal = owned(db, StudyGoal, goal_id, actor, True)
    cas(goal, body.expected_version)
    if body.title is not None:
        goal.title = body.title
    if body.status is not None:
        goal.state = body.status
    goal.version += 1
    db.flush()
    event(db, actor, "goal_updated", goal.id, state=goal.state)
    return goal_out(db, actor, goal)


def mark_read(db, actor, goal_id, unit_id, version):
    goal = owned(db, StudyGoal, goal_id, actor, True)
    cas(goal, version)
    unit = db.scalar(select(StudyUnit).where(StudyUnit.id == unit_id, StudyUnit.goal_id == goal.id))
    if unit is None:
        raise AppError("NOT_FOUND")
    unit.read = True
    goal.version += 1
    db.flush()
    event(db, actor, "unit_read", unit.id, goal_id=goal.id, learning_claim="reading_only")
    return goal_out(db, actor, goal)


def practice_item(db, actor, item_id, admin=False):
    row = db.scalar(
        select(PracticeItem).where(
            PracticeItem.id == item_id, PracticeItem.workspace_id == actor.workspace_id
        )
    )
    if row is None or (not admin and row.state != "published"):
        raise AppError("NOT_FOUND")
    if not admin:
        library.validate_locator(db, actor, row.source)
    return row


def item_out(item):
    return dict(
        id=item.id,
        **item.public_payload,
        source=item.source,
        item_revision=item.item_revision,
        validation={
            "status": item.validation.get("status", "pending"),
            "method": "structural_and_source_identity_v1",
            "semantic_correctness_verified": None,
            "publisher_confirmed": item.validation.get("publisher_confirmed", False),
        },
    )


def admin_out(item):
    return dict(
        item=item_out(item),
        state=item.state,
        version=item.version,
        rubric=item.private_rubric,
        validation_details=item.validation,
    )


def create_item(db, actor, body):
    lock_owner(db, actor)
    library.validate_locator(db, actor, body.source)
    previous = (
        practice_item(db, actor, body.previous_item_id, True) if body.previous_item_id else None
    )
    if previous:
        db.refresh(previous, with_for_update=True)
        latest = db.scalar(
            select(PracticeItem)
            .where(PracticeItem.group_id == previous.group_id)
            .order_by(PracticeItem.item_revision.desc())
            .limit(1)
        )
        if latest.id != previous.id:
            raise AppError("CONFLICT", detail="Create a successor from the latest item revision.")
    payload = body.model_dump(exclude={"source", "rubric", "previous_item_id"})
    item = PracticeItem(
        workspace_id=actor.workspace_id,
        creator_id=actor.id,
        group_id=previous.group_id if previous else str(uuid4()),
        item_revision=previous.item_revision + 1 if previous else 1,
        previous_item_id=previous.id if previous else None,
        public_payload=payload,
        private_rubric=body.rubric.model_dump(),
        source=body.source.model_dump(),
        content_hash=library.fingerprint(body.model_dump()),
    )
    db.add(item)
    db.flush()
    return admin_out(item)


def create_proposed_item(db, actor, proposal, draft, provenance):
    """Internal generation-job seam: persist an unvalidated immutable proposal only.

    The caller owns bounded model execution. Generated keys never enter a public
    response; the normal administrator validation and publication steps remain.
    """
    if actor.role.name != "admin":
        raise AppError("FORBIDDEN")
    if (
        draft.source != proposal.source
        or draft.kind != proposal.kind
        or draft.concepts != proposal.concepts
        or draft.conditions != proposal.conditions
    ):
        raise AppError(
            "VALIDATION_FAILED", detail="The proposal changed its frozen source or requirements."
        )
    allowed = {"configuration_id", "provider", "model", "prompt_hash", "request_id"}
    if (
        not provenance
        or set(provenance) - allowed
        or any(not isinstance(v, str) or len(v) > 200 for v in provenance.values())
    ):
        raise AppError(
            "VALIDATION_FAILED", detail="A safe generation provenance record is required."
        )
    # An exact concept tag can still describe a paraphrased item, so this is
    # an administrator review signal rather than an automatic correctness
    # verdict. A live proposal once requested osmosis but asked only about
    # passive transport; that mismatch must remain visible before publishing.
    visible_and_key = " ".join(
        [draft.prompt]
        + [option.text for option in draft.options]
        + [draft.rubric.explanation]
        + [term for point in draft.rubric.required_points for term in point.terms]
    ).casefold()
    unmentioned_concepts = [
        concept for concept in proposal.concepts if concept.casefold() not in visible_and_key
    ]
    created = create_item(db, actor, draft)
    item = db.get(PracticeItem, created["item"]["id"])
    item.validation = {
        "status": "pending",
        "proposal_origin": "model_generated_unreviewed",
        "generation": dict(provenance),
        "semantic_correctness_verified": None,
        "unmentioned_requested_concepts": unmentioned_concepts,
    }
    db.flush()
    return admin_out(item)


def validate_item(db, actor, item_id):
    item = practice_item(db, actor, item_id, True)
    db.refresh(item, with_for_update=True)
    if item.state not in ("draft", "validated"):
        raise AppError(
            "CONFLICT", detail="Published item content is immutable; create a successor."
        )
    _, _, unit = library.validate_locator(db, actor, item.source)
    issues = grading.validate_rubric(
        item.public_payload["kind"], item.public_payload["options"], item.private_rubric
    )
    item.validation = dict(
        **{
            k: v
            for k, v in item.validation.items()
            if k in ("proposal_origin", "generation", "unmentioned_requested_concepts")
        },
        status="failed" if issues else "passed",
        issues=issues,
        checked_at=stamp(utcnow()),
        section_id=library.section_id(unit.processing_id, unit.section),
        source_text_hash=library.text_hash(unit.cleaned_text),
        semantic_correctness_verified=None,
        publisher_confirmed=False,
    )
    item.state = "draft" if issues else "validated"
    item.version += 1
    db.flush()
    return admin_out(item)


def publish_item(db, actor, item_id, body):
    item = practice_item(db, actor, item_id, True)
    db.refresh(item, with_for_update=True)
    cas(item, body.expected_version)
    library.validate_locator(db, actor, item.source)
    if (
        item.state != "validated"
        or item.validation.get("status") != "passed"
        or not body.confirm_source_and_solvability
    ):
        raise AppError(
            "CONFLICT",
            detail="Validate this revision and explicitly confirm source support and solvability before publishing.",
        )
    item.validation = {
        **item.validation,
        "publisher_confirmed": True,
        "published_by": actor.id,
        "published_at": stamp(utcnow()),
    }
    item.state = "published"
    item.version += 1
    db.flush()
    return admin_out(item)


def get_progress(db, actor, item, create=False):
    row = db.scalar(
        select(PracticeProgress)
        .where(PracticeProgress.owner_id == actor.id, PracticeProgress.item_id == item.id)
        .with_for_update()
    )
    if row is None and create:
        row = PracticeProgress(owner_id=actor.id, item_id=item.id, version=0)
        db.add(row)
        db.flush()
    return row


def effective_attempt_feedback(db, attempt):
    from .practice_assessment import effective_feedback

    return effective_feedback(db, attempt)


def attempt_out(row, db=None):
    from .practice_assessment import assessment_out

    return dict(
        id=row.id,
        item_id=row.item_id,
        item_revision=row.item_revision,
        response=row.response,
        feedback=row.feedback,
        created_at=stamp(row.created_at),
        progress_version=row.progress_version,
        assessment=assessment_out(db, row) if db is not None else None,
    )


def progress_out(db, actor, item, progress=None):
    progress = progress or get_progress(db, actor, item)
    steps = item.private_rubric.get("steps", [])
    current = progress.current_step if progress else 1
    attempts = list(
        db.scalars(
            select(PracticeAttempt)
            .where(PracticeAttempt.owner_id == actor.id, PracticeAttempt.item_id == item.id)
            .order_by(PracticeAttempt.created_at, PracticeAttempt.id)
        )
    )
    active_step = (
        steps[current - 1] if steps and (not progress or progress.state != "completed") else None
    )
    from .tutoring import linked_task

    task = linked_task(db, actor, progress) if progress else None
    return dict(
        item_id=item.id,
        tutor_session_id=task.session_id if task else None,
        tutor_task_id=task.id if task else None,
        version=progress.version if progress else 0,
        current_step=current,
        current_step_prompt=active_step["prompt"] if active_step else None,
        current_step_response_kind=("numeric" if active_step.get("numeric") else "text")
        if active_step
        else None,
        expected_unit=active_step["numeric"]["unit"]
        if active_step and active_step.get("numeric")
        else None,
        total_steps=len(steps) or 1,
        help_level=progress.help_level if progress else 0,
        state=progress.state if progress else "awaiting_attempt",
        attempts=[attempt_out(a, db) for a in attempts],
        hints=progress.shown_hints if progress else [],
        full_explanation=item.private_rubric["explanation"]
        if progress and progress.full_explanation
        else None,
    )


def validate_attempt_goal(db, actor, item, goal):
    sections = set(db.scalars(select(StudyUnit.section_id).where(StudyUnit.goal_id == goal.id)))
    if (
        goal.owner_id != actor.id
        or goal.document_id != item.source["document_id"]
        or goal.release_id != item.source["release_id"]
        or item.validation.get("section_id") not in sections
    ):
        raise AppError(
            "VALIDATION_FAILED", detail="The practice source is outside the selected goal."
        )


def submit_attempt(db, actor, item_id, body, settings=None):
    lock_owner(db, actor)
    item = practice_item(db, actor, item_id)
    body_hash = library.fingerprint(
        {"item_id": item_id, **body.model_dump(exclude={"idempotency_key"})}
    )
    prior = db.scalar(
        select(PracticeAttempt).where(
            PracticeAttempt.owner_id == actor.id,
            PracticeAttempt.idempotency_key == body.idempotency_key,
        )
    )
    if prior:
        if prior.body_hash != body_hash:
            raise AppError("IDEMPOTENCY_CONFLICT")
        return attempt_out(prior, db)
    goal = None
    if body.goal_id:
        goal = owned(db, StudyGoal, body.goal_id, actor)
        validate_attempt_goal(db, actor, item, goal)
    row = get_progress(db, actor, item, True)
    cas(row, body.expected_version)
    kind = item.public_payload["kind"]
    if kind in ("mcq", "multiselect"):
        ids = {o["id"] for o in item.public_payload["options"]}
        if (
            not set(body.response.selection) <= ids
            or len(set(body.response.selection)) != len(body.response.selection)
            or (kind == "mcq" and len(body.response.selection) > 1)
        ):
            raise AppError(
                "VALIDATION_FAILED", detail="Select valid distinct options for this question."
            )
    if kind == "step" and row.state == "completed":
        raise AppError(
            "CONFLICT", detail="This step sequence is complete. Start a related practice item."
        )
    result = grading.grade(kind, body.response, item.private_rubric, row.current_step)
    row.version += 1
    attempt = PracticeAttempt(
        owner_id=actor.id,
        item_id=item.id,
        progress_id=row.id,
        goal_id=body.goal_id,
        idempotency_key=body.idempotency_key,
        body_hash=body_hash,
        item_revision=item.item_revision,
        response=body.response.model_dump(),
        feedback=result,
        progress_version=row.version,
    )
    db.add(attempt)
    db.flush()
    pending = result["outcome"] == "pending_review"
    if pending:
        review = db.scalar(
            select(ReviewEntry).where(
                ReviewEntry.owner_id == actor.id, ReviewEntry.item_id == item.id
            )
        )
        if review is not None:
            review.attempt_count += 1
            review.version += 1
    else:
        apply_attempt_effects(db, actor, item, attempt, row, result)
    event(
        db,
        actor,
        "practice_attempt",
        attempt.id,
        item_id=item.id,
        goal_id=body.goal_id,
        outcome=result["outcome"],
        error_categories=result["error_categories"],
        current_step=row.current_step,
        semantic_correctness_verified=None,
    )
    if not pending:
        record_practice_memory(db, actor, item, attempt)
    from .tutoring import synchronize

    synchronize(db, actor, item, row)
    if not pending:
        return attempt_out(attempt, db)
    from . import practice_assessment

    reservation = practice_assessment.reservation_details(db, actor, item, attempt, row, goal)
    prepared, failure = None, None
    try:
        if settings is None or (goal and goal.state != "active"):
            raise AppError("MODEL_UNAVAILABLE")
        prepared = practice_assessment.prepare(db, settings, actor, item, attempt, row, reservation)
        reservation.update(prepared.metadata, reserved_calls=1)
    except Exception:
        failure = "configuration_or_context_unavailable"
    db.add(
        LearningRecord(
            id=practice_assessment.operation_id(attempt.id),
            owner_id=actor.id,
            kind="practice_assessment_started",
            object_id=attempt.id,
            details=reservation,
        )
    )
    attempt_id = attempt.id
    db.commit()
    return practice_assessment.run(db, settings, actor, attempt_id, reservation, prepared, failure)


def apply_attempt_effects(db, actor, item, attempt, row, result):
    """Only a bounded rule grade or an applied model result changes grade-derived state."""
    if result["outcome"] == "pending_review":
        return
    kind = item.public_payload["kind"]
    if result["outcome"] == "correct":
        if kind == "step" and row.current_step < len(item.private_rubric["steps"]):
            row.current_step += 1
            row.help_level = 0
        else:
            row.state = "completed"
    elif kind != "step":
        row.state = "awaiting_attempt"
    attempts = list(
        db.scalars(
            select(PracticeAttempt).where(
                PracticeAttempt.owner_id == actor.id, PracticeAttempt.item_id == item.id
            )
        )
    )
    review = db.scalar(
        select(ReviewEntry).where(ReviewEntry.owner_id == actor.id, ReviewEntry.item_id == item.id)
    )
    if review is None:
        review = ReviewEntry(
            owner_id=actor.id,
            item_id=item.id,
            attempt_count=0,
            correct_count=sum(
                effective_attempt_feedback(db, a)["outcome"] == "correct"
                for a in attempts
                if a.id != attempt.id
            ),
        )
        db.add(review)
    review.attempt_count = max(review.attempt_count, len(attempts))
    review.correct_count += int(result["outcome"] == "correct")
    days = min(14, 2 ** min(review.correct_count, 4)) if result["outcome"] == "correct" else 1
    review.due_at = utcnow() + dt.timedelta(days=days)
    review.error_categories = result["error_categories"]
    review.scheduling_reason = (
        f"Last graded attempt {result['outcome']}; review after {days} day(s)."
    )
    if review.version is not None:
        review.version += 1


def record_practice_memory(db, actor, item, attempt, feedback=None, assessment_id=None):
    """Opt-in measured practice provenance; never copy the private rubric into memory."""
    result = feedback or effective_attempt_feedback(db, attempt)
    if result["outcome"] == "pending_review":
        return
    from app.modules.learning_state import memory, memory_v2

    settings = memory.settings_for(db, actor.id, lock=True)
    if not settings.enabled:
        return
    write_event = memory_v2.source_event(db, actor.id)
    topics = ", ".join(item.public_payload["concepts"])[:130]
    operation = {
        "operation": "ADD",
        "category": "assessment_performance",
        "field_key": "assessment_result",
        "scope": topics + " practice " + attempt.id,
        "content": f"One recorded practice attempt on {topics} was {result['outcome']} under {result.get('grading_method', 'deterministic_rules_v1')}. This does not establish general mastery or independent semantic verification.",
        "source_quote": "",
        "expires_at": None,
    }
    memory_v2.apply_operations(
        db,
        actor.id,
        write_event,
        [operation],
        provenance={
            "kind": "practice_attempt",
            "practice_item_id": item.id,
            "practice_attempt_id": attempt.id,
            "item_revision": item.item_revision,
            "verification": "model_assessed_unverified"
            if assessment_id
            else "automatic_rubric_evaluated",
            "assessment_id": assessment_id,
            "grading_method": result.get("grading_method", "deterministic_rules_v1"),
            "outcome": result["outcome"],
            "error_categories": result["error_categories"],
            "semantic_correctness_verified": None,
        },
    )


def help_for(db, actor, item_id, body):
    lock_owner(db, actor)
    item = practice_item(db, actor, item_id)
    row = get_progress(db, actor, item, True)
    cas(row, body.expected_version)
    if body.action == "full_explanation":
        row.full_explanation = True
    else:
        rubric = item.private_rubric
        hints = (
            rubric["steps"][row.current_step - 1]["hints"]
            if rubric.get("steps")
            else rubric.get("hints", [])
        )
        if row.help_level >= len(hints):
            raise AppError(
                "CONFLICT",
                detail="No further authored hints are available; try a step or request the full explanation.",
            )
        row.shown_hints = [*row.shown_hints, hints[row.help_level]]
        row.help_level += 1
    row.version += 1
    db.flush()
    event(
        db,
        actor,
        "practice_help",
        item.id,
        action=body.action,
        help_level=row.help_level,
        learning_claim="disclosed_help_only",
    )
    from .tutoring import synchronize

    synchronize(db, actor, item, row)
    return progress_out(db, actor, item, row)


def review_out(db, actor, row):
    if row.note_id is not None:
        note = owned(db, StudyNote, row.note_id, actor)
        if note.kind != "review_card":
            raise AppError("NOT_FOUND")
        if note.source:
            library.validate_locator(db, actor, note.source)
        if note.answer_id:
            _owned_answer_reference(db, actor, note.answer_id)
        return dict(
            id=row.id,
            target_type="personal_review_card",
            item_id=None,
            note_id=note.id,
            card_content=note.content,
            card_source=note.source,
            title=note.title,
            concepts=note.concepts,
            due_at=stamp(row.due_at),
            error_categories=row.error_categories,
            attempt_count=row.attempt_count,
            correct_count=row.correct_count,
            suggested_item_id=None,
            scheduling_reason=row.scheduling_reason,
            version=row.version,
            recent_attempt_count=0,
            recent_error_counts={},
        )
    if row.item_id is None:
        raise AppError("SOURCE_UNAVAILABLE")
    item = practice_item(db, actor, row.item_id)
    concepts = set(item.public_payload["concepts"])
    suggestion = None
    for other in db.scalars(
        select(PracticeItem)
        .where(
            PracticeItem.workspace_id == actor.workspace_id,
            PracticeItem.state == "published",
            PracticeItem.id != item.id,
        )
        .order_by(PracticeItem.created_at, PracticeItem.id)
    ):
        if other.group_id != item.group_id and concepts.intersection(
            other.public_payload["concepts"]
        ):
            try:
                library.validate_locator(db, actor, other.source)
            except AppError:
                continue
            suggestion = other.id
            break
    all_attempts = list(
        db.scalars(
            select(PracticeAttempt)
            .where(PracticeAttempt.owner_id == actor.id, PracticeAttempt.item_id == row.item_id)
            .order_by(PracticeAttempt.created_at.desc(), PracticeAttempt.id.desc())
        )
    )
    assessed = [(a, effective_attempt_feedback(db, a)) for a in all_attempts]
    graded = [(a, f) for a, f in assessed if f["outcome"] != "pending_review"]
    recent = assessed[:3]
    recent_graded = graded[:3]
    errors = Counter(
        code for _, feedback in recent_graded for code in set(feedback["error_categories"])
    )
    return dict(
        id=row.id,
        target_type="practice_item",
        item_id=row.item_id,
        note_id=None,
        card_content=None,
        card_source=None,
        title=item.public_payload["title"],
        concepts=item.public_payload["concepts"],
        due_at=stamp(row.due_at),
        error_categories=row.error_categories,
        attempt_count=row.attempt_count,
        correct_count=row.correct_count,
        graded_count=len(graded),
        pending_count=len(assessed) - len(graded),
        suggested_item_id=suggestion,
        scheduling_reason=row.scheduling_reason,
        version=row.version,
        recent_attempt_count=len(recent),
        recent_graded_count=len(recent_graded),
        recent_pending_count=sum(feedback["outcome"] == "pending_review" for _, feedback in recent),
        recent_error_counts=dict(errors),
    )


def record_review_card(db, actor, review_id, body):
    """Record a learner's own recall judgment without asserting assessed mastery."""
    lock_owner(db, actor)
    row = owned(db, ReviewEntry, review_id, actor, True)
    if row.note_id is None:
        raise AppError(
            "VALIDATION_FAILED", detail="Only personal review cards accept recall reports."
        )
    review_out(db, actor, row)  # Recheck note ownership and live source availability.
    cas(row, body.expected_version)
    row.attempt_count += 1
    if body.outcome == "recalled":
        row.correct_count += 1
        days = min(14, 2 ** min(row.correct_count, 4))
        row.error_categories = []
        row.scheduling_reason = (
            f"Self-reported recall; review after {days} day(s). No graded mastery inferred."
        )
    else:
        days = 1
        row.error_categories = ["self_reported_not_recalled"]
        row.scheduling_reason = (
            "Self-reported difficulty; review after 1 day. No graded mastery inferred."
        )
    row.due_at = utcnow() + dt.timedelta(days=days)
    row.version += 1
    db.flush()
    event(
        db,
        actor,
        "review_card_self_reported",
        row.id,
        note_id=row.note_id,
        outcome=body.outcome,
        interval_days=days,
        verification="learner_self_report",
    )
    return review_out(db, actor, row)


def note_out(row, db=None, actor=None):
    metadata = None
    if row.source and db is not None:
        try:
            _, sources, unit = library.validate_locator(db, actor, row.source)
            metadata = dict(
                book_title=sources[0][1].title,
                section_title=unit.section,
                physical_page=unit.page,
                source_url=sources[0][1].source_url,
            )
        except AppError as exc:
            if exc.code not in ("EVIDENCE_UNAVAILABLE", "SOURCE_UNAVAILABLE"):
                raise
    return dict(
        id=row.id,
        title=row.title,
        content=row.content,
        kind=row.kind,
        source=row.source,
        answer_id=row.answer_id,
        goal_id=row.goal_id,
        concepts=row.concepts,
        version=row.version,
        created_at=stamp(row.created_at),
        updated_at=stamp(row.updated_at),
        source_metadata=metadata,
    )


def _owned_answer_reference(db, actor, answer_id):
    answer = db.scalar(
        select(Answer)
        .join(AnswerRequest, AnswerRequest.id == Answer.request_id)
        .where(Answer.id == answer_id, AnswerRequest.owner_id == actor.id)
    )
    if answer is None:
        raise AppError("NOT_FOUND")
    request = db.get(AnswerRequest, answer.request_id)
    if request.session_id:
        session = db.get(ChatSession, request.session_id)
        if (
            session is None
            or session.user_id != actor.id
            or session.workspace_id != actor.workspace_id
            or session.deleted_at is not None
        ):
            raise AppError("NOT_FOUND")
    return answer


def create_note(db, actor, body):
    if body.kind == "review_card" and not body.content.strip():
        raise AppError("VALIDATION_FAILED", detail="A review card needs content to reveal.")
    if body.source:
        library.validate_locator(db, actor, body.source)
    if body.answer_id:
        _owned_answer_reference(db, actor, body.answer_id)
    if body.goal_id:
        owned(db, StudyGoal, body.goal_id, actor)
    row = StudyNote(owner_id=actor.id, **body.model_dump())
    db.add(row)
    db.flush()
    if row.kind == "review_card":
        db.add(
            ReviewEntry(
                owner_id=actor.id,
                note_id=row.id,
                due_at=utcnow(),
                error_categories=[],
                attempt_count=0,
                correct_count=0,
                scheduling_reason="Personal review card created; due now until reviewed or rescheduled.",
            )
        )
    event(db, actor, "note_created", row.id, kind_of_note=row.kind)
    return note_out(row, db, actor)


def edit_note(db, actor, note_id, body):
    row = owned(db, StudyNote, note_id, actor, True)
    cas(row, body.expected_version)
    for field in ("title", "content", "concepts"):
        value = getattr(body, field)
        if value is not None:
            setattr(row, field, value)
    row.version += 1
    db.flush()
    event(db, actor, "note_updated", row.id, note_version=row.version)
    return note_out(row, db, actor)


def delete_note(db, actor, note_id, expected_version):
    row = owned(db, StudyNote, note_id, actor, True)
    cas(row, expected_version)
    review = db.scalar(
        select(ReviewEntry).where(ReviewEntry.owner_id == actor.id, ReviewEntry.note_id == row.id)
    )
    if review is not None:
        db.delete(review)
        db.flush()
    event(db, actor, "note_deleted", row.id)
    db.delete(row)
    return {"deleted": True}


def _export_line(value):
    """Keep source metadata on one line in both Markdown and DOCX exports."""
    return " ".join(str(value or "").split())


def _saved_answer_citations(db, actor, answer_id):
    """Export only published citations that remain visible to the note owner."""
    answer = db.get(Answer, answer_id)
    request = db.get(AnswerRequest, answer.request_id) if answer else None
    if request is None or request.owner_id != actor.id:
        return ["The saved answer is currently unavailable.", ""]
    if request.session_id:
        session = db.get(ChatSession, request.session_id)
        if (
            session is None
            or session.user_id != actor.id
            or session.workspace_id != actor.workspace_id
            or session.deleted_at is not None
        ):
            return ["The saved answer is currently unavailable.", ""]

    from app.modules.learning_state import sources

    response = answer.response if isinstance(answer.response, dict) else {}
    response_citations = response.get("citations", [])
    cited_ids = (
        {value for value in response_citations if isinstance(value, str)}
        if isinstance(response_citations, list)
        else set()
    )
    presentation = sources.presentation_for(db, answer.id)
    visible_ids = cited_ids.copy()
    if presentation is not None:
        visible_ids &= {
            view["evidence_id"]
            for view in sources.visible_views(db, presentation)
            if isinstance(view, dict) and isinstance(view.get("evidence_id"), str)
        }
    output = ["Saved answer reference: " + answer.id]
    cited = list(
        db.scalars(
            select(Evidence)
            .join(Citation, Citation.evidence_id == Evidence.id)
            .where(Citation.answer_id == answer.id, Evidence.answer_id == answer.id)
            .order_by(Evidence.evidence_id)
        )
    )
    if not cited or not cited_ids:
        return output + ["This saved answer has no currently displayable textbook citations.", ""]

    for evidence in cited:
        if evidence.evidence_id not in cited_ids:
            continue
        if evidence.evidence_id not in visible_ids:
            output.append("A saved answer citation is currently unavailable.")
            continue
        item = evidence.payload if isinstance(evidence.payload, dict) else {}
        chunk = db.get(Chunk, evidence.chunk_id)
        document = db.get(Document, evidence.document_id)
        owner = db.get(User, document.owner_id) if document else None
        run = db.get(ProcessingRun, chunk.processing_id) if chunk else None
        version = db.get(DocumentVersion, run.document_version_id) if run else None
        membership = (
            db.get(ReleaseChunk, (request.release_id, evidence.chunk_id))
            if request.release_id
            else None
        )
        valid = (
            document is not None
            and document.active
            and not document.revoked
            and owner is not None
            and owner.workspace_id == actor.workspace_id
            and chunk is not None
            and chunk.document_id == document.id
            and run is not None
            and version is not None
            and version.document_id == document.id
            and membership is not None
            and item.get("asset_id") == document.id
            and item.get("chunk_id") == chunk.id
            and item.get("processing_id") == run.id
            and item.get("section") == chunk.section
            and item.get("pages") == chunk.pages
            and all(key in item for key in ("text", "text_hash"))
            and sources.exact_evidence(chunk, item)
        )
        if not valid:
            output.append("A saved answer citation is currently unavailable.")
            continue
        assert run is not None and version is not None  # Checked with the source identity above.
        page_label = (
            "physical PDF page(s)" if version.media_type == "application/pdf" else "source page(s)"
        )
        pages = ", ".join(str(page) for page in chunk.pages)
        output.extend(
            [
                f"Actual cited source {evidence.evidence_id}: {_export_line(document.title)}; "
                f"edition {_export_line(document.edition)}; {page_label} {pages}; "
                f"section {_export_line(chunk.section)}.",
                f"Locator: release {request.release_id}; document {document.id}; "
                f"version {version.id}; processing {run.id}; chunk {chunk.id}; "
                f"evidence {evidence.evidence_id}.",
                f"Original SHA256: {version.raw_hash}; cited chunk SHA256: {chunk.text_hash}.",
                f"License: {_export_line(document.license)}",
            ]
        )
        if presentation is None or presentation.payload.get("teaching_mode") != "hint":
            output.append(f"Source URL: {_export_line(document.source_url)}")
    if len(output) == 1:
        output.append("This saved answer has no currently displayable textbook citations.")
    return output + [""]


def export_notes(db, actor):
    output = [
        "# Personal learning notes",
        "",
        "These notes are personal learning material, not verified textbook evidence.",
        "",
    ]
    for row in db.scalars(
        select(StudyNote)
        .where(StudyNote.owner_id == actor.id)
        .order_by(StudyNote.created_at, StudyNote.id)
    ):
        output.extend(["## " + row.title.replace("\n", " "), "", row.content, ""])
        if row.source:
            try:
                _, rows, unit = library.validate_locator(db, actor, row.source)
                document, version = rows[0][1], rows[0][3]
                output.extend(
                    [
                        f"Source: {document.title}; edition {document.edition}; physical page {unit.page}; section {unit.section}.",
                        f"Original SHA256: {version.raw_hash}; source unit SHA256: {row.source['text_hash']}.",
                        f"Source URL: {document.source_url}",
                        f"License: {document.license}",
                        "",
                    ]
                )
            except AppError as exc:
                if exc.code not in ("EVIDENCE_UNAVAILABLE", "SOURCE_UNAVAILABLE"):
                    raise
                output.extend(
                    [
                        "The saved textbook source is currently unavailable.",
                        "Saved source unit SHA256: " + row.source["text_hash"],
                        "",
                    ]
                )
        if row.answer_id:
            output.extend(_saved_answer_citations(db, actor, row.answer_id))
    return "\n".join(output)
