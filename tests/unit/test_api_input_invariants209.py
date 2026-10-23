"""Synthetic HTTP and SQLite regressions for rejected-input atomicity."""

import datetime as dt
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from passlib.exc import UnknownHashError
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
from app.api.v1.deps import get_current_user
from app.core import security
from app.core.config import get_settings
from app.core.exceptions import AppError, register_exception_handlers
from app.db.session import get_db
from app.modules.answering import router as answering_router
from app.modules.identity import accounts
from app.modules.identity.models import Role, User, Workspace
from app.modules.identity.schemas import LoginRequest
from app.modules.learning import router as session_router
from app.modules.learning.models import ChatSession
from app.modules.learning.schemas import SessionCreate, SessionRename
from app.modules.learning_product import router as study_router, service as study
from app.modules.learning_product.models import LearningRecord, ReviewEntry, StudyNote
from app.modules.learning_state import memory, router as memory_router
from app.modules.learning_state.models import (
    MemoryEntry,
    MemoryRevision,
    MemorySettings,
    MemoryWriteEvent,
)
from app.platform_core.models import OutboxEvent
from contracts.models import ChatMessageCreate
from contracts.study import NoteCreate, NoteUpdate


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        Workspace,
        Role,
        User,
        ChatSession,
        OutboxEvent,
        StudyNote,
        ReviewEntry,
        LearningRecord,
        MemorySettings,
        MemoryEntry,
        MemoryRevision,
        MemoryWriteEvent,
    ):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    old_hash = security.hash_password("Passw0rd!")
    with factory() as db:
        db.add_all(
            [
                Workspace(id="workspace", name="Synthetic", slug="synthetic"),
                Role(id=1, name="student"),
                User(
                    id="owner",
                    email="owner@example.com",
                    hashed_password=old_hash,
                    role_id=1,
                    workspace_id="workspace",
                ),
                ChatSession(id="chat", user_id="owner", workspace_id="workspace", title="Original"),
                MemorySettings(owner_id="owner", enabled=True),
                MemoryEntry(
                    id="memory",
                    owner_id="owner",
                    category="preference",
                    canonical_key="legacy",
                    content="Original preference",
                    scope="global",
                ),
            ]
        )
        db.commit()
    actor = SimpleNamespace(id="owner", workspace_id="workspace")

    def database():
        with factory() as db:
            yield db

    def authenticated(db=Depends(get_db)):
        return db.get(User, "owner")

    app = FastAPI()
    register_exception_handlers(app)
    for router in (
        session_router.router,
        answering_router.router,
        accounts.router,
        study_router.router,
        memory_router.router,
    ):
        app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = authenticated
    # No runtime configuration or credentials are read. Invalid chat requests
    # must fail before the native submission service consumes these settings.
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(client=client, db=factory, actor=actor, old_hash=old_hash)
    engine.dispose()


@pytest.mark.parametrize(
    "path,method,body,field",
    [
        ("/sessions", "post", {"title": "Bad\x00title"}, "title"),
        ("/sessions/chat", "patch", {"title": "Bad\x00title", "version": 1}, "title"),
        ("/sessions/chat/messages", "post", {"content": "Explain\x00diffusion"}, "content"),
    ],
)
def test_actual_nul_is_field_validation_before_native_database_write(
    api, path, method, body, field
):
    response = getattr(api.client, method)(
        "/api/v1" + path, json=body, headers={"Idempotency-Key": "synthetic-invalid"}
    )
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_FAILED"
    assert any(
        v["loc"] == ["body", field] and "U+0000" in v["msg"] for v in error["details"]["violations"]
    )
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(ChatSession)) == 1
        assert db.get(ChatSession, "chat").title == "Original"
        assert db.get(ChatSession, "chat").version == 1
        assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 0
    followup = api.client.patch("/api/v1/sessions/chat", json={"title": "正常 🌿", "version": 1})
    assert followup.status_code == 200
    assert followup.json()["data"]["title"] == "正常 🌿"


@pytest.mark.parametrize("text", [r"literal\u0000", "Explain diffusion 🌿", "Normal\nline\tend"])
def test_valid_text_and_literal_escape_are_preserved(text):
    assert ChatMessageCreate(content=text).content == text
    assert SessionCreate(title=text).title == text
    assert SessionRename(title=text, version=1).title == text


