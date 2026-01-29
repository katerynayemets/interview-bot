"""repair missing columns and tables after stamped migrations

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-29

This migration repairs the database after migrations a1b2c3d4e5f6 and
b2c3d4e5f6a7 were stamped (marked as applied) without actually running.
Some tables were created by Base.metadata.create_all, but ALTER TABLE
operations (adding columns to existing tables) were never executed.
Uses IF NOT EXISTS / IF EXISTS to be idempotent.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================================================
    # FROM migration a1b2c3d4e5f6 (interview types & docs)
    # =====================================================

    # --- user_settings: interview_type, difficulty ---
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS interview_type VARCHAR(32) NOT NULL DEFAULT 'mixed'
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS difficulty VARCHAR(16) NOT NULL DEFAULT 'middle'
    """)

    # --- sessions: interview_type, difficulty, summaries ---
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS interview_type VARCHAR(32) NOT NULL DEFAULT 'mixed'
    """)
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS difficulty VARCHAR(16) NOT NULL DEFAULT 'middle'
    """)
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS vacancy_summary VARCHAR(512)
    """)
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS cv_summary VARCHAR(512)
    """)

    # --- session_documents table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS session_documents (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            doc_type VARCHAR(16) NOT NULL,
            source_url VARCHAR(512),
            raw_text TEXT,
            processed_text TEXT,
            token_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_session_documents_session_id
        ON session_documents(session_id)
    """)

    # --- interview_phases table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS interview_phases (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            phase_type VARCHAR(32) NOT NULL,
            phase_order INTEGER NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            phase_config JSON
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_interview_phases_session_id
        ON interview_phases(session_id)
    """)

    # --- messages: LLM tracking fields ---
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS phase_id INTEGER REFERENCES interview_phases(id)
    """)
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS model_used VARCHAR(64)
    """)
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS tokens_input INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS tokens_output INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS latency_ms INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_messages_phase_id
        ON messages(phase_id)
    """)

    # --- session_stats table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS session_stats (
            session_id INTEGER PRIMARY KEY REFERENCES sessions(id),
            total_tokens_input INTEGER NOT NULL DEFAULT 0,
            total_tokens_output INTEGER NOT NULL DEFAULT 0,
            total_messages INTEGER NOT NULL DEFAULT 0,
            estimated_cost_usd FLOAT NOT NULL DEFAULT 0.0,
            interview_duration_sec INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)

    # --- interview_feedback table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS interview_feedback (
            session_id INTEGER PRIMARY KEY REFERENCES sessions(id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            technical_score INTEGER,
            communication_score INTEGER,
            problem_solving_score INTEGER,
            overall_score INTEGER,
            strengths JSON,
            improvements JSON,
            detailed_feedback TEXT,
            recommended_topics JSON,
            user_rating INTEGER,
            user_comment TEXT
        )
    """)

    # =====================================================
    # FROM migration b2c3d4e5f6a7 (logging & billing)
    # =====================================================

    # --- user_settings: profile fields ---
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS username VARCHAR(64)
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS first_name VARCHAR(64)
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS last_name VARCHAR(64)
    """)

    # --- user_settings: billing fields ---
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(16) NOT NULL DEFAULT 'free'
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS balance_usd FLOAT NOT NULL DEFAULT 0.0
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS free_interviews_left INTEGER NOT NULL DEFAULT 3
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS total_interviews INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS total_tokens_used INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS total_spent_usd FLOAT NOT NULL DEFAULT 0.0
    """)

    # --- user_settings: status flags ---
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN NOT NULL DEFAULT false
    """)
    op.execute("""
        ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false
    """)

    # --- user_activities table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_activities (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL REFERENCES user_settings(chat_id),
            session_id INTEGER REFERENCES sessions(id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            action VARCHAR(64) NOT NULL,
            action_type VARCHAR(32) NOT NULL DEFAULT 'user',
            details JSON,
            message_text TEXT,
            duration_ms INTEGER,
            tokens_used INTEGER,
            ip_address VARCHAR(45),
            user_agent VARCHAR(256)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_chat_id ON user_activities(chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_session_id ON user_activities(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_created_at ON user_activities(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_activities_action ON user_activities(action)")

    # --- error_logs table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            chat_id BIGINT,
            session_id INTEGER,
            error_type VARCHAR(128) NOT NULL,
            error_message TEXT NOT NULL,
            error_traceback TEXT,
            module VARCHAR(128),
            function VARCHAR(128),
            is_resolved BOOLEAN NOT NULL DEFAULT false,
            resolved_at TIMESTAMP,
            resolved_by VARCHAR(64),
            resolution_notes TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_created_at ON error_logs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_chat_id ON error_logs(chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_session_id ON error_logs(session_id)")

    # --- billing_plans table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_plans (
            id SERIAL PRIMARY KEY,
            name VARCHAR(32) UNIQUE NOT NULL,
            display_name VARCHAR(64) NOT NULL,
            interviews_per_month INTEGER NOT NULL DEFAULT 3,
            max_tokens_per_interview INTEGER NOT NULL DEFAULT 4000,
            price_per_month_usd FLOAT NOT NULL DEFAULT 0.0,
            price_per_interview_usd FLOAT NOT NULL DEFAULT 0.0,
            price_per_1k_tokens_usd FLOAT NOT NULL DEFAULT 0.0,
            features JSON,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)

    # Insert default plans only if table is empty (include all NOT NULL columns)
    op.execute("""
        INSERT INTO billing_plans (name, display_name, interviews_per_month, max_tokens_per_interview, price_per_month_usd, price_per_interview_usd, price_per_1k_tokens_usd, features, is_active, created_at)
        SELECT 'free', 'Free', 3, 4000, 0, 0, 0, '{"detailed_feedback": false, "priority_support": false}', true, now()
        WHERE NOT EXISTS (SELECT 1 FROM billing_plans WHERE name = 'free')
    """)
    op.execute("""
        INSERT INTO billing_plans (name, display_name, interviews_per_month, max_tokens_per_interview, price_per_month_usd, price_per_interview_usd, price_per_1k_tokens_usd, features, is_active, created_at)
        SELECT 'pro', 'Pro', 20, 4000, 9.99, 0.5, 0.001, '{"detailed_feedback": true, "priority_support": false}', true, now()
        WHERE NOT EXISTS (SELECT 1 FROM billing_plans WHERE name = 'pro')
    """)
    op.execute("""
        INSERT INTO billing_plans (name, display_name, interviews_per_month, max_tokens_per_interview, price_per_month_usd, price_per_interview_usd, price_per_1k_tokens_usd, features, is_active, created_at)
        SELECT 'premium', 'Premium', 0, 4000, 29.99, 0, 0.0005, '{"detailed_feedback": true, "priority_support": true}', true, now()
        WHERE NOT EXISTS (SELECT 1 FROM billing_plans WHERE name = 'premium')
    """)

    # --- transactions table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL REFERENCES user_settings(chat_id),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            tx_type VARCHAR(32) NOT NULL,
            amount_usd FLOAT NOT NULL,
            session_id INTEGER REFERENCES sessions(id),
            description VARCHAR(256),
            tokens_charged INTEGER,
            payment_provider VARCHAR(32),
            external_id VARCHAR(128),
            status VARCHAR(16) NOT NULL DEFAULT 'completed',
            balance_after FLOAT NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_chat_id ON transactions(chat_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_created_at ON transactions(created_at)")

    # --- promo_codes table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(32) UNIQUE NOT NULL,
            promo_type VARCHAR(32) NOT NULL,
            value FLOAT NOT NULL,
            max_uses INTEGER,
            used_count INTEGER NOT NULL DEFAULT 0,
            max_uses_per_user INTEGER NOT NULL DEFAULT 1,
            valid_from TIMESTAMP NOT NULL DEFAULT now(),
            valid_until TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_codes_code ON promo_codes(code)")

    # Insert welcome promo only if not exists (include all NOT NULL columns)
    op.execute("""
        INSERT INTO promo_codes (code, promo_type, value, max_uses, used_count, max_uses_per_user, valid_from, is_active, created_at)
        SELECT 'WELCOME2024', 'free_interviews', 2, NULL, 0, 1, now(), true, now()
        WHERE NOT EXISTS (SELECT 1 FROM promo_codes WHERE code = 'WELCOME2024')
    """)

    # --- promo_code_usages table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS promo_code_usages (
            id SERIAL PRIMARY KEY,
            promo_code_id INTEGER NOT NULL REFERENCES promo_codes(id),
            chat_id BIGINT NOT NULL REFERENCES user_settings(chat_id),
            used_at TIMESTAMP NOT NULL DEFAULT now(),
            benefit_type VARCHAR(32) NOT NULL,
            benefit_value FLOAT NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_code_usages_promo_code_id ON promo_code_usages(promo_code_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_code_usages_chat_id ON promo_code_usages(chat_id)")


def downgrade() -> None:
    # This is a repair migration - downgrade is not meaningful
    pass
