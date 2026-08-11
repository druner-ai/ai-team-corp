"""Tests for POST /api/v1/links/shorten contract."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url_valid(client: AsyncClient):
    """System MUST create a short link and return 201 with required fields."""
    payload = {"original_url": "https://example.com/very/long/path?query=123"}
    resp = await client.post("/api/v1/links/shorten", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    # Check required fields
    assert "short_code" in data
    assert "original_url" in data
    assert "short_url" in data
    # short_code should be non-empty and length <= 8
    code = data["short_code"]
    assert len(code) > 0
    assert len(code) <= 8
    # original_url matches what was sent
    assert data["original_url"] == payload["original_url"]
    # short_url should contain the short_code
    assert code in data["short_url"]


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient):
    """System MUST reject invalid URL with 422."""
    payload = {"original_url": "not-a-valid-url"}
    resp = await client.post("/api/v1/links/shorten", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_missing_field(client: AsyncClient):
    """System MUST reject request without required field with 422."""
    payload = {}  # missing original_url
    resp = await client.post("/api/v1/links/shorten", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_duplicate_yields_unique_codes(client: AsyncClient):
    """Even for the same original URL, codes should be unique."""
    payload = {"original_url": "https://example.com"}
    resp1 = await client.post("/api/v1/links/shorten", json=payload)
    resp2 = await client.post("/api/v1/links/shorten", json=payload)
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    code1 = resp1.json()["short_code"]
    code2 = resp2.json()["short_code"]
    assert code1 != code2, "Each creation must generate a unique short_code"
