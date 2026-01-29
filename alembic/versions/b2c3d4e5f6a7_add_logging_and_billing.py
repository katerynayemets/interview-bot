"""add logging, billing, and admin features

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-29

Changes:
- Extend user_settings with billing fields (subscription_tier, balance, etc.)
- Add user profile fields (username, first_name, last_name)
- Create user_activities table for admin panel
- Create error_logs table for error tracking
- Create billing_plans table
- Create transactions table
- Create promo_codes and promo_code_usages tables
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === user_settings: add profile and billing fields ===
    op.add_column('user_settings', sa.Column(
        'username', sa.String(64), nullable=True
    ))
    op.add_column('user_settings', sa.Column(
        'first_name', sa.String(64), nullable=True
    ))
    op.add_column('user_settings', sa.Column(
        'last_name', sa.String(64), nullable=True
    ))

    # Billing fields
    op.add_column('user_settings', sa.Column(
        'subscription_tier', sa.String(16), server_default=sa.text("'free'"), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'balance_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'free_interviews_left', sa.Integer(), server_default=sa.text('3'), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'total_interviews', sa.Integer(), server_default=sa.text('0'), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'total_tokens_used', sa.Integer(), server_default=sa.text('0'), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'total_spent_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False
    ))

    # Status flags
    op.add_column('user_settings', sa.Column(
        'is_blocked', sa.Boolean(), server_default=sa.text('false'), nullable=False
    ))
    op.add_column('user_settings', sa.Column(
        'is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False
    ))

    # === user_activities: activity log for admin ===
    op.create_table(
        'user_activities',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('user_settings.chat_id'), nullable=False, index=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
        sa.Column('action', sa.String(64), nullable=False, index=True),
        sa.Column('action_type', sa.String(32), server_default=sa.text("'user'"), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(256), nullable=True),
    )

    # === error_logs: error tracking ===
    op.create_table(
        'error_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
        sa.Column('chat_id', sa.BigInteger(), nullable=True, index=True),
        sa.Column('session_id', sa.Integer(), nullable=True, index=True),
        sa.Column('error_type', sa.String(128), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('module', sa.String(128), nullable=True),
        sa.Column('function', sa.String(128), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(64), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
    )

    # === billing_plans: subscription tiers ===
    op.create_table(
        'billing_plans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(32), unique=True, nullable=False),
        sa.Column('display_name', sa.String(64), nullable=False),
        sa.Column('interviews_per_month', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('max_tokens_per_interview', sa.Integer(), server_default=sa.text('4000'), nullable=False),
        sa.Column('price_per_month_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('price_per_interview_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('price_per_1k_tokens_usd', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Insert default billing plans
    op.execute("""
        INSERT INTO billing_plans (name, display_name, interviews_per_month, price_per_month_usd, price_per_interview_usd, price_per_1k_tokens_usd, features)
        VALUES
            ('free', 'Free', 3, 0, 0, 0, '{"detailed_feedback": false, "priority_support": false}'),
            ('pro', 'Pro', 20, 9.99, 0.5, 0.001, '{"detailed_feedback": true, "priority_support": false}'),
            ('premium', 'Premium', 0, 29.99, 0, 0.0005, '{"detailed_feedback": true, "priority_support": true}')
    """)

    # === transactions: payment records ===
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('user_settings.chat_id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, index=True),
        sa.Column('tx_type', sa.String(32), nullable=False),  # deposit|withdraw|refund|bonus
        sa.Column('amount_usd', sa.Float(), nullable=False),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=True),
        sa.Column('description', sa.String(256), nullable=True),
        sa.Column('tokens_charged', sa.Integer(), nullable=True),
        sa.Column('payment_provider', sa.String(32), nullable=True),
        sa.Column('external_id', sa.String(128), nullable=True),
        sa.Column('status', sa.String(16), server_default=sa.text("'completed'"), nullable=False),
        sa.Column('balance_after', sa.Float(), nullable=False),
    )

    # === promo_codes: discount codes ===
    op.create_table(
        'promo_codes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(32), unique=True, nullable=False, index=True),
        sa.Column('promo_type', sa.String(32), nullable=False),  # bonus_balance|free_interviews|discount_percent
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('max_uses_per_user', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('valid_from', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Insert welcome promo code
    op.execute("""
        INSERT INTO promo_codes (code, promo_type, value, max_uses, max_uses_per_user)
        VALUES ('WELCOME2024', 'free_interviews', 2, NULL, 1)
    """)

    # === promo_code_usages: promo code usage tracking ===
    op.create_table(
        'promo_code_usages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('promo_code_id', sa.Integer(), sa.ForeignKey('promo_codes.id'), nullable=False, index=True),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('user_settings.chat_id'), nullable=False, index=True),
        sa.Column('used_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('benefit_type', sa.String(32), nullable=False),
        sa.Column('benefit_value', sa.Float(), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order (FK dependencies)
    op.drop_table('promo_code_usages')
    op.drop_table('promo_codes')
    op.drop_table('transactions')
    op.drop_table('billing_plans')
    op.drop_table('error_logs')
    op.drop_table('user_activities')

    # Drop user_settings columns
    op.drop_column('user_settings', 'is_admin')
    op.drop_column('user_settings', 'is_blocked')
    op.drop_column('user_settings', 'total_spent_usd')
    op.drop_column('user_settings', 'total_tokens_used')
    op.drop_column('user_settings', 'total_interviews')
    op.drop_column('user_settings', 'free_interviews_left')
    op.drop_column('user_settings', 'balance_usd')
    op.drop_column('user_settings', 'subscription_tier')
    op.drop_column('user_settings', 'last_name')
    op.drop_column('user_settings', 'first_name')
    op.drop_column('user_settings', 'username')
