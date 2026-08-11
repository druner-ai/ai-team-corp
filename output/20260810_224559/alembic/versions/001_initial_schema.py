"""initial schema

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
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('short_id', sa.String(length=7), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('click_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_id')
    )
    op.create_index('idx_urls_short_id', 'urls', ['short_id'], unique=True)
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])
    op.create_index('idx_urls_deleted_at', 'urls', ['deleted_at'], postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('idx_urls_deleted_at', table_name='urls')
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_index('idx_urls_short_id', table_name='urls')
    op.drop_table('urls')