import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url_returns_201(client: AsyncClient):
    resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == "https://example.com"
    assert data["short_url"] == f"http://test/{data['short_code']}"


@pytest.mark.asyncio
async def test_create_url_with_invalid_url_returns_422(client: AsyncClient):
    resp = await client.post("/api/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 422
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_create_url_missing_field_returns_422(client: AsyncClient):
    resp = await client.post("/api/shorten", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_url_with_very_long_url_returns_422(client: AsyncClient):
    long_url = "https://" + "a" * 2049
    resp = await client.post("/api/shorten", json={"url": long_url})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_url_with_non_http_scheme_returns_422(client: AsyncClient):
    resp = await client.post("/api/shorten", json={"url": "ftp://example.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_url_with_javascript_scheme_returns_422(client: AsyncClient):
    resp = await client.post("/api/shorten", json={"url": "javascript:alert(1)"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_url_returns_unique_codes(client: AsyncClient):
    resp1 = await client.post("/api/shorten", json={"url": "https://example1.com"})
    resp2 = await client.post("/api/shorten", json={"url": "https://example2.com"})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["short_code"] != resp2.json()["short_code"]


@pytest.mark.asyncio
async def test_create_url_same_url_creates_different_codes(client: AsyncClient):
    resp1 = await client.post("/api/shorten", json={"url": "https://example.com"})
    resp2 = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["short_code"] != resp2.json()["short_code"]
