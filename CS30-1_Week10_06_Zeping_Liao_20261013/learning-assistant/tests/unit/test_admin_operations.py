"""Admin operations data stays inside the actor's workspace."""

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import models as all_models  # noqa: F401
from app.db.base import Base
from app.modules.administration.operations import overview
from app.modules.answering.models import Job
from app.modules.identity.models import Role, User, Workspace
from app.platform_core.models import OutboxEvent
from app.platform_core.worker_locks import QUEUE_LOCKS, inspect_worker_locks, summarize_locks


def test_operations_queues_and_recent_failures_exclude_other_workspace(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'operations.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(name="admin")
        own = Workspace(name="Own", slug="own")
        other = Workspace(name="Other", slug="other")
        db.add_all([role, own, other])
        db.flush()
        own_user = User(
            email="own@example.test",
            full_name="Own",
            hashed_password="unused",
            role_id=role.id,
            workspace_id=own.id,
        )
        other_user = User(
            email="other@example.test",
            full_name="Other",
            hashed_password="unused",
            role_id=role.id,
            workspace_id=other.id,
        )
        db.add_all([own_user, other_user])
        db.flush()
        db.add_all(
            [
                Job(owner_id=own_user.id, kind="answer", state="queued"),
                Job(
                    owner_id=own_user.id,
                    kind="process",
                    state="failed",
                    error={"code": "SOURCE_UNAVAILABLE", "secret": "do not publish"},
                ),
                Job(
                    owner_id=other_user.id,
                    kind="answer",
                    state="failed",
                    error={"code": "OTHER_FAILURE"},
                ),
                OutboxEvent(
                    workspace_id=other.id,
                    event_type="other.private.event",
                    payload={"secret": "other workspace"},
                ),
            ]
        )
        db.commit()

        result = overview(db, own.id)
        assert result["queues"]["interactive"]["queued"] == 1
        assert result["queues"]["interactive"]["failed"] == 0
        assert result["queues"]["background"]["failed"] == 1
        assert result["worker_locks"]["observation"] == "unavailable"
        assert result["worker_locks"]["interactive"]["lock_observed"] is None
        assert [item["error_code"] for item in result["recent_failures"]] == ["SOURCE_UNAVAILABLE"]
        assert "secret" not in str(result)
        assert "OTHER_FAILURE" not in str(result)
    engine.dispose()


def test_worker_lock_layouts_never_equate_partial_or_unknown_locks_with_both_lanes():
    all_lock = summarize_locks([(QUEUE_LOCKS["all"], "ExclusiveLock")])
    assert all_lock["layout"] == "all"
    assert all_lock["interactive"]["lock_observed"] is True
    assert all_lock["background"]["lock_observed"] is True

    partial = summarize_locks(
        [
            (QUEUE_LOCKS["all"], "ShareLock"),
            (QUEUE_LOCKS["interactive"], "ExclusiveLock"),
        ]
    )
    assert partial["layout"] == "partial"
    assert partial["interactive"]["lock_observed"] is True
    assert partial["background"]["lock_observed"] is False

    split = summarize_locks(
        [
            (QUEUE_LOCKS["all"], "ShareLock"),
            (QUEUE_LOCKS["interactive"], "ExclusiveLock"),
            (QUEUE_LOCKS["background"], "ExclusiveLock"),
        ]
    )
    assert split["layout"] == "split"
    assert split["background"]["lock_observed"] is True

    stray = summarize_locks([(QUEUE_LOCKS["background"], "ExclusiveLock")])
    assert stray["layout"] == "unexpected"
    assert stray["background"]["lock_observed"] is False
    mixed = summarize_locks(
        [
            (QUEUE_LOCKS["all"], "ExclusiveLock"),
            (QUEUE_LOCKS["background"], "ExclusiveLock"),
        ]
    )
    assert mixed["layout"] == "unexpected"
    assert summarize_locks([])["layout"] == "none"


def test_system_view_failure_is_unknown_without_exposing_exception():
    class RestrictedSession:
        bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def execute(self, _query):
            raise SQLAlchemyError("private system detail")

    observed = inspect_worker_locks(RestrictedSession())
    assert observed["observation"] == "unavailable"
    assert observed["interactive"]["lock_observed"] is None
    assert "private system detail" not in str(observed)
