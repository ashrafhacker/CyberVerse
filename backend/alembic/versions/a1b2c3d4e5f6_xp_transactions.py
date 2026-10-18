"""add xp_transactions ledger

Revision ID: a1b2c3d4e5f6
Revises: de5d6b10489e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'de5d6b10489e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'xp_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False, server_default=''),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'source_type', 'source_id', name='uq_xp_tx_source'),
    )
    op.create_index('ix_xp_transactions_user_id', 'xp_transactions', ['user_id'])
    op.create_index('ix_xp_transactions_created_at', 'xp_transactions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_xp_transactions_created_at', table_name='xp_transactions')
    op.drop_index('ix_xp_transactions_user_id', table_name='xp_transactions')
    op.drop_table('xp_transactions')
