"""
SQLAlchemy model for the url shortening service.

Represents a single shortened URL mapping.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Url(Base):
    """
    URL entity: stores original URL, short ID, click statistics, and soft-delete flag.
    """
    __tablename__ = "urls"
    __table_args__ = (
        UniqueConstraint("short_id", name="uq_short_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_id = Column(String(7), nullable=False, unique=True, index=True)
    original_url = Column(Text, nullable=False)
    click_count = Column(BigInteger, nullable=False, default=0, server_default="0")
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default="NOW()")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def is_deleted(self) -> bool:
        """Check if the URL has been soft-deleted."""
        return self.deleted_at is not None