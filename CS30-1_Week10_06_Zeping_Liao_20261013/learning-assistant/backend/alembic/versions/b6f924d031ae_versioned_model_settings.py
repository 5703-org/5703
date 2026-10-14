"""Encrypted model credentials, immutable versions, probes and active pointers.

Revision ID: b6f924d031ae
Revises: 79f9729b3eae
"""

from alembic import op
import sqlalchemy as sa

revision = "b6f924d031ae"
down_revision = "79f9729b3eae"
branch_labels = None
depends_on = None


def identifier(name="id", foreign=None, **kwargs):
    constraints = [sa.ForeignKey(foreign)] if foreign else []
    return sa.Column(name, sa.String(36), *constraints, **kwargs)


def created_at():
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)


def upgrade():
    op.create_table("model_credentials", identifier(primary_key=True), identifier("workspace_id", "workspaces.id", nullable=False), sa.Column("ciphertext", sa.Text(), nullable=False), created_at())
    op.create_index("ix_model_credentials_workspace_id", "model_credentials", ["workspace_id"])
    op.create_table("model_configurations", identifier(primary_key=True), identifier("workspace_id", "workspaces.id", nullable=False), identifier("group_id", nullable=False), sa.Column("revision", sa.Integer(), nullable=False), identifier("previous_id", "model_configurations.id"), sa.Column("name", sa.String(120), nullable=False), sa.Column("preset", sa.String(60), nullable=False), sa.Column("public_config", sa.JSON(), nullable=False), sa.Column("config_hash", sa.String(64), nullable=False), identifier("credential_id", "model_credentials.id"), identifier("created_by", "users.id", nullable=False), created_at(), sa.UniqueConstraint("group_id", "revision", name="uq_model_config_group_revision"))
    op.create_index("ix_model_configurations_workspace_id", "model_configurations", ["workspace_id"])
    op.create_index("ix_model_configurations_group_id", "model_configurations", ["group_id"])
    op.create_table("model_connection_tests", identifier(primary_key=True), identifier("configuration_id", "model_configurations.id", nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("diagnostic_code", sa.String(60), nullable=False), sa.Column("message", sa.String(500), nullable=False), sa.Column("latency_ms", sa.Integer(), nullable=False), sa.Column("usage", sa.JSON(), nullable=False), identifier("tested_by", "users.id", nullable=False), created_at())
    op.create_index("ix_model_connection_tests_configuration_id", "model_connection_tests", ["configuration_id"])
    op.create_table("active_model_configurations", identifier("workspace_id", "workspaces.id", primary_key=True), identifier("configuration_id", "model_configurations.id"), sa.Column("version", sa.Integer(), nullable=False))
    op.create_table("model_activations", identifier(primary_key=True), identifier("workspace_id", "workspaces.id", nullable=False), identifier("previous_id", "model_configurations.id"), identifier("configuration_id", "model_configurations.id"), identifier("test_id", "model_connection_tests.id"), sa.Column("active_version", sa.Integer(), nullable=False), identifier("activated_by", "users.id", nullable=False), created_at())
    op.create_index("ix_model_activations_workspace_id", "model_activations", ["workspace_id"])


def downgrade():
    for table in ("model_activations", "active_model_configurations", "model_connection_tests", "model_configurations", "model_credentials"):
        op.drop_table(table)