def make_card(api, content="A complete personal prompt and answer"):
    result = api.client.post(
        "/api/v1/learning/notes",
        json={
            "title": "Synthetic recall",
            "content": content,
            "kind": "review_card",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["data"]


@pytest.mark.parametrize("blank", ["", "   ", " \n\t ", "\u2003\n"])
def test_create_and_edit_review_cards_reject_blank_without_changing_version_or_history(api, blank):
    rejected = api.client.post(
        "/api/v1/learning/notes",
        json={
            "title": "Synthetic recall",
            "content": blank,
            "kind": "review_card",
        },
    )
    assert rejected.status_code == 422
    card = make_card(api)
    edited = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "title": "Must not be applied",
            "content": blank,
        },
    )
    assert edited.status_code == 422, edited.text
    with api.db() as db:
        note = db.get(StudyNote, card["id"])
        assert (note.title, note.content, note.version) == (card["title"], card["content"], 1)
        assert db.scalar(select(func.count()).select_from(LearningRecord)) == 1
    good = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "content": "Updated 🌿 answer",
        },
    )
    assert good.status_code == 200
    assert good.json()["data"]["version"] == 2


@pytest.mark.parametrize("outcome", ["recalled", "needs_review"])
def test_legacy_blank_card_stays_readable_and_repairable_but_cannot_increment_recall(api, outcome):
    card = make_card(api)
    with api.db() as db:
        note = db.get(StudyNote, card["id"])
        note.content = " \n\t "  # Retained invalid legacy state, not an API path.
        review = db.scalar(select(ReviewEntry).where(ReviewEntry.note_id == note.id))
        review.attempt_count, review.correct_count = 3, 2
        saved = (review.id, review.due_at, review.scheduling_reason)
        db.commit()
    queue = api.client.get("/api/v1/learning/review?due_only=false")
    assert queue.status_code == 200
    assert queue.json()["data"][0]["card_content"] == " \n\t "
    response = api.client.post(
        "/api/v1/learning/review/" + saved[0] + "/record",
        json={
            "expected_version": 1,
            "outcome": outcome,
        },
    )
    assert response.status_code == 422, response.text
    with api.db() as db:
        review = db.get(ReviewEntry, saved[0])
        assert (review.version, review.attempt_count, review.correct_count) == (1, 3, 2)
        assert (review.due_at, review.scheduling_reason) == saved[1:]
        assert db.scalar(select(func.count()).select_from(LearningRecord)) == 1
    title_only = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "title": "A title cannot repair the content",
        },
    )
    assert title_only.status_code == 422
    repair = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "content": "Repaired personal answer",
        },
    )
    assert repair.status_code == 200
    recalled = api.client.post(
        "/api/v1/learning/review/" + saved[0] + "/record",
        json={
            "expected_version": 1,
            "outcome": outcome,
        },
    )
    assert recalled.status_code == 200
    data = recalled.json()["data"]
    assert data["attempt_count"] == 4
    assert data["correct_count"] == (3 if outcome == "recalled" else 2)


def test_blank_ordinary_note_and_partial_review_edit_remain_valid(api):
    result = api.client.post("/api/v1/learning/notes", json={"title": "Empty note", "content": ""})
    assert result.status_code == 201
    card = make_card(api)
    patch = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "title": "Renamed personal card",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["content"] == card["content"]
    stale = api.client.patch(
        "/api/v1/learning/notes/" + card["id"],
        json={
            "expected_version": 1,
            "content": "Must not overwrite",
        },
    )
    assert stale.status_code == 409
    with pytest.raises(ValidationError):
        NoteUpdate(expected_version=1, kind="review_card")
    assert NoteCreate(title="ordinary").kind == "note"


@pytest.mark.parametrize("length", [129, 4096, 4097])
def test_oversized_old_password_is_rejected_without_credential_or_token_mutation(api, length):
    response = api.client.post(
        "/api/v1/users/me/password",
        json={
            "old_password": "x" * length,
            "new_password": "NewSynthetic1!",
        },
    )
    assert response.status_code == 422
    with api.db() as db:
        user = db.get(User, "owner")
        assert user.hashed_password == api.old_hash
        assert (user.version, user.token_version) == (1, 1)
        assert security.verify_password("Passw0rd!", user.hashed_password)


@pytest.mark.parametrize("password", ["Passw0rd!", "x" * 128, "🌿" * 128])
def test_supported_login_passwords_keep_existing_pbkdf2_compatibility(password):
    assert LoginRequest(email="owner@example.com", password=password).password == password
    assert accounts.PasswordChange(old_password=password, new_password="NewSynthetic1!")
    hashed = security.hash_password(password)
    assert security.verify_password(password, hashed)
    assert not security.verify_password("WrongSynthetic1!", hashed)


