"""Learning persistence access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.learning.models import ChatSession


def create(db: Session, user_id: str, workspace_id: str, title: str) -> ChatSession:
    session = ChatSession(user_id=user_id, workspace_id=workspace_id, title=title)
    db.add(session)
    db.flush()
    return session


def get(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


def list_for_user(db: Session, user_id: str, status: str | None) -> list[ChatSession]:
    stmt = select(ChatSession).where(
        ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None)
    )
    if status in ("active", "archived"):
        stmt = stmt.where(ChatSession.status == status)
    return list(db.scalars(stmt.order_by(ChatSession.updated_at.desc())).all())
