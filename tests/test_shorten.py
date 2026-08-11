def test_create_short_url_returns_201(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["short_url"] == f"http://testserver/{data['short_code']}"


def test_create_url_returns_unique_codes(client):
    codes = set()
    for _ in range(5):
        resp = client.post("/shorten", json={"url": "https://unique.com"})
        assert resp.status_code == 201
        codes.add(resp.json()["short_code"])
    assert len(codes) == 5  # all codes should be different


def test_create_url_same_url_creates_different_codes(client):
    resp1 = client.post("/shorten", json={"url": "https://same.com"})
    resp2 = client.post("/shorten", json={"url": "https://same.com"})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["short_code"] != resp2.json()["short_code"]
