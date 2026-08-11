import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import DatabasePool
from app.cache import TTLCache
from app.dependencies import _db_pool, _cache, _rate_limiter
from app.config import CACHE_TTL
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    if not loop:
        raise RuntimeError("Failed to create event loop")
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db():
    # Setup test database and cache
    test_db = DatabasePool(":memory:", pool_size=1)
    if not test_db:
        raise RuntimeError("Failed to create test database pool")
    await test_db.init_pool()
    test_cache = TTLCache(ttl=CACHE_TTL)
    if not test_cache:
        raise RuntimeError("Failed to create test cache")
    # Override module-level dependencies
    _db_pool = test_db
    _cache = test_cache
    _rate_limiter._windows.clear()
    yield
    await test_db.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    if not transport:
        raise RuntimeError("Failed to create ASGI transport")
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        if not ac:
            raise RuntimeError("Failed to create AsyncClient")
        yield ac
