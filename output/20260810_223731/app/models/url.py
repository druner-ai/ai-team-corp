"""
SQLAlchemy ORM model for the urls table.
"""
import datetime
from sqlalchemy import String, Text, BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class URLRecord(Base):
    """Represents a shortened URL with analytics."""

    __tablename__ = "urls"

    id: Mapped[str] = mapped_column(String(7), primary_key=True, comment="Short identifier (base62, 7 chars)")
    original_url: Mapped[str] = mapped_column(Text, nullable=False, comment="Original long URL")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    clicks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Number of redirects")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Soft-delete flag")

    def __repr__(self) -> str:
        return f"<URLRecord(id={self.id}, original_url={self.original_url[:30]}...)>"