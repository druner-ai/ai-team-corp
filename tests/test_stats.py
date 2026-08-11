# tests/test_stats.py
import pytest


def test_stats_for_existing_link(client):
    """Получение статистики для существующей ссылки."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    response = client.get(f"/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0
    assert "created_at" in data


def test_stats_after_clicks(client):
    """Проверка статистики после нескольких переходов."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Делаем 3 перехода
    for _ in range(3):
        client.get(f"/{short_code}", follow_redirects=False)

    response = client.get(f"/{short_code}/stats")
    assert response.status_code == 200
    assert response.json()["clicks"] == 3


def test_stats_not_found(client):
    """Попытка получить статистику для несуществующей ссылки."""
    response = client.get("/nonexistent/stats")
    assert response.status_code == 404
