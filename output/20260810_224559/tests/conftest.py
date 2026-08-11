"""
Pytest fixtures for test database session, Redis mock, and test client.

Uses SQLite with aiosqlite for in-memory testing and fakeredis for Redis.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app
from src.models.url import Base
from src.core.redis_client import redis_client  # will be overridden

# Use SQLite for testing (in-memory, aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    async_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_redis():
    """Override Redis client with fakeredis for testing."""
    from fakeredis.aioredis import FakeRedis
    fake_redis = FakeRedis()
    # Monkey-patch the application's redis_client temporarily
    original = redis_client._redis  # None in test
    app.dependency_overrides[get_redis] = lambda: fake_redis
    # Also we need to replace the rate limit middleware's redis?
    # The middleware is created at startup; we'll override it for tests.
    # For integration tests, we can create a fresh app with our fake redis.
    # Simpler: we yield FakeRedis, and the test client will use it.
    yield fake_redis
    app.dependency_overrides.clear()


# Override the get_redis dependency in tests
async def get_redis_override() -> redis.asyncio.Redis:
    # This is used in the test client via dependency_overrides
    from fakeredis.aioredis import FakeRedis
    return FakeRedis()


@pytest_asyncio.fixture
async def client(async_engine, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """Provide a fastapi test client."""
    # Override get_redis to use fake redis
    app.dependency_overrides[get_redis] = lambda: test_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()