"""Engine / session management (Spec B01).

The engine is created explicitly inside create_app() so tests can point the
same factory at an isolated database (Spec A02, A07).
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi import Request

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def init_engine(database_url: str) -> Engine:
    global _engine, _SessionLocal
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialised. Call init_engine() first.")
    return _engine


@contextmanager
def session_scope():
    if _SessionLocal is None:
        raise RuntimeError("Session factory is not initialised.")
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db(request: Request):
    """FastAPI dependency: one session per request."""
    if _SessionLocal is None:
        raise RuntimeError("Session factory is not initialised.")
    db = sessionmaker(bind=request.app.state.engine, autoflush=False, expire_on_commit=False)()
    try:
        yield db
    finally:
        db.close()
