"""
Tests for GET /{short_code} redirect endpoint.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Should redirect to original URL."""
    # First create a short URL
    create_resp = await client.post("/shorten/", json={"url": "https://example.com/target"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    # Then request redirect
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/target"

@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Should return 404 for non-existent code."""
    resp = await client.get("/nonexistent", follow_redirects=False)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_redirect_expired(client: AsyncClient):
    """Should return 410 Gone for expired URLs."""
    # Create with past expiration
    resp_create = await client.post("/shorten/", json={
        "url": "https://example.com",
        "expires_at": "2020-01-01T00:00:00Z"
    })
    short_code = resp_create.json()["short_code"]
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 410

@pytest.mark.asyncio
async def test_redirect_after_delete(client: AsyncClient):
    """Should return 404 after soft delete."""
    resp_create = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = resp_create.json()["short_code"]
    # Delete it
    del_resp = await client.delete(f"/{short_code}")
    assert del_resp.status_code == 204
    # Try redirect
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 404