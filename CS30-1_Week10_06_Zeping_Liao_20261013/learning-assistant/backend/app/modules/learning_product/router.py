"""Authenticated learning workspace and separate administrator publication controls."""

from typing import Literal
from app.modules.learning_product.note_docx import notes_docx
from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from contracts.http import Envelope
from contracts.study import (
    BookOut,
    SectionOut,
    ReadingPageOut,
    ReadingPositionInput,
    ReadingPositionOut,
    GoalCreate,
    GoalUpdate,
    GoalOut,
    ConceptRelationProposal,
    ConceptRelationReview,
    ConceptRelationAdminOut,
    VersionInput,
    PracticeDraft,
    PracticeProposalInput,
    PracticeOut,
    PracticeAdminOut,
    PublishInput,
    AttemptInput,
    AttemptOut,
    PracticeProgressOut,
    PracticeTutorInput,
    PracticeTutorOut,
    HelpInput,
    ReviewOut,
    ReviewSchedule,
    ReviewCardAction,
    NoteCreate,
    NoteUpdate,
    NoteOut,
    LearningRecordOut,
    NotesExportOut,
)
from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.db.base import utcnow
from app.core.responses import ok
from app.core.exceptions import AppError
from app.core.config import Settings, get_settings
from app.modules.identity.models import User
from . import library, relations, service
from .visual_catalog_router import router as visual_catalog_router
from .models import (
    ReadingPosition,
    StudyGoal,
    StudyUnit,
    PracticeItem,
    PracticeAttempt,
    ReviewEntry,
    StudyNote,
    LearningRecord,
)


router = APIRouter(tags=["learning workspace"])
router.include_router(visual_catalog_router)


def committed(db, value):
    db.commit()
    return ok(value)


