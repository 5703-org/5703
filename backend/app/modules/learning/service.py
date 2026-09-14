"""Session lifecycle with object-level authorisation (Spec C07).

Other users' IDs always return NOT_FOUND - the API must not confirm
whether someone else's resource exists.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.base import utcnow
from app.modules.identity.models import User
from app.modules.learning import repository
from app.modules.learning.models import ChatSession
from app.modules.learning.schemas import SessionOut
from app.platform_core.events import publish_event


def get_owned(db: Session, session_id: str, user: User) -> ChatSession:
    session = repository.get(db, session_id)
    if session is None or session.deleted_at is not None or session.user_id != user.id:
        raise AppError("NOT_FOUND", detail="Session not found.")
    return session


def to_out(session: ChatSession) -> SessionOut:
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status,
        version=session.version,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def create_session(db: Session, user: User, title: str | None) -> ChatSession:
    session = repository.create(db, user.id, user.workspace_id, title or "New chat")
    publish_event(
        db,
        "learning.session.created",
        {"session_id": session.id, "user_id": user.id},
        workspace_id=user.workspace_id,
    )
    db.commit()
    return session


def rename_session(db: Session, session: ChatSession, title: str, version: int) -> ChatSession:
    db.refresh(session, with_for_update=True)
    if version != session.version:
        raise AppError("CONFLICT", detail="The session was modified elsewhere. Refresh and retry.")
    session.title = title
    session.version += 1
    db.add(session)
    db.commit()
    return session


def transition(db: Session, session: ChatSession, target: str) -> ChatSession:
    db.refresh(session, with_for_update=True)
    if session.status == target:
        return session  # idempotent: repeated calls are safe
    expected = "active" if target == "archived" else "archived"
    if session.status != expected:
        raise AppError(
            "CONFLICT", detail=f"Cannot move a session from {session.status} to {target}."
        )
    session.status = target
    if target == "archived":
        from app.modules.answering.service import active_job, cancel_job

        job = active_job(db, session.id)
        if job:
            cancel_job(db, job)
    session.version += 1
    db.add(session)
    db.commit()
    return session


def soft_delete(db: Session, session: ChatSession) -> None:
    db.refresh(session, with_for_update=True)
    from app.modules.answering.service import active_job, cancel_job

    job = active_job(db, session.id)
    if job:
        cancel_job(db, job)
    session.deleted_at = utcnow()
    session.version += 1
    db.add(session)
    db.commit()
