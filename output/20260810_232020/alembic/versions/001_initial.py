"""
Initial migration: Create urls table.

Revision ID: 001
Revises: None
Create Date: 2025-01-15 10:00:00.000000
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
    """Create the urls table with indexes."""
    op.create_table(
        "urls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("short_code", sa.String(10), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
    )

    # Create indexes
    op.create_index("idx_urls_short_code", "urls", ["short_code"], unique=True)
    op.create_index("idx_urls_created_at", "urls", ["created_at"])


def downgrade() -> None:
    """Drop the urls table and indexes."""
    op.drop_index("idx_urls_created_at", table_name="urls")
    op.drop_index("idx_urls_short_code", table_name="urls")
    op.drop_table("urls")