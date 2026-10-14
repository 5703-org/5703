"""Actual migrated PostgreSQL learning workflows with authored, labelled sources."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
import os
import zipfile
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker
from app.cli import seed
from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest, Evidence
from app.modules.identity.models import User, Workspace
from app.modules.learning_product import library
from app.modules.learning_product.models import (
    PracticeAttempt,
    PracticeItem,
    ReviewEntry,
    StudyNote,
)
from app.modules.knowledge.models import (
    ActiveCorpus,
    Document,
    DocumentVersion,
    ProcessingRun,
    SourceUnit,
)
from app.modules.learning_state.models import PrivateAnswerDraft
from .test_chat_runtime import call, corpus, finish, session, submit


def use_scripted_practice_grader(monkeypatch, outcome="correct"):
    """Finite authored wire verdicts exercise integration; never model quality labels."""
    from app.modules.learning_product import practice_assessment
    from generation.types import ModelConfig, ProviderResult

    config = ModelConfig(
        provider="openai_compatible",
        model="scripted-practice-test-only",
        configuration_id="model-settings:scripted-test",
        tokenizer_provider="estimate",
        window_tokens=32000,
        max_tokens=4096,
        timeout_seconds=1,
    )
    calls = []

    class ScriptedGrader:
        def __init__(self, config, **kwargs):
            self.config = config

        def generate(self, messages, **kwargs):
            data = json.loads(messages[1]["content"])
            calls.append(data["binding_hash"])
            points = [point["id"] for point in data["criteria"]["required_points"]]
            result = dict(
                binding_hash=data["binding_hash"],
                outcome=outcome,
                source_sufficient=True,
                rubric_supported=True,
                contradiction_present=outcome == "incorrect",
                conditions_preserved=True,
                covered_point_ids=points if outcome == "correct" else [],
                missing_point_ids=[] if outcome == "correct" else points,
                source_spans=[dict(start=0, end=len(data["source_passage"]))],
                response_spans=[dict(start=0, end=len(data["learner_text"]))],
            )
            return ProviderResult(
                raw_text=json.dumps(result),
                provider=config.provider,
                model=config.model,
                request_submitted=True,
                finish_reason="stop",
            )

    monkeypatch.setattr(
        practice_assessment, "resolve_active_checker_model_config", lambda *args: config
    )
    monkeypatch.setattr(practice_assessment, "resolve_secret", lambda *args: None)
    monkeypatch.setattr(practice_assessment, "LLMAdapter", ScriptedGrader)
    return calls


def applied_practice_feedback(attempt):
    assert attempt["feedback"]["outcome"] == "pending_review"
    assert attempt["assessment"]["status"] == "applied"
    return attempt["assessment"]["feedback"]


def source(rt):
    doc, _ = corpus(rt)
    page = call(rt, "GET", f"/learning/library/{doc['id']}/units")
    return doc, page["items"][0]


def draft(rt, unit, kind="mcq", **changes):
    value = dict(
        title="Authored practice " + uuid4().hex[:8],
        kind=kind,
        prompt="Select the energy input described in the authored paragraph.",
        options=[{"id": "A", "text": "Light"}, {"id": "B", "text": "Sound"}],
        concepts=["photosynthesis"],
        conditions=["Use the supplied textbook source."],
        source=unit["locator"],
        rubric={
            "correct_option_ids": ["A"],
            "explanation": "PRIVATE_ANSWER_SENTINEL light supplies the energy.",
            "hints": ["Think about what the leaf absorbs.", "Identify the energy input."],
        },
    )
    value.update(changes)
    return value


def published(rt, value):
    admin = rt.headers("admin@example.com")
    item = call(rt, "POST", "/admin/learning/practice", value, admin, 201)
    item = call(
        rt, "POST", "/admin/learning/practice/" + item["item"]["id"] + "/validate", headers=admin
    )
    assert item["state"] == "validated", item
    return call(
        rt,
        "POST",
        "/admin/learning/practice/" + item["item"]["id"] + "/publish",
        {"expected_version": item["version"], "confirm_source_and_solvability": True},
        admin,
    )


def student_id(rt):
    with rt.db() as db:
        return db.scalar(select(User.id).where(User.email == "student@example.com"))


def test_reading_resume_goal_prerequisites_and_reading_is_not_mastery(runtime):
    rt = runtime
    doc, unit = source(rt)
    books = call(rt, "GET", "/learning/library")
    assert any(b["id"] == doc["id"] for b in books)
    sections = call(rt, "GET", f"/learning/library/{doc['id']}/sections")
    position = call(
        rt,
        "PUT",
        "/learning/reading-position",
        {"source": unit["locator"], "char_offset": 5, "expected_version": 0},
    )
    assert call(rt, "GET", "/learning/reading-position")[0]["id"] == position["id"]
    resumed = call(
        rt, "GET", f"/learning/library/{doc['id']}/units?limit=1&source_unit_id={unit['id']}"
    )
    assert resumed["items"][0]["id"] == unit["id"]
    call(
        rt,
        "PUT",
        "/learning/reading-position",
        {"source": unit["locator"], "char_offset": 6, "expected_version": 0},
        status=409,
    )
    goal = call(
        rt,
        "POST",
        "/learning/goals",
        {
            "title": "Understand transport",
            "document_id": doc["id"],
            "section_ids": [s["id"] for s in sections],
        },
        status=201,
    )
    assert goal["units"][1]["prerequisite_unit_ids"] == [goal["units"][0]["id"]]
    updated = call(
        rt,
        "POST",
        f"/learning/goals/{goal['id']}/units/{goal['units'][0]['id']}/read",
        {"expected_version": goal["version"]},
    )
    assert updated["units"][0]["status"] == "read" and updated["units"][0]["attempts"] == 0
    assert "mastery" not in updated["units"][0]
    assert call(rt, "GET", "/learning/records")


def test_reading_scope_exact_selection_and_revocation(runtime):
    rt = runtime
    doc, unit = source(rt)
    with rt.db() as db:
        actor = db.get(User, student_id(rt))
        frozen = library.freeze_reading_context(
            db,
            actor,
            dict(
                scope="chapter",
                document_id=doc["id"],
                source_unit_id=unit["id"],
                selection={"start": 0, "end": 15, "text": unit["text"][:15]},
            ),
        )
        assert frozen["allowed_chunk_ids"] and frozen["selected_chunk_ids"]
        evidence = library.selected_reading_evidence(db, actor, frozen)
        assert all(e["chunk_id"] in frozen["allowed_chunk_ids"] for e in evidence)
        with pytest.raises(AppError):
            library.freeze_reading_context(
                db,
                actor,
                dict(
                    scope="chapter",
                    document_id=doc["id"],
                    source_unit_id=unit["id"],
                    selection={"start": 0, "end": 15, "text": "forged text"},
                ),
            )
        altered = deepcopy(frozen)
        altered["scope"] = "all"
        with pytest.raises(AppError):
            library.validate_reading_context(db, actor, altered)
        document = db.get(Document, doc["id"])
        document.revoked = True
        db.commit()
        with pytest.raises(AppError):
            library.validate_reading_context(db, actor, frozen)
    call(rt, "GET", f"/learning/library/{doc['id']}/units", status=410)


def test_cross_workspace_library_and_owned_goal_note_attempt_isolation(runtime):
    rt = runtime
    doc, unit = source(rt)
    with rt.db() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        workspace = Workspace(name="Other workspace", slug="other-" + uuid4().hex)
        db.add(workspace)
        db.flush()
        original = admin.workspace_id
        admin.workspace_id = workspace.id
        db.commit()
        student = db.get(User, student_id(rt))
        assert library.books(db, student) == []
        with pytest.raises(AppError):
            library.freeze_reading_context(db, student, {"scope": "all"})
        admin.workspace_id = original
        db.commit()
    goal = call(
        rt,
        "POST",
        "/learning/goals",
        {"title": "Own goal", "document_id": doc["id"], "section_ids": [unit["section_id"]]},
        status=201,
    )
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {"title": "Own note", "content": "Private note body", "goal_id": goal["id"]},
        status=201,
    )
    admin_headers = rt.headers("admin@example.com")
    call(rt, "GET", "/learning/goals/" + goal["id"], headers=admin_headers, status=404)
    call(
        rt,
        "PATCH",
        "/learning/notes/" + note["id"],
        {"expected_version": 1, "content": "changed"},
        admin_headers,
        404,
    )
    item = published(rt, draft(rt, unit))["item"]
    attempt = call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": {"selection": ["B"]}},
    )
    call(
        rt, "GET", "/learning/practice/attempts/" + attempt["id"], headers=admin_headers, status=404
    )


def test_practice_publication_key_isolation_idempotency_and_review(runtime):
    rt = runtime
    _, unit = source(rt)
    admin = rt.headers("admin@example.com")
    value = draft(rt, unit)
    call(rt, "POST", "/admin/learning/practice", value, status=403)
    created = call(rt, "POST", "/admin/learning/practice", value, admin, 201)
    item_id = created["item"]["id"]
    call(rt, "GET", "/learning/practice/" + item_id, status=404)
    call(
        rt,
        "POST",
        f"/admin/learning/practice/{item_id}/publish",
        {"expected_version": 1, "confirm_source_and_solvability": True},
        admin,
        409,
    )
    checked = call(rt, "POST", f"/admin/learning/practice/{item_id}/validate", headers=admin)
    call(
        rt,
        "POST",
        f"/admin/learning/practice/{item_id}/publish",
        {"expected_version": checked["version"], "confirm_source_and_solvability": True},
        admin,
    )
    public = call(rt, "GET", "/learning/practice/" + item_id)
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(public) and "rubric" not in public
    payload = {
        "idempotency_key": str(uuid4()),
        "expected_version": 0,
        "response": {"selection": ["B"]},
    }
    first = call(rt, "POST", f"/learning/practice/{item_id}/attempts", payload)
    assert first["feedback"]["outcome"] == "incorrect"
    assert call(rt, "POST", f"/learning/practice/{item_id}/attempts", payload)["id"] == first["id"]
    call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/attempts",
        {**payload, "response": {"selection": ["A"]}},
        status=409,
    )
    progress = call(rt, "GET", f"/learning/practice/{item_id}/progress")
    assert progress["full_explanation"] is None and "PRIVATE_ANSWER_SENTINEL" not in json.dumps(
        progress
    )
    review = next(
        r for r in call(rt, "GET", "/learning/review?due_only=false") if r["item_id"] == item_id
    )
    assert review["attempt_count"] == 1 and review["correct_count"] == 0
    assert review["recent_attempt_count"] == 1 and review["recent_error_counts"] == {
        "concept_misconception": 1
    }
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": review["version"], "outcome": "recalled"},
        status=422,
    )
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/reschedule",
        {"expected_version": review["version"], "days": 0},
    )
    assert any(r["item_id"] == item_id for r in call(rt, "GET", "/learning/review"))
    shown = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/help",
        {"expected_version": progress["version"], "action": "full_explanation"},
    )
    assert "PRIVATE_ANSWER_SENTINEL" in shown["full_explanation"]


@pytest.mark.parametrize(
    "kind,rubric,response,outcome",
    [
        ("multiselect", {"correct_option_ids": ["A", "B"]}, {"selection": ["A"]}, "partial"),
        (
            "short",
            {"required_points": [{"id": "energy", "terms": ["light energy"]}]},
            {"text": "Uses light energy"},
            "correct",
        ),
        (
            "numeric",
            {"numeric": {"value": 2.0, "unit": "m"}},
            {"value": 200.0, "unit": "cm"},
            "correct",
        ),
    ],
)
def test_other_published_practice_types(runtime, monkeypatch, kind, rubric, response, outcome):
    if kind == "short":
        use_scripted_practice_grader(monkeypatch, outcome)
    rt = runtime
    _, unit = source(rt)
    item = published(
        rt,
        draft(
            rt,
            unit,
            kind,
            options=[{"id": "A", "text": "First"}, {"id": "B", "text": "Second"}]
            if kind == "multiselect"
            else [],
            rubric={**rubric, "explanation": "Authored private solution"},
        ),
    )["item"]
    result = call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": response},
    )
    feedback = applied_practice_feedback(result) if kind == "short" else result["feedback"]
    assert feedback["outcome"] == outcome


def test_negated_required_point_does_not_advance_saved_practice(runtime):
    rt = runtime
    _, unit = source(rt)
    item = published(
        rt,
        draft(
            rt,
            unit,
            "short",
            prompt="Explain the energy input.",
            options=[],
            rubric={
                "required_points": [{"id": "energy", "terms": ["light energy"]}],
                "explanation": "PRIVATE_ANSWER_SENTINEL",
            },
        ),
    )["item"]
    attempt = call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": 0,
            "response": {"text": "The process does not use light energy."},
        },
    )
    assert attempt["feedback"]["outcome"] == "pending_review"
    assert attempt["feedback"]["grading_method"] == "pending_model_assessment_v1"
    assert attempt["feedback"]["error_categories"] == []
    assert attempt["assessment"]["status"] == "pending_review"
    progress = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    assert progress["state"] == "awaiting_attempt"
    assert progress["attempts"][0]["id"] == attempt["id"]
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(progress)
    review = call(rt, "GET", "/learning/review?due_only=false")
    assert not any(row["item_id"] == item["id"] for row in review)


def test_step_progress_hints_and_full_explanation_are_separate_from_success(runtime, monkeypatch):
    use_scripted_practice_grader(monkeypatch)
    rt = runtime
    _, unit = source(rt)
    rubric = {
        "steps": [
            {
                "id": "one",
                "prompt": "State the first variable",
                "acceptable_answers": ["x"],
                "hints": ["Name a variable."],
            },
            {
                "id": "two",
                "prompt": "Compute the distance",
                "numeric": {"value": 4.0, "unit": "m"},
                "hints": ["Convert units."],
            },
        ],
        "explanation": "PRIVATE_FINAL 4 m",
    }
    item = published(rt, draft(rt, unit, "step", options=[], rubric=rubric))["item"]
    item_id = item["id"]
    initial = call(rt, "GET", f"/learning/practice/{item_id}/progress")
    assert initial[
        "current_step_prompt"
    ] == "State the first variable" and "Compute" not in json.dumps(initial)
    bad = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": 0,
            "response": {"step": 2, "value": 4.0, "unit": "m"},
        },
    )
    assert bad["feedback"]["outcome"] == "irrelevant"
    hint = call(
        rt, "POST", f"/learning/practice/{item_id}/help", {"expected_version": 1, "action": "hint"}
    )
    assert hint["hints"] == ["Name a variable."] and hint["state"] == "awaiting_attempt"
    good = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": 2,
            "response": {"step": 1, "text": "x"},
        },
    )
    assert applied_practice_feedback(good)["outcome"] == "correct"
    step2 = call(rt, "GET", f"/learning/practice/{item_id}/progress")
    assert step2["current_step"] == 2 and step2["help_level"] == 0
    final = call(
        rt,
        "POST",
        f"/learning/practice/{item_id}/help",
        {
            "expected_version": good["assessment"]["applied_progress_version"],
            "action": "full_explanation",
        },
    )
    assert final["state"] == "awaiting_attempt" and final["full_explanation"] == "PRIVATE_FINAL 4 m"


def test_attempt_concurrency_cas_keeps_one_winner(runtime):
    rt = runtime
    _, unit = source(rt)
    item = published(rt, draft(rt, unit))["item"]
    headers = rt.headers()

    def submit_one(_):
        return rt.client.post(
            f"/api/v1/learning/practice/{item['id']}/attempts",
            headers=headers,
            json={
                "idempotency_key": str(uuid4()),
                "expected_version": 0,
                "response": {"selection": ["A"]},
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit_one, range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    with rt.db() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(PracticeAttempt)
                .where(PracticeAttempt.item_id == item["id"])
            )
            == 1
        )


def test_note_cas_delete_exports_and_personal_source_boundary(runtime):
    rt = runtime
    _, unit = source(rt)
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {
            "title": "Recall & compare",
            "content": "<script>raw personal note</script>",
            "source": unit["locator"],
        },
        status=201,
    )
    edited = call(
        rt,
        "PATCH",
        "/learning/notes/" + note["id"],
        {"expected_version": 1, "content": "Updated own note"},
    )
    call(
        rt,
        "PATCH",
        "/learning/notes/" + note["id"],
        {"expected_version": 1, "content": "stale"},
        status=409,
    )
    markdown = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert (
        "Updated own note" in markdown
        and "physical page" in markdown
        and "not verified textbook evidence" in markdown
    )
    docx = rt.client.get("/api/v1/learning/notes/export.docx", headers=rt.headers())
    assert docx.status_code == 200
    with zipfile.ZipFile(BytesIO(docx.content)) as bundle:
        assert "word/document.xml" in bundle.namelist()
        assert "Recall &amp; compare" in bundle.read("word/document.xml").decode()
    card = call(rt, "POST", f"/learning/notes/{note['id']}/review-card", status=201)
    assert card["kind"] == "review_card" and card["source_type"] == "personal_note"
    call(rt, "DELETE", f"/learning/notes/{note['id']}?expected_version={edited['version']}")
    assert all(n["id"] != note["id"] for n in call(rt, "GET", "/learning/notes"))


def test_personal_review_card_due_queue_self_report_and_revocation(runtime):
    rt = runtime
    document, unit = source(rt)
    call(
        rt,
        "POST",
        "/learning/notes",
        {"title": "Empty card", "content": "  ", "kind": "review_card"},
        status=422,
    )
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {
            "title": "Recall photosynthesis",
            "content": "Light energy becomes chemical energy in sugars.",
            "source": unit["locator"],
            "concepts": ["photosynthesis"],
        },
        status=201,
    )
    card = call(rt, "POST", f"/learning/notes/{note['id']}/review-card", status=201)
    review = next(
        row for row in call(rt, "GET", "/learning/review") if row["note_id"] == card["id"]
    )
    assert review["target_type"] == "personal_review_card"
    assert review["item_id"] is None and review["suggested_item_id"] is None
    assert review["card_content"] == card["content"]
    assert review["card_source"] == card["source"]
    assert review["attempt_count"] == review["correct_count"] == 0
    assert "due now" in review["scheduling_reason"]

    other = rt.headers("student2@example.com")
    assert all(
        row["id"] != review["id"]
        for row in call(rt, "GET", "/learning/review?due_only=false", headers=other)
    )
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": review["version"], "outcome": "recalled"},
        other,
        404,
    )
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/reschedule",
        {"expected_version": review["version"], "days": 0},
        other,
        404,
    )

    missed = call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": review["version"], "outcome": "needs_review"},
    )
    assert missed["attempt_count"] == 1 and missed["correct_count"] == 0
    assert missed["error_categories"] == ["self_reported_not_recalled"]
    assert "Self-reported difficulty" in missed["scheduling_reason"]
    assert (
        0.99
        < (datetime.fromisoformat(missed["due_at"]) - datetime.now(timezone.utc)).total_seconds()
        / 86400
        < 1.01
    )
    assert all(row["id"] != review["id"] for row in call(rt, "GET", "/learning/review"))
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": review["version"], "outcome": "recalled"},
        status=409,
    )
    now_due = call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/reschedule",
        {"expected_version": missed["version"], "days": 0},
    )
    assert any(row["id"] == review["id"] for row in call(rt, "GET", "/learning/review"))
    recalled = call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": now_due["version"], "outcome": "recalled"},
    )
    assert recalled["attempt_count"] == 2 and recalled["correct_count"] == 1
    assert "No graded mastery inferred" in recalled["scheduling_reason"]
    assert (
        1.99
        < (datetime.fromisoformat(recalled["due_at"]) - datetime.now(timezone.utc)).total_seconds()
        / 86400
        < 2.01
    )
    assert any(
        row["kind"] == "review_card_self_reported"
        and row["details"]["verification"] == "learner_self_report"
        for row in call(rt, "GET", "/learning/records")
    )

    with rt.db() as db:
        db.get(Document, document["id"]).revoked = True
        db.commit()
    assert all(
        row["id"] != review["id"] for row in call(rt, "GET", "/learning/review?due_only=false")
    )
    call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": recalled["version"], "outcome": "recalled"},
        status=410,
    )
    call(rt, "DELETE", f"/learning/notes/{card['id']}?expected_version={card['version']}")
    with rt.db() as db:
        assert db.scalar(select(ReviewEntry).where(ReviewEntry.note_id == card["id"])) is None


def test_existing_personal_review_card_is_backfilled_on_schema_upgrade(postgres_url):
    server = postgres_url.rsplit("/", 1)[0]
    database_name = "cs30_test_" + uuid4().hex[:12]
    admin = create_engine(server + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {database_name}"))
    database_url = server + "/" + database_name
    engine = create_engine(database_url)
    config = Config(str(Path(__file__).resolve().parents[2] / "backend/alembic.ini"))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "f4a18bc67d20")
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            seed(db)
            owner = db.scalar(select(User).where(User.email == "student@example.com"))
            card = StudyNote(
                owner_id=owner.id,
                title="Saved before queue upgrade",
                content="Explain the role of light.",
                kind="review_card",
                source=None,
                answer_id=None,
                goal_id=None,
                concepts=["photosynthesis"],
            )
            db.add(card)
            db.commit()
            card_id = card.id
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT due_at, attempt_count, correct_count, scheduling_reason "
                    "FROM study_review_entries WHERE note_id = :note_id"
                ),
                {"note_id": card_id},
            ).one()
            saved_note = connection.execute(
                text("SELECT title, content, version FROM study_notes WHERE id = :note_id"),
                {"note_id": card_id},
            ).one()
        assert row.attempt_count == row.correct_count == 0
        assert "Existing personal review card" in row.scheduling_reason
        assert row.due_at <= datetime.now(timezone.utc)
        assert tuple(saved_note) == ("Saved before queue upgrade", "Explain the role of light.", 1)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": database_name},
            )
            connection.execute(text(f"DROP DATABASE {database_name}"))
        admin.dispose()


def test_saved_answer_note_exports_only_visible_actual_citations(runtime):
    rt = runtime
    document, _ = source(rt)
    with rt.db() as db:
        row = db.get(Document, document["id"])
        row.edition = "Authored edition 2026"
        row.source_url = "https://example.org/authored-biology"
        db.commit()
    answer = finish(rt, submit(rt, session(rt)))
    assert answer["response"]["citations"]
    cited_id = answer["response"]["citations"][0]
    with rt.db() as db:
        cited = db.scalar(
            select(Evidence).where(
                Evidence.answer_id == answer["id"], Evidence.evidence_id == cited_id
            )
        )
        assert cited is not None
        request = db.get(AnswerRequest, answer["request_id"])
        run = db.get(ProcessingRun, cited.payload["processing_id"])
        version = db.get(DocumentVersion, run.document_version_id)
        expected_hash = version.raw_hash
        expected_chunk = cited.chunk_id
        db.add(
            Evidence(
                answer_id=answer["id"],
                evidence_id="ev_999",
                document_id=cited.document_id,
                chunk_id=cited.chunk_id,
                payload={**cited.payload, "evidence_id": "ev_999"},
            )
        )
        db.add(
            PrivateAnswerDraft(
                request_id=request.id,
                phase="generated_draft",
                payload={"raw_text": "PRIVATE_DRAFT_EXPORT_SENTINEL"},
            )
        )
        db.commit()
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {
            "title": "My saved explanation",
            "content": "Review this later",
            "answer_id": answer["id"],
        },
        status=201,
    )
    markdown = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert note["id"] in [row["id"] for row in call(rt, "GET", "/learning/notes")]
    assert f"Saved answer reference: {answer['id']}" in markdown
    assert f"Actual cited source {cited_id}: {document['title']}" in markdown
    assert "edition Authored edition 2026" in markdown
    assert f"chunk {expected_chunk}" in markdown
    assert f"Original SHA256: {expected_hash}" in markdown
    assert "source page(s)" in markdown and "section Photosynthesis" in markdown
    assert "https://example.org/authored-biology" in markdown
    assert "ev_999" not in markdown
    assert "PRIVATE_DRAFT_EXPORT_SENTINEL" not in markdown
    response = rt.client.get("/api/v1/learning/notes/export.docx", headers=rt.headers())
    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(response.content)) as bundle:
        xml = bundle.read("word/document.xml").decode()
    assert document["title"] in xml and expected_hash in xml
    assert "ev_999" not in xml and "PRIVATE_DRAFT_EXPORT_SENTINEL" not in xml

    other = rt.headers("student2@example.com")
    call(
        rt,
        "POST",
        "/learning/notes",
        {"title": "Cross-owner", "content": "test", "answer_id": answer["id"]},
        other,
        404,
    )
    assert (
        document["title"]
        not in call(rt, "GET", "/learning/notes/export", headers=other)["markdown"]
    )

    with rt.db() as db:
        db.get(Document, document["id"]).revoked = True
        db.commit()
    revoked = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert "Review this later" in revoked
    assert "A saved answer citation is currently unavailable." in revoked
    assert document["title"] not in revoked
    assert expected_hash not in revoked
    assert "https://example.org/authored-biology" not in revoked


def test_practice_memory_opt_in_and_owned_provenance(runtime):
    rt = runtime
    _, unit = source(rt)
    state = call(rt, "GET", "/me/memory/settings")
    call(rt, "PATCH", "/me/memory/settings", {"enabled": True, "version": state["version"]})
    item = published(rt, draft(rt, unit))["item"]
    attempt = call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": {"selection": ["B"]}},
    )
    memory = next(
        m
        for m in call(rt, "GET", "/me/memories")
        if m["provenance"].get("practice_attempt_id") == attempt["id"]
    )
    assert memory["category"] == "assessment_performance"
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(memory)
    assert (
        call(rt, "GET", "/learning/practice/attempts/" + attempt["id"])["feedback"]["outcome"]
        == "incorrect"
    )
    state = call(rt, "GET", "/me/memory/settings")
    call(rt, "PATCH", "/me/memory/settings", {"enabled": False, "version": state["version"]})


def test_successor_item_keeps_saved_attempt_key_revision_immutable(runtime):
    rt = runtime
    _, unit = source(rt)
    original = published(rt, draft(rt, unit))["item"]
    attempt = call(
        rt,
        "POST",
        f"/learning/practice/{original['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": {"selection": ["A"]}},
    )
    newer = draft(
        rt,
        unit,
        previous_item_id=original["id"],
        rubric={"correct_option_ids": ["B"], "explanation": "A changed authored rule"},
    )
    successor = published(rt, newer)["item"]
    assert successor["item_revision"] == 2
    saved = call(rt, "GET", "/learning/practice/attempts/" + attempt["id"])
    assert (
        saved == attempt
        and saved["item_revision"] == 1
        and saved["feedback"]["outcome"] == "correct"
    )
    call(rt, "POST", "/admin/learning/practice", newer, rt.headers("admin@example.com"), 409)
    old = call(rt, "GET", f"/learning/practice/{original['id']}/progress")
    assert old["attempts"] == [attempt]


def test_failed_validation_reports_admin_reason_but_never_publishes(runtime):
    rt = runtime
    _, unit = source(rt)
    headers = rt.headers("admin@example.com")
    row = call(
        rt,
        "POST",
        "/admin/learning/practice",
        draft(rt, unit, rubric={"correct_option_ids": ["unknown"], "explanation": "Not solvable"}),
        headers,
        201,
    )
    checked = call(
        rt, "POST", f"/admin/learning/practice/{row['item']['id']}/validate", headers=headers
    )
    assert checked["state"] == "draft" and checked["validation_details"]["issues"] == [
        "invalid_choice_key"
    ]
    call(
        rt,
        "POST",
        f"/admin/learning/practice/{row['item']['id']}/publish",
        {"expected_version": checked["version"], "confirm_source_and_solvability": True},
        headers,
        409,
    )
    call(rt, "GET", "/learning/practice/" + row["item"]["id"], status=404)


def test_goal_unit_filter_and_attempt_reject_unselected_section(runtime):
    rt = runtime
    doc, first = source(rt)
    units = call(rt, "GET", f"/learning/library/{doc['id']}/units")["items"]
    other = next(u for u in units if u["section_id"] != first["section_id"])
    goal = call(
        rt,
        "POST",
        "/learning/goals",
        {
            "title": "One section only",
            "document_id": doc["id"],
            "section_ids": [first["section_id"]],
        },
        status=201,
    )
    admitted = published(rt, draft(rt, first))["item"]
    excluded = published(rt, draft(rt, other))["item"]
    chosen = call(
        rt, "GET", f"/learning/practice?goal_id={goal['id']}&unit_id={goal['units'][0]['id']}"
    )
    assert admitted["id"] in {i["id"] for i in chosen} and excluded["id"] not in {
        i["id"] for i in chosen
    }
    call(
        rt,
        "GET",
        f"/learning/practice?unit_id={goal['units'][0]['id']}",
        headers=rt.headers("admin@example.com"),
        status=404,
    )
    call(
        rt,
        "POST",
        f"/learning/practice/{excluded['id']}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": 0,
            "goal_id": goal["id"],
            "response": {"selection": ["A"]},
        },
        status=422,
    )


def test_revoked_source_hides_note_link_and_blocks_new_practice(runtime):
    rt = runtime
    doc, unit = source(rt)
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {"title": "Retained own note", "content": "Own words", "source": unit["locator"]},
        status=201,
    )
    assert note["source_metadata"]["physical_page"] == unit["page"]
    item = published(rt, draft(rt, unit))["item"]
    with rt.db() as db:
        db.get(Document, doc["id"]).revoked = True
        db.commit()
    saved = next(n for n in call(rt, "GET", "/learning/notes") if n["id"] == note["id"])
    assert saved["content"] == "Own words" and saved["source_metadata"] is None
    exported = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert "Own words" in exported and "currently unavailable" in exported
    call(rt, "GET", "/learning/practice/" + item["id"], status=410)
    call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": 0, "response": {"selection": ["A"]}},
        status=410,
    )


def test_completed_step_sequence_has_no_next_task_and_full_help_does_not_complete(runtime):
    rt = runtime
    _, unit = source(rt)
    item = published(
        rt,
        draft(
            rt,
            unit,
            "step",
            options=[],
            rubric={
                "steps": [
                    {
                        "id": "one",
                        "prompt": "Convert length",
                        "numeric": {"value": 4.0, "unit": "m"},
                    }
                ],
                "explanation": "A disclosed solution",
            },
        ),
    )["item"]
    current = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    assert current["current_step_response_kind"] == "numeric" and current["expected_unit"] == "m"
    call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": 0,
            "response": {"step": 1, "value": 400.0, "unit": "cm"},
        },
    )
    done = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    assert (
        done["state"] == "completed"
        and done["current_step_prompt"] is None
        and done["expected_unit"] is None
    )


def test_internal_generated_proposal_is_unpublished_and_source_bound(runtime):
    from app.modules.learning_product import service
    from contracts.study import PracticeProposalInput, PracticeDraft

    rt = runtime
    _, unit = source(rt)
    body = PracticeDraft.model_validate(draft(rt, unit))
    proposal = PracticeProposalInput(
        source=body.source, kind=body.kind, concepts=body.concepts, conditions=body.conditions
    )
    with rt.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        value = service.create_proposed_item(
            db,
            actor,
            proposal,
            body,
            {
                "configuration_id": "authored-injected-fixture",
                "model": "scripted",
                "prompt_hash": "a" * 64,
            },
        )
        assert (
            value["state"] == "draft"
            and value["validation_details"]["proposal_origin"] == "model_generated_unreviewed"
        )
        db.commit()
        changed = body.model_copy(update={"conditions": ["different condition"]})
        with pytest.raises(AppError):
            service.create_proposed_item(db, actor, proposal, changed, {"model": "scripted"})
    call(rt, "GET", "/learning/practice/" + value["item"]["id"], status=404)
