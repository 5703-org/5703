"""Identity module persistence: Workspace, Role, User, StudentProfile.

Owns its tables; other modules must go through this module's services
instead of touching these tables directly (Spec K01).
"""

from __future__ import annotations

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base


class Workspace(Base, AuditMixin):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False, default="")


class User(Base, AuditMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active','deactivated')", name="ck_users_status"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)

    role: Mapped[Role] = relationship(lazy="joined")


class StudentProfile(Base, AuditMixin):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False, default="intermediate")
    style: Mapped[str] = mapped_column(String(30), nullable=False, default="concise")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
