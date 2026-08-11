"""
Async SQLAlchemy engine and session management.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings

# Create async engine with connection pooling
# pool_size=20, max_overflow=10 as per architecture document
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: SQLAlchemy async session.

    Note:
        Session is automatically closed when the request is complete.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()