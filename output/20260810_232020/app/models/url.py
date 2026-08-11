"""
SQLAlchemy model for the urls table.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Url(Base):
    """
    URL model representing shortened URLs.

    Attributes:
        id: Internal auto-incrementing ID.
        short_code: Unique short code (base62, 6 chars).
        original_url: The original long URL.
        created_at: Timestamp of creation.
        is_deleted: Soft delete flag.
        expires_at: Optional expiration timestamp.
    """

    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Additional indexes as per architecture document
    __table_args__ = (
        Index("idx_urls_short_code", "short_code", unique=True),
        Index("idx_urls_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Url(id={self.id}, short_code='{self.short_code}')>"