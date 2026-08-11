"""
Tests for URL redirection endpoint.
"""

from fastapi import status


def test_redirect_success(client):
    # First create a short URL
    create_payload = {"url": "https://example.com/target"}
    create_resp = client.post("/api/shorten", json=create_payload)
    short_code = create_resp.json()["short_code"]

    # Then test redirect
    response = client.get(f"/{short_code}", follow_redirects=False)

    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == create_payload["url"]


def test_redirect_not_found(client):
    response = client.get("/nonexistent", follow_redirects=False)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_redirect_increments_access_count(client):
    # Create a short URL
    create_payload = {"url": "https://example.com/count-test"}
    create_resp = client.post("/api/shorten", json=create_payload)
    short_code = create_resp.json()["short_code"]

    # Access it twice
    client.get(f"/{short_code}", follow_redirects=False)
    client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    stats_resp = client.get(f"/api/stats/{short_code}")
    assert stats_resp.status_code == status.HTTP_200_OK
    assert stats_resp.json()["access_count"] == 2
