"""Idempotent seed data (Spec B26, B31): default workspace, roles, demo users.

Run:  python -m scripts.seed
Safe to run repeatedly - existing rows are left untouched.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db import session as db_session
from app.db.base import Base
from app.modules.identity import repository
from app.modules.identity.models import Role, StudentProfile, User, Workspace
from app.modules.learning import models as _learning_models  # noqa: F401  (register tables)
from app.platform_core import models as _platform_models  # noqa: F401

DEFAULT_PASSWORD = "Passw0rd!"

ROLES = [
    ("student", "Standard learner account"),
    ("admin", "System administrator"),
    ("researcher", "Experiment and evaluation access"),
]

DEMO_USERS = [
    ("admin@example.com", "Demo Admin", "admin"),
    ("student@example.com", "Demo Student One", "student"),
    ("student2@example.com", "Demo Student Two", "student"),
]


def seed(db: Session) -> None:
    workspace = repository.get_workspace_by_slug(db, "default")
    if workspace is None:
        workspace = Workspace(name="Default Workspace", slug="default")
        db.add(workspace)
        db.flush()

    for name, description in ROLES:
        if repository.get_role_by_name(db, name) is None:
            db.add(Role(name=name, description=description))
    db.flush()

    for email, full_name, role_name in DEMO_USERS:
        if repository.get_user_by_email(db, email) is not None:
            continue
        role = repository.get_role_by_name(db, role_name)
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(DEFAULT_PASSWORD),
            role_id=role.id,
            workspace_id=workspace.id,
        )
        db.add(user)
        db.flush()
        db.add(StudentProfile(user_id=user.id))


def main() -> None:
    settings = Settings()
    engine = db_session.init_engine(settings.database_url)
    # Dev convenience: `alembic upgrade head` owns schema in real deployments.
    Base.metadata.create_all(engine)
    with db_session.session_scope() as db:
        seed(db)
    print(f"Seed complete against {settings.database_url}")


if __name__ == "__main__":
    main()
