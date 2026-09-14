"""Session endpoints: a fully closed CRUD loop (Spec section 4)."""

from __future__ import annotations

from contracts.http import Envelope
from app.modules.learning.schemas import SessionOut
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.learning import repository, service
from app.modules.learning.schemas import SessionCreate, SessionRename

router = APIRouter(prefix="/sessions", tags=["learning"])


@router.post("", response_model=Envelope[SessionOut])
def create_session(
    body: SessionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    session = service.create_session(db, user, body.title)
    return ok(service.to_out(session).model_dump(mode="json"))


@router.get("", response_model=Envelope[list[SessionOut]])
def list_sessions(
    status: str = Query(default="active", pattern="^(active|archived|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    effective = None if status == "all" else status
    sessions = repository.list_for_user(db, user.id, effective)
    return ok([service.to_out(s).model_dump(mode="json") for s in sessions])


@router.get("/{session_id}", response_model=Envelope[SessionOut])
def read_session(
    session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return ok(service.to_out(service.get_owned(db, session_id, user)).model_dump(mode="json"))


@router.patch("/{session_id}", response_model=Envelope[SessionOut])
def rename_session(
    session_id: str,
    body: SessionRename,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = service.get_owned(db, session_id, user)
    session = service.rename_session(db, session, body.title, body.version)
    return ok(service.to_out(session).model_dump(mode="json"))


@router.post("/{session_id}/archive", response_model=Envelope[SessionOut])
def archive_session(
    session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    session = service.get_owned(db, session_id, user)
    return ok(service.to_out(service.transition(db, session, "archived")).model_dump(mode="json"))


@router.post("/{session_id}/restore", response_model=Envelope[SessionOut])
def restore_session(
    session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    session = service.get_owned(db, session_id, user)
    return ok(service.to_out(service.transition(db, session, "active")).model_dump(mode="json"))


@router.delete("/{session_id}", response_model=Envelope[dict])
def delete_session(
    session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    session = service.get_owned(db, session_id, user)
    service.soft_delete(db, session)
    return ok({"deleted": True, "id": session_id})
