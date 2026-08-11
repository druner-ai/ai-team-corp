def test_shorten_valid_url(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_url" in data
    assert "short_code" in data
    assert data["short_url"].startswith("http://localhost:8000/")

def test_shorten_invalid_url(client):
    response = client.post("/shorten", json={"url": "not-a-valid-url"})
    assert response.status_code == 422

def test_shorten_missing_url(client):
    response = client.post("/shorten", json={})
    assert response.status_code == 422

def test_shorten_duplicate_url_creates_new_code(client):
    response1 = client.post("/shorten", json={"url": "https://example.com"})
    assert response1.status_code == 201
    code1 = response1.json()["short_code"]

    response2 = client.post("/shorten", json={"url": "https://example.com"})
    assert response2.status_code == 201
    code2 = response2.json()["short_code"]

    assert code1 != code2
