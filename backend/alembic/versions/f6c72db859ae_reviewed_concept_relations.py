"""Add a quarantined, reviewed registry for source-backed concept relations.

Revision ID: f6c72db859ae
Revises: f5b61c9247de
"""

from alembic import op
import sqlalchemy as sa


revision = "f6c72db859ae"
down_revision = "f5b61c9247de"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_concept_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("release_id", sa.String(36), sa.ForeignKey("corpus_releases.id"), nullable=False),
        sa.Column("from_section_id", sa.String(64), nullable=False),
        sa.Column("to_section_id", sa.String(64), nullable=False),
        sa.Column("from_concept", sa.String(200), nullable=False),
        sa.Column("to_concept", sa.String(200), nullable=False),
        sa.Column("relation_type", sa.String(20), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("source_quote", sa.Text(), nullable=False),
        sa.Column("source_quote_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("proposer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "relation_type IN ('prerequisite', 'related', 'confusion')",
            name="ck_study_relation_type",
        ),
        sa.CheckConstraint(
            "state IN ('proposed', 'approved', 'rejected')",
            name="ck_study_relation_state",
        ),
        sa.CheckConstraint(
            "from_section_id <> to_section_id", name="ck_study_relation_distinct_sections"
        ),
    )
    for name in ("workspace_id", "document_id", "release_id"):
        op.create_index(f"ix_study_concept_relations_{name}", "study_concept_relations", [name])


def downgrade():
    connection = op.get_bind()
    count = connection.scalar(sa.text("SELECT count(*) FROM study_concept_relations"))
    if count:
        raise RuntimeError("Preserve reviewed concept relation records before downgrading.")
    op.drop_table("study_concept_relations")
