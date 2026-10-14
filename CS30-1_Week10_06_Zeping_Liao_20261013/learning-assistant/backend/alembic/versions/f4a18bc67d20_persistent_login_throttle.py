"""Add shared login throttling and immutable visual-region audit tables.

Revision ID: f4a18bc67d20
Revises: f3d97fa0456e
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a18bc67d20"
down_revision = "f3d97fa0456e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_login_limits",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "visual_regions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "document_version_id",
            sa.String(36),
            sa.ForeignKey("document_versions.id"),
            nullable=False,
        ),
        sa.Column("physical_page", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("native_text", sa.Text(), nullable=False),
        sa.Column("candidate_status", sa.String(40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("extractor_revision", sa.String(80), nullable=False),
        sa.Column("catalog_sha256", sa.String(64), nullable=False),
    )
    op.create_index("ix_visual_regions_document_version_id", "visual_regions", ["document_version_id"])
    op.create_index("ix_visual_regions_physical_page", "visual_regions", ["physical_page"])
    op.create_table(
        "visual_region_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.String(64), sa.ForeignKey("visual_regions.id"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_visual_region_reviews_region_id", "visual_region_reviews", ["region_id"])
    op.create_index("ix_visual_region_reviews_reviewer_id", "visual_region_reviews", ["reviewer_id"])


def downgrade():
    op.drop_table("visual_region_reviews")
    op.drop_table("visual_regions")
    op.drop_table("auth_login_limits")
