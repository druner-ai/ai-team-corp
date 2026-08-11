def test_stats_returns_url_info(client):
    # Create a short URL
    resp = client.post("/shorten", json={"url": "https://stats-test.com"})
    code = resp.json()["short_code"]

    # Get stats
    stats = client.get(f"/stats/{code}")
    assert stats.status_code == 200
    data = stats.json()
    assert data["url"] == "https://stats-test.com"
    assert data["clicks"] == 0
    assert "created_at" in data
