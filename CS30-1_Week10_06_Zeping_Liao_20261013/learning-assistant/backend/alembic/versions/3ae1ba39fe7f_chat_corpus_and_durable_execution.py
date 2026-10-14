"""chat corpus and durable execution

Revision ID: 3ae1ba39fe7f
Revises: 0001_initial
Create Date: 2026-09-08 16:32:46.260563
"""
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision = '3ae1ba39fe7f'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('configurations',
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('values', sa.JSON(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('content_hash')
    )
    op.create_table('corpus_releases',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('state', sa.String(length=40), nullable=False),
    sa.Column('configuration', sa.JSON(), nullable=False),
    sa.Column('manifest', sa.JSON(), nullable=False),
    sa.Column('error', sa.JSON(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('active_corpus',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('release_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['release_id'], ['corpus_releases.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('documents',
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('edition', sa.String(length=200), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=False),
    sa.Column('license', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('document_versions',
    sa.Column('document_id', sa.String(length=36), nullable=False),
    sa.Column('raw_hash', sa.String(length=64), nullable=False),
    sa.Column('media_type', sa.String(length=80), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.Text(), nullable=False),
    sa.Column('original_filename', sa.String(length=250), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('raw_hash')
    )
    op.create_index(op.f('ix_document_versions_document_id'), 'document_versions', ['document_id'], unique=False)
    op.create_table('messages',
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('active_answer_id', sa.String(length=36), nullable=True),
    sa.Column('request_id', sa.String(length=36), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("role in ('user','assistant')"),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'sequence')
    )
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)
    op.create_table('session_summaries',
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('covered_until_sequence', sa.Integer(), nullable=False),
    sa.Column('source_message_ids', sa.JSON(), nullable=False),
    sa.Column('summary_text', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('token_count', sa.Integer(), nullable=False),
    sa.Column('method', sa.String(length=80), nullable=False),
    sa.Column('invalidated', sa.Boolean(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_summaries_session_id'), 'session_summaries', ['session_id'], unique=False)
    op.create_table('snapshots',
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=True),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_snapshots_owner_id'), 'snapshots', ['owner_id'], unique=False)
    op.create_table('answer_requests',
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('route', sa.String(length=250), nullable=False),
    sa.Column('idempotency_key', sa.String(length=128), nullable=False),
    sa.Column('body_hash', sa.String(length=64), nullable=False),
    sa.Column('mode', sa.String(length=30), nullable=False),
    sa.Column('response_schema', sa.String(length=40), nullable=False),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=True),
    sa.Column('user_message_id', sa.String(length=36), nullable=True),
    sa.Column('assistant_message_id', sa.String(length=36), nullable=True),
    sa.Column('context_snapshot_id', sa.String(length=36), nullable=True),
    sa.Column('profile_snapshot_id', sa.String(length=36), nullable=True),
    sa.Column('release_id', sa.String(length=36), nullable=True),
    sa.Column('config_id', sa.String(length=36), nullable=True),
    sa.Column('regeneration_of', sa.String(length=36), nullable=True),
    sa.Column('run_id', sa.String(length=36), nullable=True),
    sa.Column('item_id', sa.String(length=160), nullable=True),
    sa.Column('command', sa.JSON(), nullable=False),
    sa.Column('budget', sa.JSON(), nullable=False),
    sa.Column('trace', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['assistant_message_id'], ['messages.id'], ),
    sa.ForeignKeyConstraint(['config_id'], ['configurations.id'], ),
    sa.ForeignKeyConstraint(['context_snapshot_id'], ['snapshots.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['profile_snapshot_id'], ['snapshots.id'], ),
    sa.ForeignKeyConstraint(['release_id'], ['corpus_releases.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.ForeignKeyConstraint(['user_message_id'], ['messages.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('owner_id', 'route', 'idempotency_key')
    )
    op.create_index(op.f('ix_answer_requests_owner_id'), 'answer_requests', ['owner_id'], unique=False)
    op.create_index(op.f('ix_answer_requests_session_id'), 'answer_requests', ['session_id'], unique=False)
    op.create_table('processing_runs',
    sa.Column('document_version_id', sa.String(length=36), nullable=False),
    sa.Column('config_hash', sa.String(length=64), nullable=False),
    sa.Column('configuration', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(length=40), nullable=False),
    sa.Column('counts', sa.JSON(), nullable=False),
    sa.Column('error', sa.JSON(), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['document_version_id'], ['document_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_version_id', 'config_hash')
    )
    op.create_table('chunks',
    sa.Column('processing_id', sa.String(length=36), nullable=False),
    sa.Column('document_id', sa.String(length=36), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('text_hash', sa.String(length=64), nullable=False),
    sa.Column('section', sa.String(length=500), nullable=False),
    sa.Column('pages', sa.JSON(), nullable=False),
    sa.Column('spans', sa.JSON(), nullable=False),
    sa.Column('tokens', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['processing_id'], ['processing_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunks_processing_id'), 'chunks', ['processing_id'], unique=False)
    op.create_table('jobs',
    sa.Column('request_id', sa.String(length=36), nullable=True),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('kind', sa.String(length=40), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('execution_token', sa.String(length=36), nullable=True),
    sa.Column('worker_id', sa.String(length=80), nullable=True),
    sa.Column('error', sa.JSON(), nullable=True),
    sa.Column('answer_id', sa.String(length=36), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("state in ('queued','running','retry_wait','succeeded','failed','cancelled')"),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['answer_requests.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_request_id'), 'jobs', ['request_id'], unique=False)
    op.create_index(op.f('ix_jobs_state'), 'jobs', ['state'], unique=False)
    op.create_table('source_units',
    sa.Column('processing_id', sa.String(length=36), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=False),
    sa.Column('section', sa.String(length=500), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('cleaned_text', sa.Text(), nullable=False),
    sa.Column('quality', sa.String(length=30), nullable=False),
    sa.Column('issues', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['processing_id'], ['processing_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_source_units_processing_id'), 'source_units', ['processing_id'], unique=False)
    op.create_table('answers',
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('job_id', sa.String(length=36), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=True),
    sa.Column('response_schema', sa.String(length=40), nullable=False),
    sa.Column('response', sa.JSON(), nullable=False),
    sa.Column('model_mode', sa.String(length=20), nullable=False),
    sa.Column('timing', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['answer_requests.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('request_id')
    )
    op.create_table('attempts',
    sa.Column('job_id', sa.String(length=36), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attempts_job_id'), 'attempts', ['job_id'], unique=False)
    op.create_table('release_chunks',
    sa.Column('release_id', sa.String(length=36), nullable=False),
    sa.Column('chunk_id', sa.String(length=36), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR().with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('dimension', sa.Integer(), nullable=False),
    sa.Column('model_revision', sa.String(length=200), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ),
    sa.ForeignKeyConstraint(['release_id'], ['corpus_releases.id'], ),
    sa.PrimaryKeyConstraint('release_id', 'chunk_id')
    )
    op.create_table('evidence_snapshots',
    sa.Column('answer_id', sa.String(length=36), nullable=False),
    sa.Column('evidence_id', sa.String(length=40), nullable=False),
    sa.Column('document_id', sa.String(length=36), nullable=False),
    sa.Column('chunk_id', sa.String(length=80), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['answer_id'], ['answers.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('answer_id', 'evidence_id')
    )
    op.create_index(op.f('ix_evidence_snapshots_answer_id'), 'evidence_snapshots', ['answer_id'], unique=False)
    op.create_table('feedback',
    sa.Column('answer_id', sa.String(length=36), nullable=False),
    sa.Column('owner_id', sa.String(length=36), nullable=False),
    sa.Column('helpful', sa.Boolean(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('review_state', sa.String(length=30), nullable=False),
    sa.Column('review_note', sa.Text(), nullable=False),
    sa.Column('issue', sa.String(length=500), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['answer_id'], ['answers.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('answer_id', 'owner_id')
    )
    op.create_table('citations',
    sa.Column('answer_id', sa.String(length=36), nullable=False),
    sa.Column('evidence_id', sa.String(length=36), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['answer_id'], ['answers.id'], ),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidence_snapshots.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('answer_id', 'evidence_id')
    )
    op.add_column('users', sa.Column('token_version', sa.Integer(), server_default='1', nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'token_version')
    op.drop_table('citations')
    op.drop_table('feedback')
    op.drop_index(op.f('ix_evidence_snapshots_answer_id'), table_name='evidence_snapshots')
    op.drop_table('evidence_snapshots')
    op.drop_table('release_chunks')
    op.drop_index(op.f('ix_attempts_job_id'), table_name='attempts')
    op.drop_table('attempts')
    op.drop_table('answers')
    op.drop_index(op.f('ix_source_units_processing_id'), table_name='source_units')
    op.drop_table('source_units')
    op.drop_index(op.f('ix_jobs_state'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_request_id'), table_name='jobs')
    op.drop_table('jobs')
    op.drop_index(op.f('ix_chunks_processing_id'), table_name='chunks')
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_table('chunks')
    op.drop_table('processing_runs')
    op.drop_index(op.f('ix_answer_requests_session_id'), table_name='answer_requests')
    op.drop_index(op.f('ix_answer_requests_owner_id'), table_name='answer_requests')
    op.drop_table('answer_requests')
    op.drop_index(op.f('ix_snapshots_owner_id'), table_name='snapshots')
    op.drop_table('snapshots')
    op.drop_index(op.f('ix_session_summaries_session_id'), table_name='session_summaries')
    op.drop_table('session_summaries')
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_document_versions_document_id'), table_name='document_versions')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('active_corpus')
    op.drop_table('corpus_releases')
    op.drop_table('configurations')
    # ### end Alembic commands ###
