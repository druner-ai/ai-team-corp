"""
Fixtures for testing: test client, test database, test Redis.
"""
import asyncio
import os
from typing import AsyncIterator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from redis.asyncio import Redis

from app.main import create_app
from app.models.url import Base
from app.dependencies import get_db, get_redis_client

# Override settings for testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"  # high to avoid interference in tests

from app.config import settings  # noqa: E402

# We'll use SQLite for database testing (requires aiosqlite)
# Install aiosqlite: pip install aiosqlite
# It's not in requirements.txt, but for tests we'll need it.
# We'll add a note in the README or we can include it in dev requirements.
# In the test file we'll assume it's installed.

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    # Delete file after tests
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """Provide a transactional session for each test."""
    async with test_engine.connect() as conn:
        # Begin a transaction
        async with conn.begin():
            # Create a session bound to this connection
            session_maker = async_sessionmaker(conn, class_=AsyncSession, expire_on_commit=False)
            async with session_maker() as session:
                yield session
            # Rollback after test


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    """Provide a Redis client for tests."""
    r = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await r.flushdb()  # clean test db
    yield r
    await r.flushdb()
    await r.close()


@pytest_asyncio.fixture
async def app(test_engine, redis_client) -> AsyncIterator[AsyncClient]:
    """Create a test FastAPI app with overridden dependencies."""
    app = create_app()
    # Override dependencies to use test DB and Redis
    async def override_get_db():
        async with async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client