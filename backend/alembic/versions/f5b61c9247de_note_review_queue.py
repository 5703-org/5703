"""Add owned personal review cards to the existing review queue.

Revision ID: f5b61c9247de
Revises: f4a18bc67d20
"""

import datetime as dt
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "f5b61c9247de"
down_revision = "f4a18bc67d20"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "study_review_entries",
        "item_id",
        existing_type=sa.String(length=36),
        nullable=True,
    )
    op.add_column(
        "study_review_entries",
        sa.Column("note_id", sa.String(length=36), sa.ForeignKey("study_notes.id"), nullable=True),
    )
    op.create_index("ix_study_review_entries_note_id", "study_review_entries", ["note_id"])
    op.create_unique_constraint(
        "uq_review_owner_note", "study_review_entries", ["owner_id", "note_id"]
    )
    op.create_check_constraint(
        "ck_review_exactly_one_target",
        "study_review_entries",
        "(item_id IS NOT NULL) <> (note_id IS NOT NULL)",
    )

    # Existing personal cards gain queue entries without changing their note records.
    connection = op.get_bind()
    existing = connection.execute(
        sa.text(
            "SELECT id, owner_id FROM study_notes WHERE kind = 'review_card' ORDER BY created_at, id"
        )
    )
    now = dt.datetime.now(dt.timezone.utc)
    for note_id, owner_id in existing:
        connection.execute(
            sa.text(
                "INSERT INTO study_review_entries "
                "(id, created_at, updated_at, version, owner_id, item_id, note_id, "
                "due_at, error_categories, attempt_count, correct_count, scheduling_reason) "
                "VALUES (:id, :created_at, :updated_at, 1, :owner_id, NULL, :note_id, "
                ":due_at, CAST(:error_categories AS json), 0, 0, :scheduling_reason)"
            ),
            {
                "id": str(uuid4()),
                "created_at": now,
                "updated_at": now,
                "owner_id": owner_id,
                "note_id": note_id,
                "due_at": now,
                "error_categories": "[]",
                "scheduling_reason": "Existing personal review card added to the queue; due now.",
            },
        )


def downgrade():
    connection = op.get_bind()
    count = connection.scalar(
        sa.text("SELECT count(*) FROM study_review_entries WHERE note_id IS NOT NULL")
    )
    if count:
        raise RuntimeError(
            "Remove personal review-card queue entries before downgrading this schema."
        )
    op.drop_constraint("ck_review_exactly_one_target", "study_review_entries", type_="check")
    op.drop_constraint("uq_review_owner_note", "study_review_entries", type_="unique")
    op.drop_index("ix_study_review_entries_note_id", table_name="study_review_entries")
    op.drop_column("study_review_entries", "note_id")
    op.alter_column(
        "study_review_entries", "item_id", existing_type=sa.String(length=36), nullable=False
    )
