"""Initial URL table

Revision ID: 001
Revises:
Create Date: 2025-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.String(7), primary_key=True, comment='Short identifier (base62, 7 chars)'),
        sa.Column('original_url', sa.Text(), nullable=False, comment='Original long URL'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('clicks', sa.BigInteger(), nullable=False, server_default=sa.text('0'), comment='Number of redirects'),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Soft-delete flag'),
    )
    # Create indexes
    op.create_index('idx_urls_original_url', 'urls', ['original_url'])
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_index('idx_urls_original_url', table_name='urls')
    op.drop_table('urls')