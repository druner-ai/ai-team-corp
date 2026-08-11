"""initial

Revision ID: 001
Revises:
Create Date: 2025-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'url_mapping',
        sa.Column('id', sa.String(7), primary_key=True),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('click_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    )
    op.create_index('idx_original_url', 'url_mapping', ['original_url'])
    op.create_index('idx_expires_at', 'url_mapping', ['expires_at'], postgresql_where=sa.text('is_deleted = FALSE'))

def downgrade():
    op.drop_index('idx_expires_at')
    op.drop_index('idx_original_url')
    op.drop_table('url_mapping')