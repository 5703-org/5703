"""Transactional invalidation for validated release and lexical caches."""

from alembic import op
import sqlalchemy as sa

revision = "f2c86e9f345d"
down_revision = "f1b75d8e234c"
branch_labels = None
depends_on = None

TABLES = (
    "documents", "document_versions", "processing_runs", "source_units",
    "chunks", "corpus_releases", "release_chunks", "active_corpus", "configurations",
)


def upgrade():
    op.create_table(
        "retrieval_epochs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(36), nullable=False),
    )
    op.execute("INSERT INTO retrieval_epochs(id, token) VALUES (1, gen_random_uuid()::text)")
    op.execute("""
        CREATE FUNCTION cs30_invalidate_retrieval() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          UPDATE retrieval_epochs SET token = gen_random_uuid()::text WHERE id = 1;
          RETURN NULL;
        END $$
    """)
    for table in TABLES:
        op.execute(f"""CREATE TRIGGER cs30_retrieval_epoch
            AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION cs30_invalidate_retrieval()""")


def downgrade():
    for table in TABLES:
        op.execute(f"DROP TRIGGER cs30_retrieval_epoch ON {table}")
    op.execute("DROP FUNCTION cs30_invalidate_retrieval()")
    op.drop_table("retrieval_epochs")
