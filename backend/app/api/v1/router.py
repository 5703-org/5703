"""API v1 aggregate router (Spec A04)."""

from fastapi import APIRouter

from app.modules.administration.router import router as administration_router
from app.modules.identity.router import router as identity_router
from app.modules.learning.router import router as learning_router

api_v1_router = APIRouter()
api_v1_router.include_router(identity_router)
api_v1_router.include_router(learning_router)
api_v1_router.include_router(administration_router)
