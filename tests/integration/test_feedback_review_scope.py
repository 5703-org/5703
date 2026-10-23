"""Administrator feedback reads and writes use the same private request scope."""

from uuid import uuid4
from sqlalchemy import select

from app.modules.answering.models import Feedback
from app.modules.identity.models import User, Workspace
from app.modules.learning.models import ChatSession
from .test_chat_runtime import call, finish, session, submit


def test_feedback_review_excludes_other_workspace_and_deleted_session(runtime):
    rt = runtime
    chat = session(rt)
    answer = finish(rt, submit(rt, chat, "Hello"))
    feedback = call(rt, "PUT", f"/answers/{answer['id']}/feedback", {"helpful": False})
    admin = rt.headers("admin@example.com")
    assert feedback["id"] in {r["id"] for r in call(rt, "GET", "/admin/feedback", headers=admin)}
    with rt.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        original_workspace = actor.workspace_id
        separate = Workspace(name="Feedback isolation", slug="feedback-" + uuid4().hex)
        db.add(separate)
        db.flush()
        actor.workspace_id = separate.id
        db.commit()
    assert feedback["id"] not in {
        row["id"] for row in call(rt, "GET", "/admin/feedback", headers=admin)
    }
    call(rt, "PATCH", f"/admin/feedback/{feedback['id']}", {"review_state": "reviewed"}, admin, 404)
    with rt.db() as db:
        assert db.get(Feedback, feedback["id"]).review_state == "pending"
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        actor.workspace_id = original_workspace
        db.get(ChatSession, chat["id"]).deleted_at = actor.created_at
        db.commit()
    assert feedback["id"] not in {
        row["id"] for row in call(rt, "GET", "/admin/feedback", headers=admin)
    }
    call(rt, "PATCH", f"/admin/feedback/{feedback['id']}", {"review_state": "reviewed"}, admin, 404)


def test_feedback_review_preserves_same_workspace_administrator_workflow(runtime):
    rt = runtime
    answer = finish(rt, submit(rt, session(rt), "Hello"))
    feedback = call(rt, "PUT", f"/answers/{answer['id']}/feedback", {"helpful": True})
    path = f"/admin/feedback/{feedback['id']}"
    call(rt, "PATCH", path, {"review_state": "reviewed"}, status=403)
    reviewed = call(
        rt,
        "PATCH",
        path,
        {"review_state": "reviewed", "review_note": "Reviewed within the workspace."},
        rt.headers("admin@example.com"),
    )
    assert reviewed["review_state"] == "reviewed"
