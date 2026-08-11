"""
Tests for URL shortening endpoint.
"""

from fastapi import status


def test_create_short_url_success(client):
    payload = {"url": "https://example.com/very/long/url/path"}
    response = client.post("/api/shorten", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == payload["url"]
    assert data["short_url"] == f"http://localhost:8000/{data['short_code']}"


def test_create_short_url_duplicate_returns_same_code(client):
    payload = {"url": "https://example.com/duplicate"}

    response1 = client.post("/api/shorten", json=payload)
    assert response1.status_code == status.HTTP_201_CREATED
    code1 = response1.json()["short_code"]

    response2 = client.post("/api/shorten", json=payload)
    assert response2.status_code == status.HTTP_201_CREATED
    code2 = response2.json()["short_code"]

    assert code1 == code2


def test_create_short_url_invalid_url(client):
    payload = {"url": "not-a-valid-url"}
    response = client.post("/api/shorten", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
