"""
Pytest fixtures for URL Shortener tests.
Provides test client, database session, and mocked Redis.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import create_app
from app.models.url_mapping import Base
from app.db.session import get_db_session
from app.db.redis_client import get_redis_client
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.services.url_service import UrlService
from app.dependencies import (
    get_cache_service,
    get_stats_service,
    get_url_service,
)


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create test database engine.
    Uses SQLite for fast, isolated tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis():
    """
    Create a mocked Redis client for testing.
    """
    redis_mock = AsyncMock(spec=redis.Redis)
    
    # Setup common Redis mock behaviors
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = None
    redis_mock.delete.return_value = None
    redis_mock.incr.return_value = 1
    redis_mock.ping.return_value = True
    
    # Mock pipeline
    pipeline_mock = AsyncMock()
    pipeline_mock.execute.return_value = [1, 60]
    redis_mock.pipeline.return_value = pipeline_mock
    
    return redis_mock


@pytest.fixture
def cache_service(mock_redis):
    """
    Create CacheService with mocked Redis.
    """
    return CacheService(mock_redis, ttl=3600)


@pytest.fixture
def stats_service(cache_service):
    """
    Create StatsService with mocked cache.
    """
    return StatsService(cache_service, sync_threshold=10)


@pytest.fixture
def url_service(cache_service, stats_service):
    """
    Create UrlService with mocked dependencies.
    """
    return UrlService(cache_service, stats_service, short_id_length=7)


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session, mock_redis, url_service):
    """
    Create test FastAPI application with overridden dependencies.
    """
    app = create_app()
    
    # Override dependencies for testing
    async def override_get_db_session():
        yield test_session
    
    async def override_get_redis_client():
        return mock_redis
    
    async def override_get_cache_service():
        return url_service.cache_service
    
    async def override_get_stats_service():
        return url_service.stats_service
    
    async def override_get_url_service():
        return url_service
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_stats_service] = override_get_stats_service
    app.dependency_overrides[get_url_service] = override_get_url_service
    
    return app


@pytest_asyncio.fixture(scope="function")
async def client(test_app):
    """
    Create async HTTP test client.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac