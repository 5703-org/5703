"""Identity endpoints: auth, current user, admin user list, profile."""

from __future__ import annotations

from contracts.http import Envelope
from app.modules.identity.schemas import UserOut
from contracts.models import Profile
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.core.responses import ok
from app.core.security import create_access_token
from app.db.session import get_db
from app.modules.identity import repository, service
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    LoginRequest,
    ProfileUpdate,
    TokenData,
    UserUpdate,
)
from contracts.models import RevisionInput

router = APIRouter(tags=["identity"])


@router.post("/auth/login", response_model=Envelope[TokenData])
def login(
    body: LoginRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    user = service.authenticate(db, body.email, body.password)
    token = create_access_token(user.id, settings, token_version=user.token_version)
    return ok(
        TokenData(
            access_token=token, expires_in_minutes=settings.access_token_expire_minutes
        ).model_dump()
    )


@router.get("/users/me", response_model=Envelope[UserOut])
def read_me(user: User = Depends(get_current_user)):
    return ok(service.to_user_out(user).model_dump())


@router.patch("/users/me", response_model=Envelope[UserOut])
def update_me(
    body: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    user.full_name = body.full_name
    user.version += 1
    db.add(user)
    db.commit()
    return ok(service.to_user_out(user).model_dump())


@router.get("/admin/users", response_model=Envelope[list[UserOut]])
def admin_list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return ok(
        [service.to_user_out(u).model_dump() for u in repository.list_users(db, _.workspace_id)]
    )


@router.get("/profiles/me", response_model=Envelope[Profile])
def read_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = service.get_or_create_profile(db, user.id)
    db.commit()
    return ok(service.to_profile_out(profile).model_dump())


@router.put("/profiles/me", response_model=Envelope[Profile])
def put_profile(
    body: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    profile = service.update_profile(db, user.id, body)
    db.commit()
    return ok(service.to_profile_out(profile).model_dump())


@router.post("/profiles/me/reset", response_model=Envelope[Profile])
def reset_profile(
    body: RevisionInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    profile = service.reset_profile(db, user.id, body.version)
    db.commit()
    return ok(service.to_profile_out(profile).model_dump())