@router.get("/learning/library", response_model=Envelope[list[BookOut]])
def library_books(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(library.books(db, actor))


@router.get("/learning/library/{document_id}/sections", response_model=Envelope[list[SectionOut]])
def library_sections(
    document_id: str,
    query: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(library.sections(db, actor, document_id, query))


@router.get("/learning/library/{document_id}/units", response_model=Envelope[ReadingPageOut])
def library_units(
    document_id: str,
    section_id: str | None = None,
    source_unit_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(
        library.reading_page(db, actor, document_id, section_id, offset, limit, source_unit_id)
    )


@router.get("/learning/reading-position", response_model=Envelope[list[ReadingPositionOut]])
def reading_positions(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(
        [
            service.position_out(p)
            for p in db.scalars(
                select(ReadingPosition)
                .where(ReadingPosition.owner_id == actor.id)
                .order_by(ReadingPosition.updated_at.desc())
            )
        ]
    )


@router.put("/learning/reading-position", response_model=Envelope[ReadingPositionOut])
def reading_position(
    body: ReadingPositionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.save_position(db, actor, body))


@router.get("/learning/goals", response_model=Envelope[list[GoalOut]])
def goals(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(
        [
            service.goal_out(db, actor, g)
            for g in db.scalars(
                select(StudyGoal)
                .where(StudyGoal.owner_id == actor.id)
                .order_by(StudyGoal.created_at.desc())
            )
        ]
    )


@router.post("/learning/goals", status_code=201, response_model=Envelope[GoalOut])
def create_goal(
    body: GoalCreate, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    return committed(db, service.create_goal(db, actor, body))


@router.get("/learning/goals/{goal_id}", response_model=Envelope[GoalOut])
def goal(goal_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(service.goal_out(db, actor, service.owned(db, StudyGoal, goal_id, actor)))


@router.patch("/learning/goals/{goal_id}", response_model=Envelope[GoalOut])
def edit_goal(
    goal_id: str,
    body: GoalUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.update_goal(db, actor, goal_id, body))


@router.post("/learning/goals/{goal_id}/units/{unit_id}/read", response_model=Envelope[GoalOut])
def mark_read(
    goal_id: str,
    unit_id: str,
    body: VersionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.mark_read(db, actor, goal_id, unit_id, body.expected_version))


@router.get(
    "/admin/learning/concept-relations",
    response_model=Envelope[list[ConceptRelationAdminOut]],
)
def concept_relations(
    state: Literal["proposed", "approved", "rejected"] | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(relations.list_proposals(db, actor, state))


@router.post(
    "/admin/learning/concept-relations",
    status_code=201,
    response_model=Envelope[ConceptRelationAdminOut],
)
def propose_concept_relation(
    body: ConceptRelationProposal,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return committed(db, relations.propose(db, actor, body))


@router.post(
    "/admin/learning/concept-relations/{relation_id}/review",
    response_model=Envelope[ConceptRelationAdminOut],
)
def review_concept_relation(
    relation_id: str,
    body: ConceptRelationReview,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return committed(db, relations.review(db, actor, relation_id, body))


@router.get("/learning/practice", response_model=Envelope[list[PracticeOut]])
def practice_list(
    goal_id: str | None = None,
    section_id: str | None = None,
    unit_id: str | None = None,
    concept: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    goal = service.owned(db, StudyGoal, goal_id, actor) if goal_id else None
    sections = (
        set(db.scalars(select(StudyUnit.section_id).where(StudyUnit.goal_id == goal.id)))
        if goal
        else None
    )
    if unit_id:
        unit = db.scalar(
            select(StudyUnit)
            .join(StudyGoal, StudyGoal.id == StudyUnit.goal_id)
            .where(StudyUnit.id == unit_id, StudyGoal.owner_id == actor.id)
        )
        if unit is None or (goal and unit.goal_id != goal.id):
            raise AppError("NOT_FOUND")
        if section_id is not None and section_id != unit.section_id:
            raise AppError("VALIDATION_FAILED")
        section_id = unit.section_id
    result = []
    for item in db.scalars(
        select(PracticeItem)
        .where(PracticeItem.workspace_id == actor.workspace_id, PracticeItem.state == "published")
        .order_by(PracticeItem.created_at.desc())
    ):
        if goal and (
            item.source["document_id"] != goal.document_id
            or item.source["release_id"] != goal.release_id
        ):
            continue
        if sections is not None and item.validation.get("section_id") not in sections:
            continue
        if section_id and item.validation.get("section_id") != section_id:
            continue
        if concept and concept.casefold() not in {
            c.casefold() for c in item.public_payload["concepts"]
        }:
            continue
        try:
            library.validate_locator(db, actor, item.source)
        except AppError:
            continue
        result.append(service.item_out(item))
        if len(result) == 200:
            break
    return ok(result)


@router.get("/learning/practice/{item_id}", response_model=Envelope[PracticeOut])
def practice(item_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(service.item_out(service.practice_item(db, actor, item_id)))


@router.get("/learning/practice/{item_id}/progress", response_model=Envelope[PracticeProgressOut])
def progress(item_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(service.progress_out(db, actor, service.practice_item(db, actor, item_id)))


@router.get("/learning/practice/attempts/{attempt_id}", response_model=Envelope[AttemptOut])
def saved_attempt(
    attempt_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    return ok(service.attempt_out(service.owned(db, PracticeAttempt, attempt_id, actor), db))


@router.post("/learning/practice/{item_id}/attempts", response_model=Envelope[AttemptOut])
def attempt(
    item_id: str,
    body: AttemptInput,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.submit_attempt(db, actor, item_id, body, settings))


@router.post("/learning/practice/{item_id}/help", response_model=Envelope[PracticeProgressOut])
def help_for(
    item_id: str,
    body: HelpInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.help_for(db, actor, item_id, body))


@router.get("/learning/review", response_model=Envelope[list[ReviewOut]])
def reviews(
    due_only: bool = True, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    query = select(ReviewEntry).where(ReviewEntry.owner_id == actor.id)
    if due_only:
        query = query.where(ReviewEntry.due_at <= utcnow())
    result = []
    for row in db.scalars(query.order_by(ReviewEntry.due_at).limit(200)):
        try:
            result.append(service.review_out(db, actor, row))
        except AppError as exc:
            if exc.code not in ("NOT_FOUND", "EVIDENCE_UNAVAILABLE", "SOURCE_UNAVAILABLE"):
                raise
    return ok(result)


@router.post("/learning/practice/{item_id}/tutor", response_model=Envelope[PracticeTutorOut])
def practice_tutor(
    item_id: str,
    body: PracticeTutorInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    from .goal_tutoring import open_tutor

    return committed(db, open_tutor(db, actor, item_id, body))


@router.post("/learning/review/{review_id}/reschedule", response_model=Envelope[ReviewOut])
def reschedule(
    review_id: str,
    body: ReviewSchedule,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    import datetime as dt

    row = service.owned(db, ReviewEntry, review_id, actor, True)
    service.review_out(db, actor, row)
    service.cas(row, body.expected_version)
    row.due_at = utcnow() + dt.timedelta(days=body.days)
    row.scheduling_reason = f"Learner scheduled review after {body.days} day(s)."
    row.version += 1
    db.flush()
    return committed(db, service.review_out(db, actor, row))


@router.post("/learning/review/{review_id}/record", response_model=Envelope[ReviewOut])
def record_review_card(
    review_id: str,
    body: ReviewCardAction,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.record_review_card(db, actor, review_id, body))


@router.get("/learning/notes", response_model=Envelope[list[NoteOut]])
def notes(
    goal_id: str | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    query = select(StudyNote).where(StudyNote.owner_id == actor.id)
    if goal_id:
        service.owned(db, StudyGoal, goal_id, actor)
        query = query.where(StudyNote.goal_id == goal_id)
    return ok(
        [
            service.note_out(n, db, actor)
            for n in db.scalars(query.order_by(StudyNote.updated_at.desc()))
        ]
    )


@router.post("/learning/notes", status_code=201, response_model=Envelope[NoteOut])
def create_note(
    body: NoteCreate, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    return committed(db, service.create_note(db, actor, body))


@router.get("/learning/notes/export", response_model=Envelope[NotesExportOut])
def export_notes(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok({"markdown": service.export_notes(db, actor)})


@router.get("/learning/notes/export.docx")
def export_notes_docx(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    # Standard OOXML text-only export; no macros, embedded files, external relationships or HTML.
    markdown = service.export_notes(db, actor)
    return Response(
        notes_docx(markdown),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="learning-notes.docx"'},
    )


@router.patch("/learning/notes/{note_id}", response_model=Envelope[NoteOut])
def edit_note(
    note_id: str,
    body: NoteUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.edit_note(db, actor, note_id, body))


@router.delete("/learning/notes/{note_id}", response_model=Envelope[dict])
def delete_note(
    note_id: str,
    expected_version: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return committed(db, service.delete_note(db, actor, note_id, expected_version))


@router.post(
    "/learning/notes/{note_id}/review-card", status_code=201, response_model=Envelope[NoteOut]
)
def note_review_card(
    note_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    row = service.owned(db, StudyNote, note_id, actor)
    body = NoteCreate(
        title="Review " + row.title[:190],
        content="Recall and explain: " + row.content[:11970],
        kind="review_card",
        source=row.source,
        answer_id=row.answer_id,
        goal_id=row.goal_id,
        concepts=row.concepts,
    )
    return committed(db, service.create_note(db, actor, body))


@router.get("/learning/records", response_model=Envelope[list[LearningRecordOut]])
def records(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    from .practice_assessment import public_record_details

    return ok(
        [
            dict(
                id=r.id,
                kind=r.kind,
                object_id=r.object_id,
                details=public_record_details(r),
                created_at=service.stamp(r.created_at),
            )
            for r in db.scalars(
                select(LearningRecord)
                .where(LearningRecord.owner_id == actor.id)
                .order_by(LearningRecord.created_at.desc())
                .limit(limit)
            )
        ]
    )


@router.get("/admin/learning/practice", response_model=Envelope[list[PracticeAdminOut]])
def admin_practice(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    return ok(
        [
            service.admin_out(i)
            for i in db.scalars(
                select(PracticeItem)
                .where(PracticeItem.workspace_id == actor.workspace_id)
                .order_by(PracticeItem.created_at.desc())
                .limit(200)
            )
        ]
    )


@router.post("/admin/learning/practice", status_code=201, response_model=Envelope[PracticeAdminOut])
def draft_practice(
    body: PracticeDraft,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return committed(db, service.create_item(db, actor, body))


@router.post(
    "/admin/learning/practice-proposals", status_code=201, response_model=Envelope[PracticeAdminOut]
)
def propose_practice(
    body: PracticeProposalInput,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    from .proposals import propose

    value, replay = propose(db, settings, actor, body, idempotency_key)
    response.status_code = 200 if replay else 201
    return ok(value)


@router.post(
    "/admin/learning/practice/{item_id}/validate", response_model=Envelope[PracticeAdminOut]
)
def validate_practice(
    item_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    return committed(db, service.validate_item(db, actor, item_id))


@router.post(
    "/admin/learning/practice/{item_id}/publish", response_model=Envelope[PracticeAdminOut]
)
def publish_practice(
    item_id: str,
    body: PublishInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return committed(db, service.publish_item(db, actor, item_id, body))


@router.post("/admin/learning/practice/{item_id}/retire", response_model=Envelope[PracticeAdminOut])
def retire_practice(
    item_id: str,
    body: VersionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    row = service.practice_item(db, actor, item_id, True)
    db.refresh(row, with_for_update=True)
    service.cas(row, body.expected_version)
    row.state = "retired"
    row.version += 1
    db.flush()
    return committed(db, service.admin_out(row))
