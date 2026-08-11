def test_redirect_returns_302(client):
    # Create a short URL first
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    
    response = client.get(f"/{short_code}", allow_redirects=False)
    assert response.status_code == 302
    # Check that redirect location matches original URL (without trailing slash)
    assert response.headers["location"] == "https://example.com"

def test_redirect_increments_clicks(client):
    # Create a short URL
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    
    # First access
    client.get(f"/{short_code}", allow_redirects=False)
    # Check stats
    stats_resp1 = client.get(f"/stats/{short_code}")
    assert stats_resp1.status_code == 200
    assert stats_resp1.json()["clicks"] == 1
    
    # Second access
    client.get(f"/{short_code}", allow_redirects=False)
    stats_resp2 = client.get(f"/stats/{short_code}")
    assert stats_resp2.json()["clicks"] == 2
