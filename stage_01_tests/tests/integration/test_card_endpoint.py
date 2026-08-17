"""ASSERT-01, ASSERT-03, ASSERT-05: интеграционные тесты POST /validate/card."""

import pytest
from httpx import AsyncClient


class TestCardEndpoint:
    @pytest.mark.asyncio
    async def test_valid_card_returns_200(self, client: AsyncClient):
        """ASSERT-05: валидная карта возвращает 200 с is_valid=true."""
        resp = await client.post("/validate/card", json={"card_number": "4111-1111-1111-1111"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["type"] == "card"
        assert data["normalized"] == "4111111111111111"
        assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_invalid_checksum_returns_200_with_errors(self, client: AsyncClient):
        """ASSERT-05: невалидная контрольная сумма — 200, is_valid=false, ошибка INVALID_CHECKSUM."""
        resp = await client.post("/validate/card", json={"card_number": "4111-1111-1111-1112"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert any(e["code"] == "INVALID_CHECKSUM" for e in data["errors"])

    @pytest.mark.asyncio
    async def test_mask_contains_first4_last4(self, client: AsyncClient):
        """ASSERT-01: маска содержит первые 4 и последние 4 символа."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        data = resp.json()
        assert data["mask"] == "4111********1111"

    @pytest.mark.asyncio
    async def test_hash_is_sha256_of_normalized(self, client: AsyncClient):
        """ASSERT-05: hash — SHA-256 от нормализованного значения."""
        import hashlib
        resp = await client.post("/validate/card", json={"card_number": "4111-1111-1111-1111"})
        data = resp.json()
        expected_hash = hashlib.sha256("4111111111111111".encode()).hexdigest()
        assert data["hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_original_preserved(self, client: AsyncClient):
        """Поле original содержит исходный ввод."""
        resp = await client.post("/validate/card", json={"card_number": "4111-1111-1111-1111"})
        data = resp.json()
        assert data["original"] == "4111-1111-1111-1111"

    @pytest.mark.asyncio
    async def test_missing_card_number_returns_422(self, client: AsyncClient):
        """ASSERT-03: отсутствие поля card_number — 422."""
        resp = await client.post("/validate/card", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_wrong_type_card_number_returns_422(self, client: AsyncClient):
        """ASSERT-03: неверный тип поля card_number — 422."""
        resp = await client.post("/validate/card", json={"card_number": 1234567890123456})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_card_number_returns_400(self, client: AsyncClient):
        """Пустая строка после нормализации — 400."""
        resp = await client.post("/validate/card", json={"card_number": "   "})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_non_digit_card_returns_400(self, client: AsyncClient):
        """Нецифровые символы в карте — 400."""
        resp = await client.post("/validate/card", json={"card_number": "abcd-efgh-ijkl-mnop"})
        assert resp.status_code == 400
