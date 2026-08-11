from fastapi.testclient import TestClient


def test_create_url(client: TestClient):
    response = client.post("/urls", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "slug" in data
    assert data["original_url"] == "https://example.com"


def test_redirect_to_url(client: TestClient):
    # First create a URL
    create_resp = client.post("/urls", json={"url": "https://example.org"})
    slug = create_resp.json()["slug"]
    # Then access it
    redirect_resp = client.get(f"/{slug}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.org"


def test_stats(client: TestClient):
    create_resp = client.post("/urls", json={"url": "https://example.net"})
    slug = create_resp.json()["slug"]
    # Simulate a visit
    client.get(f"/{slug}", follow_redirects=False)
    stats_resp = client.get(f"/stats/{slug}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["visit_count"] == 1
    assert len(data["visits"]) == 1
