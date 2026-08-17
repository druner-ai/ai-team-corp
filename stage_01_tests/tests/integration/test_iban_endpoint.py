"""ASSERT-01, ASSERT-05: интеграционные тесты POST /validate/iban."""

import pytest
from httpx import AsyncClient


class TestIbanEndpoint:
    @pytest.mark.asyncio
    async def test_valid_iban_returns_200(self, client: AsyncClient):
        """ASSERT-05: валидный IBAN возвращает 200 с is_valid=true."""
        resp = await client.post("/validate/iban", json={"iban": "DE89 3704 0044 0532 0130 00"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["type"] == "iban"
        assert data["normalized"] == "DE89370400440532013000"
        assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_invalid_iban_checksum_returns_200_with_errors(self, client: AsyncClient):
        """ASSERT-05: невалидная контрольная сумма IBAN — 200, is_valid=false."""
        resp = await client.post("/validate/iban", json={"iban": "DE89370400440532013001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert any(e["code"] == "INVALID_CHECKSUM" for e in data["errors"])

    @pytest.mark.asyncio
    async def test_mask_contains_first4_last4(self, client: AsyncClient):
        """ASSERT-01: маска IBAN содержит первые 4 и последние 4 символа."""
        resp = await client.post("/validate/iban", json={"iban": "DE89370400440532013000"})
        data = resp.json()
        assert data["mask"] == "DE89****************3000"

    @pytest.mark.asyncio
    async def test_hash_is_sha256_of_normalized(self, client: AsyncClient):
        """ASSERT-05: hash — SHA-256 от нормализованного IBAN."""
        import hashlib
        resp = await client.post("/validate/iban", json={"iban": "DE89 3704 0044 0532 0130 00"})
        data = resp.json()
        expected_hash = hashlib.sha256("DE89370400440532013000".encode()).hexdigest()
        assert data["hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_original_preserved(self, client: AsyncClient):
        """Поле original содержит исходный ввод."""
        resp = await client.post("/validate/iban", json={"iban": "DE89 3704 0044 0532 0130 00"})
        data = resp.json()
        assert data["original"] == "DE89 3704 0044 0532 0130 00"

    @pytest.mark.asyncio
    async def test_missing_iban_returns_422(self, client: AsyncClient):
        """Отсутствие поля iban — 422."""
        resp = await client.post("/validate/iban", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_iban_returns_400(self, client: AsyncClient):
        """Пустая строка после нормализации — 400."""
        resp = await client.post("/validate/iban", json={"iban": "   "})
        assert resp.status_code == 400
