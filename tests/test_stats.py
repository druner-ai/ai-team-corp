def test_stats_returns_url_info(client):
    # Create a short URL
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    
    # Fetch stats
    response = client.get(f"/stats/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://example.com"
    assert data["short_code"] == short_code
    assert "clicks" in data
    assert "created_at" in data
