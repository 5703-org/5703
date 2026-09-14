"""Force actual PostgreSQL first-create races at the vulnerable read boundary."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import func, select

from app.modules.answering.models import Feedback
from app.modules.answering import router as answers
from app.modules.identity import repository
from app.modules.identity.models import StudentProfile, User
from .test_chat_runtime import call, finish, session, submit


def test_concurrent_account_creation_returns_conflict_without_partial_profile(runtime, monkeypatch):
    rt = runtime
    email = uuid4().hex + "@example.com"
    headers = rt.headers("admin@example.com")
    barrier = Barrier(2)
    original = repository.get_user_by_email

    def both_observe_missing(db, candidate):
        result = original(db, candidate)
        if candidate.lower() == email and result is None:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(repository, "get_user_by_email", both_observe_missing)
    body = {
        "email": email,
        "full_name": "Concurrent account",
        "password": "Only-a-test-password-123!",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: rt.client.post("/api/v1/admin/users", json=body, headers=headers),
                range(2),
            )
        )
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert (
        next(response for response in responses if response.status_code == 409).json()["error"][
            "code"
        ]
        == "CONFLICT"
    )
    with rt.db() as db:
        users = list(db.scalars(select(User).where(User.email == email)))
        assert len(users) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(StudentProfile)
                .where(StudentProfile.user_id == users[0].id)
            )
            == 1
        )


def test_concurrent_first_feedback_save_reuses_one_record_and_keeps_review_editable(
    runtime, monkeypatch
):
    rt = runtime
    chat = session(rt)
    receipt = submit(rt, chat, "Hello")
    answer = finish(rt, receipt)
    answer_id = answer["id"]
    headers = rt.headers()
    barrier = Barrier(2)
    original = answers.owned_answer

    def both_own_same_answer(db, identifier, actor):
        result = original(db, identifier, actor)
        if identifier == answer_id:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(answers, "owned_answer", both_own_same_answer)
    bodies = [
        {"helpful": True, "comment": "First tab"},
        {"helpful": False, "comment": "Second tab"},
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda body: rt.client.put(
                    f"/api/v1/answers/{answer_id}/feedback", json=body, headers=headers
                ),
                bodies,
            )
        )
    monkeypatch.setattr(answers, "owned_answer", original)
    assert [response.status_code for response in responses] == [200, 200]
    ids = {response.json()["data"]["id"] for response in responses}
    assert len(ids) == 1
    with rt.db() as db:
        rows = list(db.scalars(select(Feedback).where(Feedback.answer_id == answer_id)))
        assert len(rows) == 1 and rows[0].comment in {body["comment"] for body in bodies}
    current = call(rt, "GET", f"/answers/{answer_id}/feedback")
    assert current["id"] in ids
    reviewed = call(
        rt,
        "PATCH",
        "/admin/feedback/" + current["id"],
        {
            "review_state": "reviewed",
            "review_note": "Reviewed after concurrent save",
            "issue": "LOCAL-1",
        },
        rt.headers("admin@example.com"),
    )
    assert reviewed["review_state"] == "reviewed"
    updated = call(
        rt,
        "PUT",
        f"/answers/{answer_id}/feedback",
        {"helpful": True, "comment": "Final correction"},
    )
    assert updated["id"] == current["id"] and updated["review_state"] == "pending"
    assert updated["review_note"] == reviewed["review_note"] and updated["issue"] == "LOCAL-1"
