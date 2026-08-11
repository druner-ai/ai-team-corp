"""
SQLAlchemy ORM model for the Task entity.

Defines the tasks table schema with all columns and constraints
as specified in the architecture document.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Task(Base):
    """
    Task entity representing a single TODO item.

    Attributes:
        id: Auto-incrementing primary key.
        title: Task description (1-500 characters).
        completed: Whether the task is done (default False).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Index for efficient ordering by creation time (newest first)
    __table_args__ = (
        Index("idx_tasks_created_at", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title[:30]}...', completed={self.completed})>"