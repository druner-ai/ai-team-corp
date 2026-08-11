import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Тест успешного редиректа по короткой ссылке."""
    # Создаём ссылку
    create_resp = await client.post(
        "/api/v1/urls",
        json={"original_url": "https://example.com/target"},
    )
    slug = create_resp.json()["slug"]

    # Переходим по короткой ссылке (без редиректа)
    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Тест 404 при переходе по несуществующей ссылке."""
    response = await client.get("/nonexistent-slug")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_records_click(client: AsyncClient):
    """Тест записи клика при переходе."""
    # Создаём ссылку
    create_resp = await client.post(
        "/api/v1/urls",
        json={"original_url": "https://example.com"},
    )
    slug = create_resp.json()["slug"]

    # Переходим по ссылке
    await client.get(f"/{slug}", follow_redirects=False)

    # Проверяем статистику
    stats_resp = await client.get(f"/api/v1/stats/{slug}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 1
