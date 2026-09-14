"""Basic account operations and credential revocation."""

from contracts.http import Envelope
from app.modules.identity.schemas import UserOut
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from contracts.models import Contract
from app.api.v1.deps import get_current_user, require_roles
from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity import repository, service
from app.modules.identity.models import User, StudentProfile

router = APIRouter(tags=["accounts"])


class PasswordChange(Contract):
    old_password: str
    new_password: str = Field(min_length=10, max_length=128)


class AccountCreate(Contract):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: Literal["student", "admin"] = "student"


class AccountUpdate(Contract):
    version: int
    status: Literal["active", "deactivated"] | None = None
    password: str | None = Field(default=None, min_length=10, max_length=128)


@router.post("/users/me/password", response_model=Envelope[dict[str, bool]])
def change_password(
    body: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    db.refresh(user, with_for_update={"of": User})
    if not verify_password(body.old_password, user.hashed_password):
        raise AppError("BAD_CREDENTIALS")
    user.hashed_password = hash_password(body.new_password)
    user.token_version += 1
    user.version += 1
    db.commit()
    return ok({"changed": True, "login_required": True})


@router.post("/admin/users", status_code=201, response_model=Envelope[UserOut])
def create_user(
    body: AccountCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    if repository.get_user_by_email(db, str(body.email)):
        raise AppError("CONFLICT", detail="An account already exists with this email.")
    role = repository.get_role_by_name(db, body.role)
    user = User(
        email=str(body.email).lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role_id=role.id,
        workspace_id=actor.workspace_id,
    )
    try:
        db.add(user)
        db.flush()
        db.add(StudentProfile(user_id=user.id))
        db.commit()
    except IntegrityError:
        # The unique index arbitrates concurrent first creates; a prior SELECT
        # cannot lock an email that has no row. Keep account/profile atomic.
        db.rollback()
        if repository.get_user_by_email(db, str(body.email)):
            raise AppError(
                "CONFLICT", detail="An account already exists with this email."
            ) from None
        raise
    return ok(service.to_user_out(user).model_dump())


@router.patch("/admin/users/{user_id}", response_model=Envelope[UserOut])
def update_user(
    user_id: str,
    body: AccountUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    user = repository.get_user(db, user_id)
    if not user or user.workspace_id != actor.workspace_id:
        raise AppError("NOT_FOUND")
    db.refresh(user, with_for_update={"of": User})
    if body.version != user.version:
        raise AppError("CONFLICT")
    if user.id == actor.id and body.status == "deactivated":
        raise AppError("CONFLICT", detail="An administrator cannot deactivate their own session.")
    if body.status:
        user.status = body.status
    if body.password:
        user.hashed_password = hash_password(body.password)
    user.token_version += 1
    user.version += 1
    db.commit()
    return ok(service.to_user_out(user).model_dump())
