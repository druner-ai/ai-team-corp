"""
Async SQLAlchemy engine and session setup.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

# Create async engine with connection pooling (recommended for production)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    echo=False,  # set to True for SQL debugging
)

# Session factory bound to the engine
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session.

    Ensures the session is closed after the request.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()