"""
Tests for rate limiting middleware.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_rate_limit_not_exceeded(client: AsyncClient, mock_redis):
    """
    Test that requests within rate limit succeed.
    """
    # Mock rate limit check to allow request
    mock_redis.get.return_value = "1"  # 1 request so far
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient, mock_redis):
    """
    Test that requests exceeding rate limit are blocked.
    """
    # Mock rate limit check to deny request
    mock_redis.get.return_value = "100"  # At limit
    
    # Mock TTL for rate limit key
    mock_redis.ttl.return_value = 30
    
    response = await client.get("/health")
    
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    data = response.json()
    assert "detail" in data
    assert "Too many requests" in data["detail"]


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient, mock_redis):
    """
    Test that rate limit headers are present in responses.
    """
    mock_redis.get.return_value = "5"  # Some requests
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers