import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_url_success(client: AsyncClient):
    """Тест успешного создания короткой ссылки."""
    response = await client.post(
        "/api/v1/urls",
        json={"original_url": "https://example.com/very/long/url"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "slug" in data
    assert data["original_url"] == "https://example.com/very/long/url"
    assert "short_url" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_url_with_custom_slug(client: AsyncClient):
    """Тест создания ссылки с кастомным slug."""
    response = await client.post(
        "/api/v1/urls",
        json={
            "original_url": "https://example.com",
            "custom_slug": "my-custom-slug",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "my-custom-slug"


@pytest.mark.asyncio
async def test_create_url_duplicate_custom_slug(client: AsyncClient):
    """Тест ошибки при дублировании кастомного slug."""
    # Создаём первую ссылку
    await client.post(
        "/api/v1/urls",
        json={
            "original_url": "https://example.com",
            "custom_slug": "duplicate-slug",
        },
    )
    # Пытаемся создать вторую с тем же slug
    response = await client.post(
        "/api/v1/urls",
        json={
            "original_url": "https://other.com",
            "custom_slug": "duplicate-slug",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_url(client: AsyncClient):
    """Тест успешного удаления (деактивации) ссылки."""
    # Создаём ссылку
    create_resp = await client.post(
        "/api/v1/urls",
        json={"original_url": "https://example.com"},
    )
    slug = create_resp.json()["slug"]

    # Удаляем
    response = await client.delete(f"/api/v1/urls/{slug}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    """Тест удаления несуществующей ссылки."""
    response = await client.delete("/api/v1/urls/nonexistent")
    assert response.status_code == 404
