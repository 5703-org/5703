"""Add reading, learning goals, private practice, revision and personal notes."""

from alembic import op
import sqlalchemy as sa

revision = "f3d97fa0456e"
down_revision = "f2c86e9f345d"
branch_labels = None
depends_on = None


def common():
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    ]


def fk(name, target, nullable=False):
    return sa.Column(name, sa.String(36), sa.ForeignKey(target), nullable=nullable)


def col(name, kind, nullable=False):
    return sa.Column(name, kind, nullable=nullable)


def upgrade():
    op.create_table(
        "reading_positions",
        *common(),
        fk("owner_id", "users.id"),
        fk("document_id", "documents.id"),
        col("source", sa.JSON()),
        col("char_offset", sa.Integer()),
        sa.UniqueConstraint("owner_id", "document_id"),
    )
    op.create_table(
        "study_goals",
        *common(),
        fk("owner_id", "users.id"),
        col("title", sa.String(200)),
        fk("document_id", "documents.id"),
        fk("release_id", "corpus_releases.id"),
        col("depth", sa.String(30)),
        col("state", sa.String(30)),
    )
    op.create_table(
        "study_goal_units",
        *common(),
        fk("goal_id", "study_goals.id"),
        col("section_id", sa.String(64)),
        col("title", sa.String(500)),
        col("ordinal", sa.Integer()),
        col("concepts", sa.JSON()),
        col("prerequisites", sa.JSON()),
        col("read", sa.Boolean()),
        sa.UniqueConstraint("goal_id", "section_id"),
    )
    op.create_table(
        "practice_items",
        *common(),
        fk("workspace_id", "workspaces.id"),
        fk("creator_id", "users.id"),
        col("group_id", sa.String(36)),
        col("item_revision", sa.Integer()),
        fk("previous_item_id", "practice_items.id", True),
        col("state", sa.String(30)),
        col("public_payload", sa.JSON()),
        col("private_rubric", sa.JSON()),
        col("source", sa.JSON()),
        col("validation", sa.JSON()),
        col("content_hash", sa.String(64)),
        sa.UniqueConstraint("group_id", "item_revision"),
    )
    op.create_table(
        "practice_progress",
        *common(),
        fk("owner_id", "users.id"),
        fk("item_id", "practice_items.id"),
        col("current_step", sa.Integer()),
        col("help_level", sa.Integer()),
        col("state", sa.String(30)),
        col("full_explanation", sa.Boolean()),
        col("shown_hints", sa.JSON()),
        sa.UniqueConstraint("owner_id", "item_id"),
    )
    op.create_table(
        "practice_attempts",
        *common(),
        fk("owner_id", "users.id"),
        fk("item_id", "practice_items.id"),
        fk("progress_id", "practice_progress.id"),
        fk("goal_id", "study_goals.id", True),
        col("idempotency_key", sa.String(128)),
        col("body_hash", sa.String(64)),
        col("item_revision", sa.Integer()),
        col("response", sa.JSON()),
        col("feedback", sa.JSON()),
        col("progress_version", sa.Integer()),
        sa.UniqueConstraint("owner_id", "idempotency_key"),
    )
    op.create_table(
        "study_review_entries",
        *common(),
        fk("owner_id", "users.id"),
        fk("item_id", "practice_items.id"),
        col("due_at", sa.DateTime(timezone=True)),
        col("error_categories", sa.JSON()),
        col("attempt_count", sa.Integer()),
        col("correct_count", sa.Integer()),
        col("scheduling_reason", sa.String(200)),
        sa.UniqueConstraint("owner_id", "item_id"),
    )
    op.create_table(
        "study_notes",
        *common(),
        fk("owner_id", "users.id"),
        col("title", sa.String(200)),
        col("content", sa.Text()),
        col("kind", sa.String(30)),
        col("source", sa.JSON(), True),
        fk("answer_id", "answers.id", True),
        fk("goal_id", "study_goals.id", True),
        col("concepts", sa.JSON()),
    )
    op.create_table(
        "learning_records",
        *common(),
        fk("owner_id", "users.id"),
        col("kind", sa.String(40)),
        col("object_id", sa.String(36)),
        col("details", sa.JSON()),
    )
    for table, field in (
        ("reading_positions", "owner_id"),
        ("study_goals", "owner_id"),
        ("study_goal_units", "goal_id"),
        ("practice_items", "workspace_id"),
        ("practice_progress", "owner_id"),
        ("practice_attempts", "owner_id"),
        ("practice_attempts", "item_id"),
        ("study_review_entries", "owner_id"),
        ("study_review_entries", "due_at"),
        ("study_notes", "owner_id"),
        ("learning_records", "owner_id"),
    ):
        op.create_index(f"ix_{table}_{field}", table, [field])


def downgrade():
    for table in (
        "learning_records",
        "study_notes",
        "study_review_entries",
        "practice_attempts",
        "practice_progress",
        "practice_items",
        "study_goal_units",
        "study_goals",
        "reading_positions",
    ):
        op.drop_table(table)
