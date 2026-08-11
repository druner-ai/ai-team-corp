"""
Pytest fixtures for test database, Redis mock, and async HTTP client.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.redis_client import get_redis
from app.models.url import Base
from unittest.mock import patch

# Use SQLite in-memory for tests (requires aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database schema and provide a session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


# Simple async mock for Redis (used in all tests)
class MockRedis:
    """Simple async mock for Redis used in tests."""

    def __init__(self):
        self.store = {}
        self.expiry = {}

    async def get(self, key):
        if key in self.store and self._is_expired(key) is False:
            return self.store[key]
        return None

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            import time
            self.expiry[key] = time.time() + ex

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiry.pop(key, None)
        return 1

    async def incr(self, key):
        if key not in self.store:
            self.store[key] = 0
        self.store[key] += 1
        return self.store[key]

    async def expire(self, key, ttl):
        import time
        if key in self.store:
            self.expiry[key] = time.time() + ttl

    async def pipeline(self, transaction=True):
        return MockPipeline(self)

    async def ping(self):
        return True

    def _is_expired(self, key):
        import time
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            return True
        return False


class MockPipeline:
    def __init__(self, mock_redis):
        self.mock = mock_redis
        self.commands = []

    def incr(self, key):
        self.commands.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        import time
        for cmd, *args in self.commands:
            if cmd == "incr":
                res = await self.mock.incr(args[0])
                results.append(res)
            elif cmd == "expire":
                await self.mock.expire(args[0], args[1])
                results.append(True)
            else:
                results.append(None)
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_redis():
    return MockRedis()


# Patch Redis client in modules that import it directly using unittest.mock
@pytest.fixture(autouse=True)
def patch_redis_client(mock_redis: MockRedis):
    """Replace Redis client in all modules that use it directly."""
    # Modules to patch
    patchers = [
        patch("app.middleware.rate_limiter.redis_client", mock_redis),
        patch("app.services.url_service.redis_client", mock_redis),
        patch("app.services.delete_service.redis_client", mock_redis),
    ]
    for patcher in patchers:
        patcher.start()
    yield
    for patcher in patchers:
        patcher.stop()


# Override the dependencies to use test DB and mock Redis
@pytest.fixture(autouse=True)
def override_dependencies(db_session: AsyncSession, mock_redis: MockRedis):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client