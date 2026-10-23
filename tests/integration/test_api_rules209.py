"""Owned Phase209 PostgreSQL input, card-lock and logout integration."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from threading import Barrier, Event
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.cli import seed
from app.modules.answering.models import AnswerRequest, Job, Message
from app.modules.identity import sessions
from app.modules.identity.models import RevokedSession, User
from app.modules.learning.models import ChatSession
from app.modules.learning_product import service as study
from app.modules.learning_product.models import LearningRecord, ReviewEntry, StudyNote
from app.modules.learning_state.models import (
    MemoryEntry,
    MemoryRevision,
    MemorySettings,
    MemoryWriteEvent,
)
from contracts.study import NoteUpdate, ReviewCardAction


@pytest.fixture(scope="module")
def owned_runtime(tmp_path_factory, postgres_url):
    url = make_url(postgres_url)
    assert url.database.startswith("cs30_test_")
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=url.render_as_string(hide_password=False),
        jwt_secret="synthetic-phase209-rules-secret-at-least-thirty-two-characters",
        storage_root=str(tmp_path_factory.mktemp("storage")),
        model_mode="mock",
        llm_provider="mock",
        llm_api_key=None,
        local_model_device="recorded",
        chat_query_preparation_policy="recorded",
        chat_relevance_gate=False,
        chat_retrieval_cache=False,
    )
    app = create_app(settings)
    factory = sessionmaker(bind=app.state.engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed(db)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, factory, settings
    app.state.engine.dispose()


def login(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "student@example.com", "password": "Passw0rd!"}
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}


def call(client, method, path, body=None, auth=None, expected=200, key=None):
    headers = dict(auth or {})
    if key:
        headers["Idempotency-Key"] = key
    response = client.request(method, "/api/v1" + path, json=body, headers=headers)
    assert response.status_code == expected, (response.status_code, path)
    return response.json()


def counts(db, *models):
    return [db.scalar(select(func.count()).select_from(model)) for model in models]


def card(client, auth):
    return call(
        client,
        "POST",
        "/learning/notes",
        {
            "title": "Synthetic PG card " + uuid4().hex[:8],
            "content": "Original prompt and answer",
            "kind": "review_card",
        },
        auth,
        201,
    )["data"]


def test_postgres_nul_ingress_preserves_counts_and_immediate_valid_chat_is_accepted_then_cancelled(
    owned_runtime,
):
    client, factory, _ = owned_runtime
    auth = login(client)
    chat = call(client, "POST", "/sessions", {"title": "Synthetic input boundary"}, auth)["data"]
    with factory() as db:
        before = counts(db, ChatSession, Message, AnswerRequest, Job)
    call(client, "POST", "/sessions", {"title": "bad\x00title"}, auth, 422)
    call(
        client,
        "PATCH",
        "/sessions/" + chat["id"],
        {"title": "bad\x00title", "version": 1},
        auth,
        422,
    )
    call(
        client,
        "POST",
        "/sessions/" + chat["id"] + "/messages",
        {
            "content": "bad\x00question",
            "answer_mode": "general_knowledge",
            "use_profile": False,
            "check_answer": False,
        },
        auth,
        422,
        "nul-" + uuid4().hex,
    )
    with factory() as db:
        assert counts(db, ChatSession, Message, AnswerRequest, Job) == before
        assert db.get(ChatSession, chat["id"]).version == 1
    call(
        client,
        "PATCH",
        "/sessions/" + chat["id"],
        {"title": "Valid Unicode 🌿", "version": 1},
        auth,
    )
    receipt = call(
        client,
        "POST",
        "/sessions/" + chat["id"] + "/messages",
        {
            "content": "Synthetic question for queue validation only",
            "answer_mode": "general_knowledge",
            "use_profile": False,
            "check_answer": False,
        },
        auth,
        202,
        "good-" + uuid4().hex,
    )["data"]
    job_id = receipt["job_id"]
    call(client, "POST", "/jobs/" + job_id + "/cancel", auth=auth)
    with factory() as db:
        assert db.get(Job, job_id).state == "cancelled"
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.session_id == chat["id"])
            )
            == 1
        )


def test_postgres_blank_card_rejects_atomically_and_legacy_card_can_be_repaired(owned_runtime):
    client, factory, _ = owned_runtime
    auth = login(client)
    note = card(client, auth)
    with factory() as db:
        event_count = counts(db, LearningRecord)
        review = db.scalar(select(ReviewEntry).where(ReviewEntry.note_id == note["id"]))
        review_id = review.id
        before = (review.version, review.attempt_count, review.correct_count, review.due_at)
    call(
        client,
        "PATCH",
        "/learning/notes/" + note["id"],
        {
            "expected_version": 1,
            "title": "Must not persist",
            "content": " \n\t ",
        },
        auth,
        422,
    )
    with factory() as db:
        saved = db.get(StudyNote, note["id"])
        assert (saved.version, saved.title, saved.content) == (1, note["title"], note["content"])
        assert counts(db, LearningRecord) == event_count
        saved.content = " \n\t "  # Synthetic retained historical invalid state.
        db.commit()
    call(
        client,
        "POST",
        "/learning/review/" + review_id + "/record",
        {
            "expected_version": 1,
            "outcome": "recalled",
        },
        auth,
        422,
    )
    with factory() as db:
        review = db.get(ReviewEntry, review_id)
        assert (review.version, review.attempt_count, review.correct_count, review.due_at) == before
        assert counts(db, LearningRecord) == event_count
    call(
        client,
        "PATCH",
        "/learning/notes/" + note["id"],
        {
            "expected_version": 1,
            "content": "Repaired personal answer",
        },
        auth,
    )
    repaired = call(
        client,
        "POST",
        "/learning/review/" + review_id + "/record",
        {
            "expected_version": 1,
            "outcome": "recalled",
        },
        auth,
    )["data"]
    assert (repaired["attempt_count"], repaired["correct_count"]) == (1, 1)


def test_postgres_edit_then_recall_waits_for_actual_row_lock(owned_runtime):
    client, factory, _ = owned_runtime
    auth = login(client)
    note = card(client, auth)
    with factory() as db:
        review_id = db.scalar(select(ReviewEntry.id).where(ReviewEntry.note_id == note["id"]))
        owner_id = db.scalar(select(User.id).where(User.email == "student@example.com"))
    edit_locked, release_edit, recall_started = Event(), Event(), Event()
    recall_pid = []

    def edit():
        with factory() as db:
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            result = study.edit_note(
                db,
                db.get(User, owner_id),
                note["id"],
                NoteUpdate(
                    expected_version=1,
                    content="Committed before recall",
                ),
            )
            edit_locked.set()
            if not release_edit.wait(5):
                raise TimeoutError("Synthetic lock release timed out")
            db.commit()
            return result["version"]

    def recall():
        with factory() as db:
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            recall_pid.append(db.scalar(text("SELECT pg_backend_pid()")))
            recall_started.set()
            result = study.record_review_card(
                db,
                db.get(User, owner_id),
                review_id,
                ReviewCardAction(expected_version=1, outcome="recalled"),
            )
            db.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        editor = pool.submit(edit)
        assert edit_locked.wait(5)
        recaller = pool.submit(recall)
        try:
            assert recall_started.wait(5)
            deadline = time.monotonic() + 3
            observed_wait = False
            while time.monotonic() < deadline:
                with factory() as db:
                    observed_wait = (
                        db.scalar(
                            text(
                                "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid AND datname=current_database()"
                            ),
                            {"pid": recall_pid[0]},
                        )
                        is True
                    )
                if observed_wait:
                    break
                time.sleep(0.02)
            assert observed_wait
            assert not recaller.done()
        finally:
            release_edit.set()
        assert editor.result(timeout=8) == 2
        result = recaller.result(timeout=8)
        assert result["card_content"] == "Committed before recall"
        assert (result["attempt_count"], result["correct_count"]) == (1, 1)


def test_postgres_expiry_overflow_preserves_entry_events_and_revisions(owned_runtime):
    client, factory, _ = owned_runtime
    auth = login(client)
    with factory() as db:
        owner = db.scalar(select(User).where(User.email == "student@example.com"))
        settings = db.scalar(select(MemorySettings).where(MemorySettings.owner_id == owner.id))
        if settings is None:
            settings = MemorySettings(owner_id=owner.id, enabled=True)
            db.add(settings)
        row = MemoryEntry(
            owner_id=owner.id,
            category="preference",
            canonical_key=uuid4().hex,
            content="Original preference",
            scope="global",
        )
        db.add(row)
        db.commit()
        entry_id = row.id
        original = (settings.event_sequence, settings.revocation_epoch)
        before_counts = counts(db, MemoryRevision, MemoryWriteEvent)
    for expiry in ("9999-12-31T23:59:59-12:00", "0001-01-01T00:00:00+12:00"):
        call(
            client,
            "PATCH",
            "/me/memories/" + entry_id,
            {
                "version": 1,
                "content": "Must not persist",
                "scope": "global",
                "expires_at": expiry,
            },
            auth,
            422,
        )
    with factory() as db:
        row = db.get(MemoryEntry, entry_id)
        settings = db.scalar(select(MemorySettings).where(MemorySettings.owner_id == row.owner_id))
        assert (row.version, row.content, row.expires_at) == (1, "Original preference", None)
        assert (settings.event_sequence, settings.revocation_epoch) == original
        assert counts(db, MemoryRevision, MemoryWriteEvent) == before_counts
    call(
        client,
        "PATCH",
        "/me/memories/" + entry_id,
        {
            "version": 1,
            "content": "Prefer concise answers",
            "scope": "global",
            "expires_at": "2027-01-10T23:59:59Z",
        },
        auth,
    )
    with factory() as db:
        assert db.get(MemoryEntry, entry_id).expires_at == datetime(
            2027, 1, 10, 23, 59, 59, tzinfo=timezone.utc
        )


def test_postgres_oversized_old_password_leaves_credentials_and_versions_unchanged(owned_runtime):
    client, factory, _ = owned_runtime
    auth = login(client)
    with factory() as db:
        user = db.scalar(select(User).where(User.email == "student@example.com"))
        original = (user.hashed_password, user.version, user.token_version)
    call(
        client,
        "POST",
        "/users/me/password",
        {"old_password": "x" * 4097, "new_password": "SyntheticNew1!"},
        auth,
        422,
    )
    with factory() as db:
        user = db.scalar(select(User).where(User.email == "student@example.com"))
        unchanged = (user.hashed_password, user.version, user.token_version) == original
        assert unchanged
    login(client)


def test_postgres_concurrent_logout_is_unique_and_other_login_survives(owned_runtime):
    client, factory, settings = owned_runtime
    first, second = login(client), login(client)
    token = first["Authorization"].removeprefix("Bearer ")
    gate = Barrier(2)

    def revoke_once():
        with factory() as db:
            current = sessions.authenticate(db, token, settings, allow_revoked=True)
            gate.wait(timeout=5)
            sessions.revoke(db, current)
            return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(revoke_once) for _ in range(2)]
        assert all(future.result(timeout=10) for future in futures)
    call(client, "GET", "/users/me", auth=first, expected=401)
    call(client, "POST", "/auth/logout", auth=first)
    call(client, "GET", "/users/me", auth=second)
    with factory() as db:
        current = sessions.authenticate(db, token, settings, allow_revoked=True)
        assert (
            db.scalar(
                select(func.count())
                .select_from(RevokedSession)
                .where(RevokedSession.identity_hash == current.identity_hash)
            )
            == 1
        )


def test_postgres_logout_commit_failure_rolls_back_native_insert(owned_runtime):
    client, factory, settings = owned_runtime
    auth = login(client)
    token = auth["Authorization"].removeprefix("Bearer ")
    with factory() as db:
        current = sessions.authenticate(db, token, settings)

        def fail_commit(session):
            raise RuntimeError("Synthetic commit failure")

        event.listen(db, "before_commit", fail_commit)
        with pytest.raises(RuntimeError, match="Synthetic commit failure"):
            sessions.revoke(db, current)
        db.rollback()
    call(client, "GET", "/users/me", auth=auth)
    with factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(RevokedSession)
                .where(RevokedSession.identity_hash == current.identity_hash)
            )
            == 0
        )
