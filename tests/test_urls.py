import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_url_success(async_client: AsyncClient):
    payload = {"original_url": "https://example.com/path?q=1"}
    response = await async_client.post("/api/v1/urls", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "slug" in data
    assert data["original_url"] == payload["original_url"]
    assert data["short_url"].startswith("http://test/r/")


@pytest.mark.asyncio
async def test_create_url_with_custom_slug(async_client: AsyncClient):
    payload = {"original_url": "https://example.com", "custom_slug": "my-link"}
    response = await async_client.post("/api/v1/urls", json=payload)
    assert response.status_code == 201
    assert response.json()["slug"] == "my-link"


@pytest.mark.asyncio
async def test_create_url_duplicate_custom_slug(async_client: AsyncClient):
    payload = {"original_url": "https://example.com", "custom_slug": "dup"}
    # First creation succeeds
    await async_client.post("/api/v1/urls", json=payload)
    # Second must return conflict
    response = await async_client.post("/api/v1/urls", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_url_invalid_scheme(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/urls", json={"original_url": "ftp://bad.com"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_url_no_scheme(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/urls", json={"original_url": "example.com"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_url(async_client: AsyncClient):
    # Create a URL
    resp = await async_client.post(
        "/api/v1/urls", json={"original_url": "https://example.com"}
    )
    slug = resp.json()["slug"]
    # Delete it
    del_resp = await async_client.delete(f"/api/v1/urls/{slug}")
    assert del_resp.status_code == 204
    # Redirect should now return 404
    redir = await async_client.get(f"/r/{slug}", follow_redirects=False)
    assert redir.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(async_client: AsyncClient):
    response = await async_client.delete("/api/v1/urls/absent")
    assert response.status_code == 404
