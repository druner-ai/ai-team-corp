"""
Tests for rate limiting middleware.
"""
import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_exceeded(async_client: AsyncClient, mock_redis):
    # Simulate limit exceeded by setting the count directly
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"
    await mock_redis.set(key, 101)

    response = await async_client.get("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_allowed(async_client: AsyncClient, mock_redis):
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"
    await mock_redis.set(key, 1)

    response = await async_client.get("/health")
    assert response.status_code != 429