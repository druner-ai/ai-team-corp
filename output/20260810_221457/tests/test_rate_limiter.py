import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limit(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr("src.config.settings.RATE_LIMIT_PER_MINUTE", 2)
    responses = []
    for _ in range(3):
        resp = await async_client.post("/shorten", json={"url": "https://example.com"})
        responses.append(resp.status_code)
    assert responses[0] == 201
    assert responses[1] == 201
    assert responses[2] == 429