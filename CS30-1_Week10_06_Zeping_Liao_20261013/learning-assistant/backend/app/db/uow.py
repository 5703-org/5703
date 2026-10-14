"""Unit of Work (Spec B04): commit everything or roll everything back.

Usage:
    with UnitOfWork() as uow:
        uow.db.add(obj)
        ...
"""

from __future__ import annotations

from app.db import session as db_session


class UnitOfWork:
    def __enter__(self) -> "UnitOfWork":
        self._ctx = db_session.session_scope()
        self.db = self._ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return self._ctx.__exit__(exc_type, exc, tb)
