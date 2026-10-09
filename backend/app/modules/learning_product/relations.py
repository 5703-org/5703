"""Quarantined concept-relation proposals and exact released-source review."""

from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.base import utcnow

from . import library
from .models import StudyConceptRelation


def _admin_out(row):
    return dict(
        id=row.id,
        document_id=row.document_id,
        release_id=row.release_id,
        from_section_id=row.from_section_id,
        to_section_id=row.to_section_id,
        from_concept=row.from_concept,
        to_concept=row.to_concept,
        relation_type=row.relation_type,
        source=row.source,
        source_quote=row.source_quote,
        source_quote_hash=row.source_quote_hash,
        reason=row.reason,
        state=row.state,
        proposer_id=row.proposer_id,
        reviewer_id=row.reviewer_id,
        reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
        review_note=row.review_note,
        version=row.version,
    )


def list_proposals(db, actor, state=None):
    query = select(StudyConceptRelation).where(
        StudyConceptRelation.workspace_id == actor.workspace_id
    )
    if state:
        query = query.where(StudyConceptRelation.state == state)
    return [
        _admin_out(row)
        for row in db.scalars(query.order_by(StudyConceptRelation.created_at.desc()).limit(200))
    ]


def _check_source(db, actor, source, quote):
    release, rows, unit = library.validate_locator(db, actor, source)
    value = source.model_dump() if hasattr(source, "model_dump") else source
    end = value["end"] if value.get("end") is not None else len(unit.cleaned_text)
    if unit.cleaned_text[value["start"] : end] != quote:
        raise AppError(
            "VALIDATION_FAILED", detail="The quotation must equal the exact pinned source range."
        )
    return release, rows, unit


def propose(db, actor, body):
    if body.document_id != body.source.document_id:
        raise AppError("VALIDATION_FAILED", detail="The proposal must use one textbook.")
    if body.from_section_id == body.to_section_id:
        raise AppError("VALIDATION_FAILED", detail="Choose two distinct published sections.")
    release, rows, _ = _check_source(db, actor, body.source, body.source_quote)
    _, _, units = library.book_data(db, actor, body.document_id, release.id)
    published_sections = {library.section_id(u.processing_id, u.section) for u in units}
    if {body.from_section_id, body.to_section_id} - published_sections:
        raise AppError(
            "VALIDATION_FAILED", detail="Both concepts must map to sections in this release."
        )
    if not rows or rows[0][1].id != body.document_id:
        raise AppError("EVIDENCE_UNAVAILABLE")
    existing = db.scalar(
        select(StudyConceptRelation.id).where(
            StudyConceptRelation.workspace_id == actor.workspace_id,
            StudyConceptRelation.release_id == release.id,
            StudyConceptRelation.from_section_id == body.from_section_id,
            StudyConceptRelation.to_section_id == body.to_section_id,
            StudyConceptRelation.relation_type == body.relation_type,
            StudyConceptRelation.state.in_(("proposed", "approved")),
        )
    )
    if existing:
        raise AppError("CONFLICT", detail="A proposal for this relation already exists.")
    row = StudyConceptRelation(
        workspace_id=actor.workspace_id,
        document_id=body.document_id,
        release_id=release.id,
        from_section_id=body.from_section_id,
        to_section_id=body.to_section_id,
        from_concept=body.from_concept.strip(),
        to_concept=body.to_concept.strip(),
        relation_type=body.relation_type,
        source=body.source.model_dump(),
        source_quote=body.source_quote,
        source_quote_hash=library.text_hash(body.source_quote),
        reason=body.reason.strip(),
        state="proposed",
        proposer_id=actor.id,
    )
    db.add(row)
    db.flush()
    return _admin_out(row)


def review(db, actor, relation_id, body):
    row = db.scalar(
        select(StudyConceptRelation)
        .where(
            StudyConceptRelation.id == relation_id,
            StudyConceptRelation.workspace_id == actor.workspace_id,
        )
        .with_for_update()
    )
    if row is None:
        raise AppError("NOT_FOUND")
    if row.version != body.expected_version or row.state != "proposed":
        raise AppError("CONFLICT", detail="The proposal changed. Refresh before reviewing.")
    if body.decision == "approve":
        if not body.verified_source_support:
            raise AppError(
                "VALIDATION_FAILED",
                detail="Approval requires an explicit review of the quoted source and relation.",
            )
        _check_source(db, actor, row.source, row.source_quote)
        if library.text_hash(row.source_quote) != row.source_quote_hash:
            raise AppError("EVIDENCE_UNAVAILABLE", detail="The proposal quotation changed.")
        row.state = "approved"
    else:
        row.state = "rejected"
    row.reviewer_id = actor.id
    row.reviewed_at = utcnow()
    row.review_note = body.review_note.strip()
    row.version += 1
    db.flush()
    return _admin_out(row)


def for_goal(db, actor, goal, unit_results):
    by_section = {unit["section_id"]: unit["id"] for unit in unit_results}
    if len(by_section) < 2:
        return []
    rows = list(
        db.scalars(
            select(StudyConceptRelation).where(
                StudyConceptRelation.workspace_id == actor.workspace_id,
                StudyConceptRelation.document_id == goal.document_id,
                StudyConceptRelation.release_id == goal.release_id,
                StudyConceptRelation.state == "approved",
                StudyConceptRelation.from_section_id.in_(by_section),
                StudyConceptRelation.to_section_id.in_(by_section),
            )
        )
    )
    if not rows:
        return []
    try:
        _, book_rows, units = library.book_data(db, actor, goal.document_id, goal.release_id)
    except AppError as exc:
        if exc.code in ("SOURCE_UNAVAILABLE", "EVIDENCE_UNAVAILABLE"):
            return []
        raise
    document = book_rows[0][1]
    unit_by_id = {unit.id: unit for unit in units}
    out = []
    for row in rows:
        source = row.source
        if (
            source.get("release_id") != row.release_id
            or source.get("document_id") != goal.document_id
            or row.reviewed_at is None
        ):
            continue
        unit = unit_by_id.get(source.get("source_unit_id"))
        if unit is None or source.get("processing_id") != unit.processing_id:
            continue
        if source.get("text_hash") != library.text_hash(unit.cleaned_text):
            continue
        start, end = source.get("start"), source.get("end")
        if end is None:
            end = len(unit.cleaned_text)
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(unit.cleaned_text)
            or unit.cleaned_text[start:end] != row.source_quote
            or library.text_hash(row.source_quote) != row.source_quote_hash
        ):
            continue
        out.append(
            dict(
                id=row.id,
                relation_type=row.relation_type,
                from_unit_id=by_section[row.from_section_id],
                to_unit_id=by_section[row.to_section_id],
                from_concept=row.from_concept,
                to_concept=row.to_concept,
                reason=row.reason,
                source=source,
                source_quote=row.source_quote,
                source_quote_hash=row.source_quote_hash,
                source_book=document.title,
                source_edition=document.edition,
                source_section=unit.section,
                source_page=unit.page,
                source_url=document.source_url,
                reviewed_at=row.reviewed_at.isoformat(),
                provenance="administrator_reviewed_released_source",
            )
        )
    return out
