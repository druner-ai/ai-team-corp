"""
Tests for GET /health endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient, mock_redis):
    """
    Test health check when all services are healthy.
    """
    mock_redis.ping.return_value = True
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(client: AsyncClient, mock_redis):
    """
    Test health check when Redis is unhealthy.
    """
    mock_redis.ping.side_effect = Exception("Redis connection failed")
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "unhealthy"