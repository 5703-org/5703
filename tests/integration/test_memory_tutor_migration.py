"""Additive controls and tutoring links preserve existing rows on rollback refusal."""

from uuid import uuid4
from alembic import command
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.modules.identity.models import User
from app.modules.answering.models import Message
from app.modules.learning.models import ChatSession
from app.modules.learning_state.models import LearningTask
from app.modules.learning_product.models import PracticeItem, PracticeProgress
from .test_learning_migration_safety import isolated_schema, rows, head


def test_memory_controls_upgrade_preserves_old_content_and_guarded_downgrade(
    postgres_url, monkeypatch
):
    with isolated_schema(postgres_url, monkeypatch, "f6c72db859ae") as (engine, config):
        with engine.begin() as connection:
            actor = connection.scalar(
                text("SELECT id FROM users WHERE email = 'student@example.com'")
            )
            connection.execute(
                text(
                    "INSERT INTO learning_memory_entries (id,created_at,updated_at,version,owner_id,category,canonical_key,content,scope,status) VALUES (:id,now(),now(),1,:owner,'goal',:key,'Preserved migration fixture goal.','biology','active')"
                ),
                {"id": str(uuid4()), "owner": actor, "key": "a" * 64},
            )
        before = rows(engine, "learning_memory_entries")
        command.upgrade(config, "f7d83ea960bf")
        after = rows(engine, "learning_memory_entries")
        assert [
            {key: value for key, value in row.items() if key != "match_policy"} for row in after
        ] == before
        assert after[0]["match_policy"] == "rules_only"
        with engine.begin() as connection:
            connection.execute(text("UPDATE learning_memory_entries SET status = 'paused'"))
        paused = rows(engine, "learning_memory_entries")
        with pytest.raises(RuntimeError, match="Resume paused memories"):
            command.downgrade(config, "f6c72db859ae")
        assert head(engine) == "f7d83ea960bf" and rows(engine, "learning_memory_entries") == paused
        with engine.begin() as connection:
            connection.execute(text("UPDATE learning_memory_entries SET status = 'active'"))
        command.downgrade(config, "f6c72db859ae")
        assert rows(engine, "learning_memory_entries") == before


def test_tutor_link_rollback_refuses_to_drop_association_and_preserves_task(
    postgres_url, monkeypatch
):
    with isolated_schema(postgres_url, monkeypatch, "f8e94fb071c0") as (engine, config):
        with sessionmaker(bind=engine, expire_on_commit=False)() as db:
            actor = db.scalar(select(User).where(User.email == "student@example.com"))
            session = ChatSession(
                user_id=actor.id,
                workspace_id=actor.workspace_id,
                title="Migration-only tutor fixture",
            )
            item = PracticeItem(
                workspace_id=actor.workspace_id,
                creator_id=actor.id,
                group_id=str(uuid4()),
                item_revision=1,
                public_payload={},
                private_rubric={},
                source={},
                content_hash="0" * 64,
            )
            db.add_all([session, item])
            db.flush()
            message = Message(
                session_id=session.id,
                sequence=1,
                role="user",
                content="Preserved public fixture question.",
            )
            db.add(message)
            db.flush()
            task = LearningTask(
                owner_id=actor.id,
                session_id=session.id,
                initial_message_id=message.id,
                question=message.content,
                task_type="process_reasoning",
                requirements={"migration_fixture": True},
            )
            db.add(task)
            db.flush()
            db.add(PracticeProgress(owner_id=actor.id, item_id=item.id, tutor_task_id=task.id))
            db.commit()
        task_before, progress_before = (
            rows(engine, "learning_tasks"),
            rows(engine, "practice_progress"),
        )
        with pytest.raises(RuntimeError, match="explicitly detach linked practice tutors"):
            command.downgrade(config, "f7d83ea960bf")
        assert head(engine) == "f8e94fb071c0"
        assert (
            rows(engine, "learning_tasks") == task_before
            and rows(engine, "practice_progress") == progress_before
        )
        # A deliberate test-only detachment exercises the documented empty-link inverse.
        with engine.begin() as connection:
            connection.execute(text("UPDATE practice_progress SET tutor_task_id = NULL"))
        command.downgrade(config, "f7d83ea960bf")
        assert rows(engine, "learning_tasks") == task_before
        command.upgrade(config, "f8e94fb071c0")
        assert rows(engine, "practice_progress")[0]["tutor_task_id"] is None
