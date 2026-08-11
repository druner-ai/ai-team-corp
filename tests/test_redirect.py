def test_redirect_returns_302(client):
    # First create a short URL
    resp = client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    code = resp.json()["short_code"]

    # Now follow the redirect (allow_redirects=False to see the 302)
    redir = client.get(f"/{code}", allow_redirects=False)
    assert redir.status_code == 302
    assert redir.headers["location"] == "https://example.com"


def test_redirect_increments_clicks(client):
    resp = client.post("/shorten", json={"url": "https://example.org"})
    code = resp.json()["short_code"]

    # Initial stats should show 0 clicks
    stats = client.get(f"/stats/{code}")
    assert stats.json()["clicks"] == 0

    # Perform a redirect
    client.get(f"/{code}", allow_redirects=False)

    # Clicks should now be 1
    stats = client.get(f"/stats/{code}")
    assert stats.json()["clicks"] == 1
