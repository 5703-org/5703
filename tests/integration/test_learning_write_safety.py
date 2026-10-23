"""Mutating learner routes and private practice projections use owner/role fences."""

from copy import deepcopy
from io import BytesIO
import json
from uuid import uuid4
import zipfile

from sqlalchemy import select

from app.modules.learning_product.models import LearningRecord, ReviewEntry, StudyGoal, StudyNote
from .test_chat_runtime import call
from .test_learning_product import draft, published, source


def owner_snapshot(rt, goal_id, note_id, card_id):
    with rt.db() as db:
        goal = db.get(StudyGoal, goal_id)
        notes = [db.get(StudyNote, value) for value in (note_id, card_id)]
        queue = db.scalar(select(ReviewEntry).where(ReviewEntry.note_id == card_id))
        return deepcopy(
            {
                "goal": (goal.title, goal.state, goal.version),
                "notes": [(note.id, note.title, note.content, note.version) for note in notes],
                "queue": (
                    queue.id,
                    queue.due_at,
                    queue.attempt_count,
                    queue.correct_count,
                    queue.version,
                ),
                "records": [
                    record.id
                    for record in db.scalars(select(LearningRecord).order_by(LearningRecord.id))
                ],
            }
        )


def test_cross_owner_writes_leave_learning_records_unchanged(runtime):
    rt = runtime
    document, unit = source(rt)
    goal = call(
        rt,
        "POST",
        "/learning/goals",
        {
            "title": "Owner-only write fixture",
            "document_id": document["id"],
            "section_ids": [unit["section_id"]],
        },
        status=201,
    )
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {
            "title": "Owner-only note",
            "content": "OWNER_PRIVATE_WRITE_CANARY",
            "goal_id": goal["id"],
        },
        status=201,
    )
    card = call(rt, "POST", f"/learning/notes/{note['id']}/review-card", status=201)
    review = next(
        row
        for row in call(rt, "GET", "/learning/review?due_only=false")
        if row["note_id"] == card["id"]
    )
    item = published(rt, draft(rt, unit))["item"]
    before = owner_snapshot(rt, goal["id"], note["id"], card["id"])
    other = rt.headers("admin@example.com")
    requests = [
        (
            "PATCH",
            f"/learning/goals/{goal['id']}",
            {"expected_version": goal["version"], "title": "Unauthorized change"},
        ),
        (
            "POST",
            f"/learning/goals/{goal['id']}/units/{goal['units'][0]['id']}/read",
            {"expected_version": goal["version"]},
        ),
        (
            "PATCH",
            f"/learning/notes/{note['id']}",
            {"expected_version": note["version"], "content": "Unauthorized change"},
        ),
        ("DELETE", f"/learning/notes/{note['id']}?expected_version={note['version']}", None),
        ("POST", f"/learning/notes/{note['id']}/review-card", None),
        (
            "POST",
            f"/learning/review/{review['id']}/reschedule",
            {"expected_version": review["version"], "days": 30},
        ),
        (
            "POST",
            f"/learning/review/{review['id']}/record",
            {"expected_version": review["version"], "outcome": "recalled"},
        ),
        ("POST", "/learning/notes", {"title": "Foreign goal", "goal_id": goal["id"]}),
        (
            "POST",
            f"/learning/practice/{item['id']}/attempts",
            {
                "idempotency_key": str(uuid4()),
                "expected_version": 0,
                "goal_id": goal["id"],
                "response": {"selection": ["B"]},
            },
        ),
    ]
    for method, path, body in requests:
        response = rt.client.request(method, "/api/v1" + path, json=body, headers=other)
        assert response.status_code == 404, response.text
        assert "OWNER_PRIVATE_WRITE_CANARY" not in response.text
        assert response.headers["Cache-Control"] == "no-store"
    assert owner_snapshot(rt, goal["id"], note["id"], card["id"]) == before


def test_student_admin_writes_and_pre_solution_exports_exclude_private_rubric(runtime):
    rt = runtime
    _, unit = source(rt)
    value = draft(rt, unit)
    item = published(rt, value)
    item_id = item["item"]["id"]
    student = rt.headers()
    admin_writes = [
        ("POST", "/admin/learning/practice", value),
        ("POST", f"/admin/learning/practice/{item_id}/validate", None),
        (
            "POST",
            f"/admin/learning/practice/{item_id}/publish",
            {"expected_version": item["version"], "confirm_source_and_solvability": True},
        ),
        (
            "POST",
            f"/admin/learning/practice/{item_id}/retire",
            {"expected_version": item["version"]},
        ),
        (
            "POST",
            "/admin/learning/concept-relations/missing/review",
            {
                "expected_version": 1,
                "decision": "reject",
                "verified_source_support": False,
                "review_note": "Role fence fixture",
            },
        ),
    ]
    for method, path, body in admin_writes:
        response = rt.client.request(method, "/api/v1" + path, json=body, headers=student)
        assert response.status_code == 403, response.text
        assert response.headers["Cache-Control"] == "no-store"
    public_paths = [
        "/learning/practice",
        f"/learning/practice/{item_id}",
        f"/learning/practice/{item_id}/progress",
    ]
    for path in public_paths:
        response = rt.client.get("/api/v1" + path, headers=student)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert "PRIVATE_ANSWER_SENTINEL" not in response.text
        assert "correct_option_ids" not in response.text and '"rubric"' not in response.text
    attempt = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": {"selection": ["B"]}},
    )
    hinted = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/help",
        {"expected_version": attempt["progress_version"], "action": "hint"},
    )
    assert hinted["full_explanation"] is None
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(hinted)
    for path in (
        f"/learning/practice/{item_id}/progress",
        f"/learning/practice/attempts/{attempt['id']}",
        "/learning/records",
        "/learning/notes/export",
    ):
        response = rt.client.get("/api/v1" + path, headers=student)
        assert response.status_code == 200
        assert "PRIVATE_ANSWER_SENTINEL" not in response.text
        assert "correct_option_ids" not in response.text
    docx = rt.client.get("/api/v1/learning/notes/export.docx", headers=student)
    assert docx.status_code == 200 and docx.headers["Cache-Control"] == "no-store"
    with zipfile.ZipFile(BytesIO(docx.content)) as archive:
        assert "PRIVATE_ANSWER_SENTINEL" not in archive.read("word/document.xml").decode()
    # This explicit learner action is the documented solution-disclosure boundary.
    shown = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/help",
        {"expected_version": hinted["version"], "action": "full_explanation"},
    )
    assert "PRIVATE_ANSWER_SENTINEL" in shown["full_explanation"]
