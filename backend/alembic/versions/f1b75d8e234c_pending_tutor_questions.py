"""Persist versioned tutor questions and learner-attempt progress."""

from alembic import op
import sqlalchemy as sa

revision = "f1b75d8e234c"
down_revision = "e0a64c7d123b"
branch_labels = None
depends_on = None


def upgrade():
    for column in (
        sa.Column("pending_tutor_question_id", sa.String(36), nullable=True),
        sa.Column("pending_tutor_question", sa.Text(), nullable=True),
        sa.Column("pending_tutor_question_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_response_kind", sa.String(20), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("turn_role", sa.String(20), nullable=False, server_default="user_question"),
        sa.Column("last_attempt_evaluation", sa.JSON(), nullable=True),
    ):
        op.add_column("learning_tasks", column)


def downgrade():
    for name in (
        "last_attempt_evaluation", "turn_role", "current_step", "expected_response_kind",
        "pending_tutor_question_version", "pending_tutor_question", "pending_tutor_question_id",
    ):
        op.drop_column("learning_tasks", name)
