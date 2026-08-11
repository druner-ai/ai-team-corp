"""
Initial migration: Create url_mappings table.

Revision ID: 001
Revises: None
Create Date: 2025-01-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create url_mappings table with all required columns and indexes.
    """
    op.create_table(
        "url_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("short_id", sa.String(7), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("click_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_id"),
    )
    
    # Create indexes
    op.create_index("idx_url_mappings_short_id", "url_mappings", ["short_id"], unique=True)
    op.create_index("idx_url_mappings_created_at", "url_mappings", ["created_at"])


def downgrade() -> None:
    """
    Drop url_mappings table and indexes.
    """
    op.drop_index("idx_url_mappings_created_at", table_name="url_mappings")
    op.drop_index("idx_url_mappings_short_id", table_name="url_mappings")
    op.drop_table("url_mappings")