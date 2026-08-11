import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_shorten_valid_url(client: AsyncClient):
    response = await client.post("/api/v1/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "code" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].endswith(data["code"])


@pytest.mark.anyio
async def test_shorten_with_custom_code(client: AsyncClient):
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/page", "custom_code": "myLink42"},
    )
    assert response.status_code == 201
    assert response.json()["code"] == "myLink42"


@pytest.mark.anyio
async def test_shorten_custom_code_conflict(client: AsyncClient):
    # First creation
    await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com", "custom_code": "code1"},
    )
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/other", "custom_code": "code1"},
    )
    assert response.status_code == 409
    assert "already in use" in response.json()["detail"]


@pytest.mark.anyio
async def test_shorten_reuse_existing_url(client: AsyncClient):
    # First call
    r1 = await client.post("/api/v1/shorten", json={"url": "https://example.com/reuse"})
    assert r1.status_code == 201
    code1 = r1.json()["code"]

    # Second call with same URL should return the same code (reuse = True by default)
    r2 = await client.post("/api/v1/shorten", json={"url": "https://example.com/reuse"})
    assert r2.status_code == 201
    assert r2.json()["code"] == code1


@pytest.mark.anyio
async def test_shorten_invalid_url(client: AsyncClient):
    response = await client.post("/api/v1/shorten", json={"url": "javascript:alert(1)"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_shorten_invalid_custom_code_format(client: AsyncClient):
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com", "custom_code": "ab"},
    )
    assert response.status_code == 422  # Pydantic validation error
