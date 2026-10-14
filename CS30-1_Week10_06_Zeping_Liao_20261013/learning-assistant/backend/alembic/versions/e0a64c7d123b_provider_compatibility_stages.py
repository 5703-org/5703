"""Add role-specific staged provider compatibility tests; preserve legacy history."""

from alembic import op
import sqlalchemy as sa

revision = "e0a64c7d123b"
down_revision = "d9e53f6b012a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("model_compatibility_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("configuration_id", sa.String(36), sa.ForeignKey("model_configurations.id"), nullable=False),
        sa.Column("tested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("network_label", sa.String(80), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("test_version", sa.String(60), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("diagnostic_code", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("configuration_id", "idempotency_key", name="uq_model_probe_key"))
    op.create_index("ix_model_compatibility_runs_configuration_id", "model_compatibility_runs", ["configuration_id"])
    op.create_table("model_compatibility_stages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("model_compatibility_runs.id"), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "tier", name="uq_model_probe_stage"))
    op.create_index("ix_model_compatibility_stages_run_id", "model_compatibility_stages", ["run_id"])
    for table, column, target in [
        ("active_model_configurations", "checker_configuration_id", "model_configurations.id"),
        ("model_activations", "checker_configuration_id", "model_configurations.id"),
        ("model_activations", "answer_probe_id", "model_compatibility_runs.id"),
        ("model_activations", "checker_probe_id", "model_compatibility_runs.id")]:
        op.add_column(table, sa.Column(column, sa.String(36), nullable=True))
        op.create_foreign_key(f"fk_{table}_{column}", table, target.split(".")[0], [column], ["id"])


def downgrade():
    for table, columns in [("model_activations", ["checker_probe_id", "answer_probe_id", "checker_configuration_id"]), ("active_model_configurations", ["checker_configuration_id"])]:
        for column in columns:
            op.drop_constraint(f"fk_{table}_{column}", table, type_="foreignkey")
            op.drop_column(table, column)
    op.drop_table("model_compatibility_stages")
    op.drop_table("model_compatibility_runs")
