"""
Database session management with SQLAlchemy async engine.
Provides connection pooling and session factory.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.config import settings


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.
    
    Args:
        database_url: Optional database URL. Uses settings.DATABASE_URL if not provided.
        
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
        
    Note:
        Pool size is set to 10 with max overflow of 20 as per architecture requirements.
        For testing, NullPool can be used to avoid connection pooling issues.
    """
    url = database_url or settings.DATABASE_URL
    
    engine = create_async_engine(
        url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
    return engine


# Global engine instance
engine = create_engine()

# Session factory for creating async sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Yields:
        AsyncSession: Database session that is automatically closed after use.
        
    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """
    Close the database engine and release all connections.
    Called during application shutdown.
    """
    await engine.dispose()