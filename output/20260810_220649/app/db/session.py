"""
Database session and engine management using SQLAlchemy async.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# SessionLocal is a factory for sessions
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Initialize database engine (run on startup).
    """
    # The engine is created lazily; just verify connectivity
    async with engine.connect() as conn:
        await conn.execute(select(1))


async def close_db() -> None:
    """
    Dispose engine on shutdown.
    """
    await engine.dispose()