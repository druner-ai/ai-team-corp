"""
Database initialization and session management.

Creates the async SQLAlchemy engine, session factory, and provides
a FastAPI dependency for obtaining database sessions.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine with SQLite-specific configuration
# StaticPool ensures a single connection is reused (required for SQLite with WAL mode)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Yields an AsyncSession and ensures it is closed after the request completes.

    Yields:
        AsyncSession: SQLAlchemy async session for database operations.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database: enable WAL mode and create all tables.

    Should be called once at application startup.
    WAL mode allows concurrent reads without blocking writers.
    """
    async with engine.begin() as conn:
        # Enable WAL mode for better concurrent read performance
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        # Enable foreign keys (good practice, though not strictly needed here)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")

    # Create all tables defined in models
    from app.models.task import Base  # noqa: F401 - imported for table registration

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully with WAL mode enabled.")