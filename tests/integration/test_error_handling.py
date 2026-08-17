"""ASSERT-03, ASSERT-04: обработка ошибок — 404, 422, 400."""

import pytest
from httpx import AsyncClient


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_unknown_route_returns_404(self, client: AsyncClient):
        """ASSERT-04: неизвестный маршрут — 404 с ROUTE_NOT_FOUND."""
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "ROUTE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_unknown_post_route_returns_404(self, client: AsyncClient):
        """ASSERT-04: POST на неизвестный маршрут — 404."""
        resp = await client.post("/validate/unknown", json={})
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "ROUTE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_422_response_has_error_structure(self, client: AsyncClient):
        """ASSERT-03: 422 ответ содержит error и detail."""
        resp = await client.post("/validate/card", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_400_response_has_error_structure(self, client: AsyncClient):
        """400 ответ содержит error."""
        resp = await client.post("/validate/card", json={"card_number": "   "})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    @pytest.mark.asyncio
    async def test_422_for_wrong_type_in_iban(self, client: AsyncClient):
        """ASSERT-03: неверный тип поля iban — 422."""
        resp = await client.post("/validate/iban", json={"iban": 12345})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_422_for_wrong_type_in_account(self, client: AsyncClient):
        """ASSERT-03: неверный тип поля bik — 422."""
        resp = await client.post("/validate/account", json={
            "bik": 123456789,
            "account": "40702810400000025200"
        })
        assert resp.status_code == 422
