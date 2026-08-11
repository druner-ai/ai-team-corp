# tests/test_redirect.py
import pytest


def test_redirect_valid_url(client):
    """Редирект по валидной короткой ссылке."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    response = client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


def test_redirect_increments_clicks(client):
    """Проверка, что редирект увеличивает счётчик кликов."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Первый переход
    client.get(f"/{short_code}", follow_redirects=False)

    # Проверяем статистику
    stats_resp = client.get(f"/{short_code}/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1

    # Второй переход
    client.get(f"/{short_code}", follow_redirects=False)

    stats_resp = client.get(f"/{short_code}/stats")
    assert stats_resp.json()["clicks"] == 2


def test_redirect_not_found(client):
    """Редирект по несуществующей короткой ссылке."""
    response = client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404


def test_redirect_expired_link(client):
    """Редирект по истёкшей короткой ссылке."""
    create_resp = client.post(
        "/shorten",
        json={
            "url": "https://example.com",
            "expires_at": "2020-01-01T00:00:00Z",
        },
    )
    short_code = create_resp.json()["short_code"]

    response = client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 410
