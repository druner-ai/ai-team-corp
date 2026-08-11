# tests/test_integration.py
import pytest


def test_full_lifecycle(client):
    """Полный жизненный цикл: создание -> редирект -> статистика -> удаление."""
    # Создание
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Редирект
    redirect_resp = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com"

    # Статистика
    stats_resp = client.get(f"/{short_code}/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1

    # Удаление
    delete_resp = client.delete(f"/{short_code}")
    assert delete_resp.status_code == 200

    # Проверка, что удалено
    get_resp = client.get(f"/{short_code}", follow_redirects=False)
    assert get_resp.status_code == 404


def test_multiple_redirects_accumulate_clicks(client):
    """Проверка накопления кликов при множественных редиректах."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    for _ in range(5):
        client.get(f"/{short_code}", follow_redirects=False)

    stats_resp = client.get(f"/{short_code}/stats")
    assert stats_resp.json()["clicks"] == 5


def test_custom_code_and_redirect(client):
    """Создание с кастомным кодом и последующий редирект."""
    create_resp = client.post(
        "/shorten",
        json={"url": "https://example.com", "custom_code": "mycustom"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["short_code"] == "mycustom"

    redirect_resp = client.get("/mycustom", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com"
