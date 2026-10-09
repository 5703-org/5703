"""Identity API schemas. All cross-module payloads carry a schema version (Spec K07)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

SCHEMA_VERSION = "1.0"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    version: int


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)


class ProfileOut(BaseModel):
    level: str
    style: str
    language: str
    topics: list[str]
    version: int


from contracts.models import ProfileUpdate
