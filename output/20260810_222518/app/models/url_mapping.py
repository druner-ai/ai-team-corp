"""
SQLAlchemy model for URL mappings.
Represents the url_mappings table in PostgreSQL.
"""
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    Index,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class UrlMapping(Base):
    """
    URL mapping entity storing short ID to original URL mappings.
    
    Attributes:
        id: Internal auto-incrementing ID
        short_id: Unique 7-character short identifier
        original_url: The original long URL
        created_at: Timestamp of creation
        expires_at: Optional expiration timestamp
        is_active: Soft delete flag
        click_count: Total number of redirects
    """
    __tablename__ = "url_mappings"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    short_id = Column(String(7), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    click_count = Column(BigInteger, nullable=False, default=0)
    
    # Additional indexes as per architecture document
    __table_args__ = (
        Index("idx_url_mappings_short_id", "short_id", unique=True),
        Index("idx_url_mappings_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<UrlMapping(short_id='{self.short_id}', is_active={self.is_active})>"