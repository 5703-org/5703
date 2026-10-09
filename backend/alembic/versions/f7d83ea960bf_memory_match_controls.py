"""Add conservative per-memory applicability controls.

Revision ID: f7d83ea960bf
Revises: f6c72db859ae
"""

from alembic import op
import sqlalchemy as sa

revision = "f7d83ea960bf"
down_revision = "f6c72db859ae"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "learning_memory_entries",
        sa.Column(
            "match_policy", sa.String(length=30), server_default="rules_only", nullable=False
        ),
    )


def downgrade():
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM learning_memory_entries WHERE status = 'paused' OR match_policy <> 'rules_only'"
        )
    ):
        raise RuntimeError(
            "Resume paused memories and restore rules-only matching before downgrade."
        )
    op.drop_column("learning_memory_entries", "match_policy")
