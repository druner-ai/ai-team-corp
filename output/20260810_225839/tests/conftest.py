"""
Global test fixtures for the URL shortener application.
We use a separate test database and (optionally) in-memory Redis.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_async_session
from app.redis_client import get_redis_client
from app.main import app
from app.config import settings
from app.middleware.rate_limiter import limiter
from slowapi.storage import MemoryStorage


# Override the database URL for testing (use a test database)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_urlshortener"

# Override Redis URL in settings? We'll mock with fakeredis.
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an async engine connected to a test database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create test database tables and drop before each session? We'll do per-function reset.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Provide a transactional session for a test function."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        # No need to rollback; we recreate tables per function via fixture override


@pytest_asyncio.fixture
async def redis_client():
    """Provide a fakeredis async client (similar to aioredis)."""
    import fakeredis.aioredis
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()

# Override FastAPI dependencies for testing
@pytest.fixture
def override_dependencies(db_session, redis_client):
    """Override DB session and Redis client with test versions."""
    async def override_get_db():
        yield db_session
    async def override_get_redis():
        yield redis_client
    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    yield
    app.dependency_overrides.clear()


# Override rate limiter to use in-memory storage for fast tests
@pytest.fixture(autouse=True)
def setup_rate_limiter(override_dependencies):
    """Patch limiter storage to MemoryStorage."""
    old_storage = limiter.storage
    limiter.storage = MemoryStorage()
    yield
    limiter.storage = old_storage


@pytest_asyncio.fixture
async def client(override_dependencies):
    """Async HTTP client for testing FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac