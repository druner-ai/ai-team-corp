import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_link_success(client: AsyncClient):
    """Test successful creation of a short link."""
    payload = {"url": "https://example.com/long/path"}
    response = await client.post("/api/links", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == "https://example.com/long/path"
    assert data["short_url"] == f"http://test/{data['short_code']}"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_link_duplicate_url(client: AsyncClient):
    """Test that submitting the same URL returns the existing short code."""
    payload = {"url": "https://example.com/duplicate"}
    response1 = await client.post("/api/links", json=payload)
    assert response1.status_code == 201
    data1 = response1.json()

    response2 = await client.post("/api/links", json=payload)
    assert response2.status_code == 201
    data2 = response2.json()

    assert data1["short_code"] == data2["short_code"]
    assert data1["original_url"] == data2["original_url"]


@pytest.mark.asyncio
async def test_create_link_invalid_url(client: AsyncClient):
    """Test validation error for invalid URL."""
    payload = {"url": "not-a-valid-url"}
    response = await client.post("/api/links", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_link_empty_url(client: AsyncClient):
    """Test validation error for missing URL field."""
    response = await client.post("/api/links", json={})
    assert response.status_code == 422
