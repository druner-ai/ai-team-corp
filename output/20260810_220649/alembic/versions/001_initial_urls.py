"""initial urls table

Revision ID: 001
Revises:
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('short_id', sa.String(7), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('click_count', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_accessed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_unique_index('idx_urls_short_id', 'urls', ['short_id'])
    op.create_index('idx_urls_active', 'urls', ['short_id'], postgresql_where=sa.text('is_active = TRUE'))


def downgrade() -> None:
    op.drop_index('idx_urls_active', table_name='urls')
    op.drop_index('idx_urls_short_id', table_name='urls')
    op.drop_table('urls')