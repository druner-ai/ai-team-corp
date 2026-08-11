"""
Test fixtures for URL Shortener tests.

Provides:
- Test database (SQLite in-memory)
- Test Redis (or mock)
- Test HTTP client
- Test service instances
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.main import create_app
from app.models.url import Base
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator
from app.services.url_service import UrlService


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


class MockRedis:
    """
    Mock Redis client for testing.

    Implements basic Redis operations used by CacheService.
    """

    def __init__(self):
        self._data: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._ttls: dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = value
        self._ttls[key] = ttl

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    async def hincrby(self, key: str, field: str, amount: int) -> int:
        if key not in self._hashes:
            self._hashes[key] = {}
        current = int(self._hashes[key].get(field, 0))
        new_value = current + amount
        self._hashes[key][field] = str(new_value)
        return new_value

    async def hset(self, key: str, field: str, value: str) -> None:
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {})

    async def ping(self) -> bool:
        return True

    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline for testing."""

    def __init__(self, redis: MockRedis):
        self.redis = redis
        self._commands: list = []

    def hincrby(self, key: str, field: str, amount: int):
        self._commands.append(("hincrby", key, field, amount))
        return self

    def hset(self, key: str, field: str, value: str):
        self._commands.append(("hset", key, field, value))
        return self

    async def execute(self) -> list:
        results = []
        for cmd in self._commands:
            if cmd[0] == "hincrby":
                result = await self.redis.hincrby(cmd[1], cmd[2], cmd[3])
                results.append(result)
            elif cmd[0] == "hset":
                await self.redis.hset(cmd[1], cmd[2], cmd[3])
                results.append(True)
        return results


@pytest_asyncio.fixture(scope="function")
async def mock_redis():
    """Create a mock Redis client."""
    return MockRedis()


@pytest_asyncio.fixture(scope="function")
def url_repository(test_session):
    """Create a URL repository for testing."""
    return UrlRepository(test_session)


@pytest_asyncio.fixture(scope="function")
def cache_service(mock_redis):
    """Create a cache service with mock Redis."""
    return CacheService(mock_redis)


@pytest_asyncio.fixture(scope="function")
def code_generator():
    """Create a code generator for testing."""
    return CodeGenerator(code_length=6)


@pytest_asyncio.fixture(scope="function")
def url_service(url_repository, cache_service, code_generator):
    """Create a URL service for testing."""
    return UrlService(
        repository=url_repository,
        cache_service=cache_service,
        code_generator=code_generator,
    )


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session, mock_redis):
    """Create a test FastAPI application."""
    app = create_app()

    # Override dependencies
    async def override_get_db():
        yield test_session

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    return app


@pytest_asyncio.fixture(scope="function")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client