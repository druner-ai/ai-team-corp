"""ASSERT-01, ASSERT-05: интеграционные тесты POST /validate/account."""

import pytest
from httpx import AsyncClient


class TestAccountEndpoint:
    @pytest.mark.asyncio
    async def test_valid_account_returns_200(self, client: AsyncClient):
        """ASSERT-05: валидный счёт возвращает 200 с is_valid=true."""
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["type"] == "account"
        assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_invalid_account_checksum_returns_200_with_errors(self, client: AsyncClient):
        """ASSERT-05: невалидная контрольная сумма счёта — 200, is_valid=false."""
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025201"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert any(e["code"] == "INVALID_CHECKSUM" for e in data["errors"])

    @pytest.mark.asyncio
    async def test_mask_contains_first4_last4(self, client: AsyncClient):
        """ASSERT-01: маска счёта содержит первые 4 и последние 4 символа."""
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        data = resp.json()
        assert data["mask"] == "0445********25200"

    @pytest.mark.asyncio
    async def test_hash_is_sha256_of_normalized(self, client: AsyncClient):
        """ASSERT-05: hash — SHA-256 от нормализованного значения."""
        import hashlib
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        data = resp.json()
        expected_normalized = "044525225|40702810400000025200"
        expected_hash = hashlib.sha256(expected_normalized.encode()).hexdigest()
        assert data["hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_original_contains_bik_and_account(self, client: AsyncClient):
        """Поле original содержит БИК и счёт."""
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        data = resp.json()
        assert "044525225" in data["original"]
        assert "40702810400000025200" in data["original"]

    @pytest.mark.asyncio
    async def test_missing_bik_returns_422(self, client: AsyncClient):
        """Отсутствие поля bik — 422."""
        resp = await client.post("/validate/account", json={"account": "40702810400000025200"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_account_returns_422(self, client: AsyncClient):
        """Отсутствие поля account — 422."""
        resp = await client.post("/validate/account", json={"bik": "044525225"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_bik_length_returns_400(self, client: AsyncClient):
        """БИК неверной длины — 400."""
        resp = await client.post("/validate/account", json={
            "bik": "04452522",
            "account": "40702810400000025200"
        })
        assert resp.status_code == 400
