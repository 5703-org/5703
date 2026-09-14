"""Identity persistence access. SQL lives here, never in routers (Spec A03)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.models import Role, StudentProfile, User, Workspace


def get_workspace_by_slug(db: Session, slug: str) -> Workspace | None:
    return db.scalar(select(Workspace).where(Workspace.slug == slug))


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def list_users(db: Session, workspace_id: str | None = None) -> list[User]:
    query = select(User)
    if workspace_id is not None:
        query = query.where(User.workspace_id == workspace_id)
    return list(db.scalars(query.order_by(User.created_at, User.id)).all())


def get_profile(db: Session, user_id: str) -> StudentProfile | None:
    return db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))


def create_default_profile(db: Session, user_id: str) -> StudentProfile:
    profile = StudentProfile(user_id=user_id)
    db.add(profile)
    db.flush()
    return profile
