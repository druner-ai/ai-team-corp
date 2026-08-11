"""Tests for POST /api/shorten and DELETE /api/shorten/{code}."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url(client: AsyncClient):
    """System MUST return 201 with short_code, short_url, original_url, created_at."""
    payload = {"url": "https://example.com/very/long/path?query=1"}
    resp = await client.post("/api/shorten", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["short_url"] == f"http://test/{data['short_code']}"
    # Pydantic HttpUrl may add trailing slash – normalize
    assert data["original_url"].rstrip("/") == "https://example.com/very/long/path?query=1"
    assert "created_at" in data
    assert data["expires_at"] is None


@pytest.mark.asyncio
async def test_create_with_custom_code(client: AsyncClient):
    """System MUST accept a valid custom_code and return it as short_code."""
    payload = {"url": "https://example.com", "custom_code": "myLink1"}
    resp = await client.post("/api/shorten", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["short_code"] == "myLink1"
    assert data["short_url"] == "http://test/myLink1"


@pytest.mark.asyncio
async def test_create_duplicate_custom_code(client: AsyncClient):
    """System MUST return 409 when custom_code is already taken."""
    payload = {"url": "https://example.com", "custom_code": "dupcode"}
    # First creation
    resp1 = await client.post("/api/shorten", json=payload)
    assert resp1.status_code == 201
    # Second creation with same custom_code
    resp2 = await client.post("/api/shorten", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_create_invalid_url_scheme(client: AsyncClient):
    """System MUST return 422 for URLs with non-http(s) schemes."""
    payload = {"url": "ftp://files.example.com"}
    resp = await client.post("/api/shorten", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_missing_url_field(client: AsyncClient):
    """System MUST return 422 when required 'url' field is missing."""
    resp = await client.post("/api/shorten", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_with_expires_at(client: AsyncClient):
    """System MUST accept an optional expires_at and return it."""
    payload = {
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    }
    resp = await client.post("/api/shorten", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["expires_at"] == "2025-12-31T23:59:59Z"


@pytest.mark.asyncio
async def test_create_custom_code_invalid_format(client: AsyncClient):
    """System MUST return 422 for custom_code with invalid characters."""
    payload = {"url": "https://example.com", "custom_code": "ab cd"}
    resp = await client.post("/api/shorten", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_existing_short_code(client: AsyncClient):
    """System MUST return 204 and make the link inactive (redirect returns 404)."""
    # Create a link
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Delete it
    del_resp = await client.delete(f"/api/shorten/{short_code}")
    assert del_resp.status_code == 204

    # Subsequent redirect must return 404 (or 410)
    redir_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redir_resp.status_code in (404, 410)


@pytest.mark.asyncio
async def test_delete_nonexistent_code(client: AsyncClient):
    """System MUST return 404 when deleting a non-existent short code."""
    resp = await client.delete("/api/shorten/nonexistent")
    assert resp.status_code == 404
