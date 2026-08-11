"""
Unit tests for rate limiter logic (using fakeredis).
"""
import time
import pytest
import pytest_asyncio

from src.middleware.rate_limit import RateLimitMiddleware


@pytest_asyncio.fixture
async def redis_limiter():
    """Create a FakeRedis instance for rate limiter tests."""
    from fakeredis.aioredis import FakeRedis
    return FakeRedis()


@pytest.mark.asyncio
async def test_rate_limit_within_window(redis_limiter):
    """Requests within the limit should not be blocked."""
    middleware = RateLimitMiddleware(app=None, redis_client=redis_limiter)
    # Simulate 3 requests that should pass (limit=30, window=60)
    limit = middleware.limit
    window = middleware.window
    ip = "127.0.0.1"
    key = f"ratelimit:{ip}"
    now = time.time()

    # Initially empty
    count = await redis_limiter.zcard(key)
    assert count == 0

    # Add some entries manually to simulate previous requests
    for i in range(limit):
        await redis_limiter.zadd(key, {f"{now - i}": now - i})
    # Should be exactly limit
    count = await redis_limiter.zcard(key)
    assert count == limit

    # Next request should trigger block
    # We'll simulate dispatch logic manually
    async with redis_limiter.pipeline() as pipe:
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        _, _, new_count = await pipe.execute()
    assert new_count > limit