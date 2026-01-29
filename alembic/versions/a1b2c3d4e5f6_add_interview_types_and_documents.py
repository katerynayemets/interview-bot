"""add interview types, documents, phases, stats, feedback

Revision ID: a1b2c3d4e5f6
Revises: ed3b44ec1d0a
Create Date: 2026-01-29

Changes:
- Add interview_type and difficulty to user_settings
- Add interview_type, difficulty, vacancy_summary, cv_summary to sessions
- Create session_documents table for long texts
- Create interview_phases table for structured interview flow
- Add LLM tracking fields to messages
- Create session_stats table for token/cost tracking
- Create interview_feedback table for scoring
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ed3b44ec1d0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === user_settings: add interview_type and difficulty ===
    op.add_column('user_settings', sa.Column(
        'interview_type', sa.String(length=32),
        server_default=sa.text("'mixed'"), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'difficulty', sa.String(length=16),
        server_default=sa.text("'middle'"), nullable=False
    ))

    # === sessions: add interview_type, difficulty, summaries ===
    op.add_column('sessions', sa.Column(
        'interview_type', sa.String(length=32),
        server_default=sa.text("'mixed'"), nullable=False
    ))
    op.add_column('sessions', sa.Column(
        'difficulty', sa.String(length=16),
        server_default=sa.text("'middle'"), nullable=False
    ))
    op.add_column('sessions', sa.Column(
        'vacancy_summary', sa.String(length=512), nullable=True
    ))
    op.add_column('sessions', sa.Column(
        'cv_summary', sa.String(length=512), nullable=True
    ))

    # === session_documents: new table for long texts ===
    op.create_table(
        'session_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('doc_type', sa.String(length=16), nullable=False),  # cv|vacancy
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('processed_text', sa.Text(), nullable=True),
        sa.Column('token_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    )

    # === interview_phases: new table for structured flow ===
    op.create_table(
        'interview_phases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=False, index=True),
        sa.Column('phase_type', sa.String(length=32), nullable=False),
        sa.Column('phase_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('phase_config', sa.JSON(), nullable=True),
    )

    # === messages: add LLM tracking fields ===
    op.add_column('messages', sa.Column(
        'phase_id', sa.Integer(), sa.ForeignKey('interview_phases.id'), nullable=True
    ))
    op.add_column('messages', sa.Column(
        'model_used', sa.String(length=64), nullable=True
    ))
    op.add_column('messages', sa.Column(
        'tokens_input', sa.Integer(), server_default=sa.text('0'), nullable=False
    ))
    op.add_column('messages', sa.Column(
        'tokens_output', sa.Integer(), server_default=sa.text('0'), nullable=False
    ))
    op.add_column('messages', sa.Column(
        'latency_ms', sa.Integer(), server_default=sa.text('0'), nullable=False
    ))
    op.create_index('ix_messages_phase_id', 'messages', ['phase_id'])

    # === session_stats: new table for aggregated stats ===
    op.create_table(
        'session_stats',
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), primary_key=True),
        sa.Column('total_tokens_input', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_tokens_output', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('total_messages', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('interview_duration_sec', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # === interview_feedback: new table for scoring ===
    op.create_table(
        'interview_feedback',
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        # LLM scores (1-10)
        sa.Column('technical_score', sa.Integer(), nullable=True),
        sa.Column('communication_score', sa.Integer(), nullable=True),
        sa.Column('problem_solving_score', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        # Detailed feedback
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('improvements', sa.JSON(), nullable=True),
        sa.Column('detailed_feedback', sa.Text(), nullable=True),
        sa.Column('recommended_topics', sa.JSON(), nullable=True),
        # User feedback
        sa.Column('user_rating', sa.Integer(), nullable=True),  # 1-5 stars
        sa.Column('user_comment', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_table('interview_feedback')
    op.drop_table('session_stats')

    # Drop messages LLM columns
    op.drop_index('ix_messages_phase_id', table_name='messages')
    op.drop_column('messages', 'latency_ms')
    op.drop_column('messages', 'tokens_output')
    op.drop_column('messages', 'tokens_input')
    op.drop_column('messages', 'model_used')
    op.drop_column('messages', 'phase_id')

    # Drop new tables (order matters for FK)
    op.drop_table('interview_phases')
    op.drop_table('session_documents')

    # Drop sessions columns
    op.drop_column('sessions', 'cv_summary')
    op.drop_column('sessions', 'vacancy_summary')
    op.drop_column('sessions', 'difficulty')
    op.drop_column('sessions', 'interview_type')

    # Drop user_settings columns
    op.drop_column('user_settings', 'difficulty')
    op.drop_column('user_settings', 'interview_type')
