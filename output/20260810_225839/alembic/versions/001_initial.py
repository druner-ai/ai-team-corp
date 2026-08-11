"""Initial migration: create urls table

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column('short_code', sa.String(length=6), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column('click_count', sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column('last_clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_code', name='idx_urls_short_code'),
    )
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])
    op.create_index('idx_urls_expires_at', 'urls', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))

def downgrade() -> None:
    op.drop_index('idx_urls_expires_at', table_name='urls')
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_table('urls')