import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_url_success(client: AsyncClient):
    response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_url_with_custom_code(client: AsyncClient):
    response = await client.post("/api/v1/urls", json={
        "url": "https://example.com",
        "custom_code": "mycode"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "mycode"


@pytest.mark.asyncio
async def test_create_url_duplicate_custom_code(client: AsyncClient):
    await client.post("/api/v1/urls", json={
        "url": "https://example.com",
        "custom_code": "mycode"
    })
    response = await client.post("/api/v1/urls", json={
        "url": "https://example2.com",
        "custom_code": "mycode"
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_url_invalid_url(client: AsyncClient):
    response = await client.post("/api/v1/urls", json={"url": "not-a-valid-url"})
    assert response.status_code == 422
