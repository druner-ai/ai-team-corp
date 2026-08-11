"""
    SQLAlchemy ORM model for url_mapping table.
"""
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, BigInteger, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UrlMapping(Base):
    __tablename__ = "url_mapping"

    id: Mapped[str] = mapped_column(String(7), primary_key=True)
    original_url: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean(), server_default=text("false"), nullable=False)
    click_count: Mapped[int] = mapped_column(BigInteger(), server_default=text("0"), nullable=False)