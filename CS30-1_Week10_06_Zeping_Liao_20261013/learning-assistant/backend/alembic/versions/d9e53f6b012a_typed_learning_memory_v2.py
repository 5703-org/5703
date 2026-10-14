"""Add typed learning memory and ordered write events without rewriting legacy rows."""

from alembic import op
import sqlalchemy as sa

revision = "d9e53f6b012a"
down_revision = "c8d42e5a901f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "learning_memory_settings",
        sa.Column("event_sequence", sa.Integer(), nullable=False, server_default="0"),
    )
    for column in [
        sa.Column("field_key", sa.String(120), nullable=True),
        sa.Column("scope_topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "verification", sa.String(60), nullable=False, server_default="legacy_unverified"
        ),
        sa.Column(
            "writer_version",
            sa.String(60),
            nullable=False,
            server_default="explicit_learning_memory_v1",
        ),
        sa.Column("source_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_event_sequence", sa.Integer(), nullable=False, server_default="0"),
    ]:
        op.add_column("learning_memory_entries", column)
    op.add_column(
        "learning_memory_revisions",
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "learning_memory_write_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("source_message_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("operations", sa.JSON(), nullable=False),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.UniqueConstraint("owner_id", "source_message_id"),
        sa.UniqueConstraint("owner_id", "sequence"),
    )
    op.create_index(
        "ix_learning_memory_write_events_owner_id", "learning_memory_write_events", ["owner_id"]
    )


def downgrade():
    op.drop_table("learning_memory_write_events")
    op.drop_column("learning_memory_revisions", "details")
    for name in (
        "field_key",
        "scope_topics",
        "verification",
        "writer_version",
        "source_details",
        "effective_at",
        "source_event_sequence",
    ):
        op.drop_column("learning_memory_entries", name)
    op.drop_column("learning_memory_settings", "event_sequence")
