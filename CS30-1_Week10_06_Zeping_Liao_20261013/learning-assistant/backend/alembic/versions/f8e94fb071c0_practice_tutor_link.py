"""Link owned practice progress to a learner-visible tutoring task.

Revision ID: f8e94fb071c0
Revises: f7d83ea960bf
"""

from alembic import op
import sqlalchemy as sa

revision = "f8e94fb071c0"
down_revision = "f7d83ea960bf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "practice_progress",
        sa.Column(
            "tutor_task_id", sa.String(length=36), sa.ForeignKey("learning_tasks.id"), nullable=True
        ),
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM practice_progress WHERE tutor_task_id IS NOT NULL")
    ):
        raise RuntimeError("Archive and explicitly detach linked practice tutors before downgrade.")
    op.drop_column("practice_progress", "tutor_task_id")
