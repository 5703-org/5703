"""Learning module persistence: chat sessions.

Questions / answers plug in on top of the pipeline executor.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base


class ChatSession(Base, AuditMixin):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active','archived')", name="ck_sessions_status"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New chat")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # Soft delete (Spec B28): filtered out by default, restorable by admins later.
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
