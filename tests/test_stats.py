"""
Tests for URL statistics endpoint.
"""

from fastapi import status


def test_get_stats_success(client):
    # Create a short URL
    create_payload = {"url": "https://example.com/stats-test"}
    create_resp = client.post("/api/shorten", json=create_payload)
    short_code = create_resp.json()["short_code"]

    # Get stats
    response = client.get(f"/api/stats/{short_code}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == create_payload["url"]
    assert data["access_count"] == 0
    assert "created_at" in data


def test_get_stats_not_found(client):
    response = client.get("/api/stats/nonexistent")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_stats_after_redirects(client):
    # Create a short URL
    create_payload = {"url": "https://example.com/stats-after"}
    create_resp = client.post("/api/shorten", json=create_payload)
    short_code = create_resp.json()["short_code"]

    # Perform 3 redirects
    for _ in range(3):
        client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    response = client.get(f"/api/stats/{short_code}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["access_count"] == 3
