def test_create_short_url_returns_201(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"
    assert "short_url" in data

def test_create_url_returns_unique_codes(client):
    response1 = client.post("/shorten", json={"url": "https://example.com"})
    response2 = client.post("/shorten", json={"url": "https://example.org"})
    assert response1.json()["short_code"] != response2.json()["short_code"]

def test_create_url_same_url_creates_different_codes(client):
    response1 = client.post("/shorten", json={"url": "https://example.com"})
    response2 = client.post("/shorten", json={"url": "https://example.com"})
    assert response1.json()["short_code"] != response2.json()["short_code"]
