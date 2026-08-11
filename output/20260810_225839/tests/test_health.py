"""
Tests for health check endpoint.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
    assert data["redis_connected"] is True