def test_wrong_then_legacy_eight_character_old_password_change_is_controlled(api):
    wrong = api.client.post(
        "/api/v1/users/me/password",
        json={
            "old_password": "WrongSynthetic1!",
            "new_password": "NewSynthetic1!",
        },
    )
    assert wrong.status_code == 401, wrong.text
    with api.db() as db:
        user = db.get(User, "owner")
        assert (user.version, user.token_version, user.hashed_password) == (1, 1, api.old_hash)
    changed = api.client.post(
        "/api/v1/users/me/password",
        json={
            "old_password": "Passw0rd!",
            "new_password": "NewSynthetic1!",
        },
    )
    assert changed.status_code == 200, changed.text
    with api.db() as db:
        user = db.get(User, "owner")
        assert (user.version, user.token_version) == (2, 2)
        assert security.verify_password("NewSynthetic1!", user.hashed_password)


def test_only_passlib_size_error_becomes_validation_error(monkeypatch):
    with pytest.raises(AppError, match="Password is too long") as size:
        security.verify_password("x" * 4097, security.hash_password("Passw0rd!"))
    assert size.value.code == "VALIDATION_FAILED"
    with pytest.raises(UnknownHashError):
        security.verify_password("Passw0rd!", "broken-configuration-hash")

    def broken(*args):
        raise RuntimeError("Synthetic configuration defect")

    monkeypatch.setattr(security.pwd_context, "verify", broken)
    with pytest.raises(RuntimeError, match="configuration defect"):
        security.verify_password("Passw0rd!", "unused")


@pytest.mark.parametrize(
    "expiry",
    [
        "9999-12-31T23:59:59-12:00",
        "0001-01-01T00:00:00+12:00",
        "not-a-date",
        "2027-01-10T23:59:59",
        "",
    ],
)
def test_invalid_expiry_rejects_before_any_entry_revision_event_or_epoch_change(api, expiry):
    response = api.client.patch(
        "/api/v1/me/memories/memory",
        json={
            "version": 1,
            "content": "Changed preference",
            "scope": "global",
            "expires_at": expiry,
        },
    )
    assert response.status_code == 422, response.text
    with api.db() as db:
        row = db.get(MemoryEntry, "memory")
        settings = db.scalar(select(MemorySettings))
        assert (row.version, row.content, row.expires_at) == (1, "Original preference", None)
        assert (settings.event_sequence, settings.revocation_epoch) == (0, 0)
        assert db.scalar(select(func.count()).select_from(MemoryWriteEvent)) == 0
        assert db.scalar(select(func.count()).select_from(MemoryRevision)) == 0


@pytest.mark.parametrize(
    "expiry,expected",
    [
        ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00+00:00"),
        ("9999-12-31T23:59:59Z", "9999-12-31T23:59:59+00:00"),
        ("2027-01-10T23:59:59+12:00", "2027-01-10T11:59:59+00:00"),
        (None, None),
    ],
)
def test_expiry_supported_utc_range_offset_and_null_semantics(expiry, expected):
    parsed = memory.parse_expiry(expiry)
    assert (parsed.isoformat() if parsed else None) == expected
    if parsed:
        assert parsed.tzinfo == dt.timezone.utc


def test_valid_expiry_followup_uses_actual_memory_commit(api):
    # No private drafts/snapshots/jobs exist in this narrow fixture. Their
    # unchanged revocation service is exercised in the integrated PG checkpoint.
    from app.modules.answering.models import AnswerRequest, Job, Message
    from app.modules.learning_state.models import MemorySnapshot, PrivateAnswerDraft

    with api.db() as db:
        for model in (Message, AnswerRequest, Job, MemorySnapshot, PrivateAnswerDraft):
            model.__table__.create(db.bind)
    response = api.client.patch(
        "/api/v1/me/memories/memory",
        json={
            "version": 1,
            "content": "Prefer concise answers",
            "scope": "global",
            "expires_at": "2027-01-10T23:59:59Z",
        },
    )
    assert response.status_code == 200, response.text
    with api.db() as db:
        row = db.get(MemoryEntry, "memory")
        assert row.version == 2
        assert row.expires_at == dt.datetime(2027, 1, 10, 23, 59, 59)
        assert db.scalar(select(func.count()).select_from(MemoryRevision)) == 1
        assert db.scalar(select(func.count()).select_from(MemoryWriteEvent)) == 1
