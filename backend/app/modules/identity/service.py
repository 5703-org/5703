"""Identity business logic: authentication, profile lifecycle."""

from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import verify_password
from app.modules.identity import repository
from app.modules.identity.models import StudentProfile, User
from app.modules.identity.schemas import ProfileOut, ProfileUpdate, UserOut


def authenticate(db: Session, email: str, password: str) -> User:
    user = repository.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        # Same error for unknown email and wrong password: no account enumeration.
        raise AppError("BAD_CREDENTIALS")
    if user.status != "active":
        raise AppError("FORBIDDEN", detail="Account is deactivated.")
    return user


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        status=user.status,
        version=user.version,
    )


def get_or_create_profile(db: Session, user_id: str) -> StudentProfile:
    profile = repository.get_profile(db, user_id)
    if profile:
        return profile
    # Older imported accounts may not yet have a profile. Serialize only that
    # first creation so simultaneous first chats cannot violate its unique key.
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    return repository.get_profile(db, user_id) or repository.create_default_profile(db, user_id)


def to_profile_out(profile: StudentProfile) -> ProfileOut:
    return ProfileOut(
        level=profile.level,
        style=profile.style,
        language=profile.language,
        topics=list(profile.topics or []),
        version=profile.version,
    )


def update_profile(db: Session, user_id: str, patch: ProfileUpdate) -> StudentProfile:
    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id).with_for_update()
    )
    if profile is None:
        profile = get_or_create_profile(db, user_id)
    if profile.version != patch.version:
        raise AppError(
            "CONFLICT", detail="The profile was changed elsewhere. Reload before saving."
        )
    data = patch.model_dump(exclude={"version"})
    for field_name, value in data.items():
        setattr(profile, field_name, value)
    profile.version += 1  # new profile version, history preserved later via snapshots
    db.add(profile)
    db.flush()
    return profile


def reset_profile(db: Session, user_id: str, version: int) -> StudentProfile:
    return update_profile(db, user_id, ProfileUpdate(version=version))
