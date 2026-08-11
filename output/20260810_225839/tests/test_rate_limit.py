"""
Tests for rate limiting on various endpoints.
"""
import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_rate_limit_redirect(client: AsyncClient):
    """Test that redirect endpoint respects rate limits."""
    # Create a URL first
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    # Fast requests beyond limit
    statuses = []
    for _ in range(105):  # limit is 100/min
        resp = await client.get(f"/{short_code}", follow_redirects=False)
        statuses.append(resp.status_code)
    assert 429 in statuses

@pytest.mark.asyncio
async def test_rate_limit_stats(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    for _ in range(35):  # limit 30/min
        await client.get(f"/stats/{short_code}")
    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 429