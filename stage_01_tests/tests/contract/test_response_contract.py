"""ASSERT-01, ASSERT-05: проверка единообразия контракта ответов."""

import pytest
from httpx import AsyncClient


class TestResponseContract:
    """Проверяет, что все успешные ответы имеют единую структуру."""

    REQUIRED_FIELDS = ["original", "normalized", "is_valid", "type", "mask", "hash", "errors"]

    @pytest.mark.asyncio
    async def test_card_response_has_all_fields(self, client: AsyncClient):
        """Ответ /validate/card содержит все обязательные поля."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        assert resp.status_code == 200
        data = resp.json()
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_iban_response_has_all_fields(self, client: AsyncClient):
        """Ответ /validate/iban содержит все обязательные поля."""
        resp = await client.post("/validate/iban", json={"iban": "DE89370400440532013000"})
        assert resp.status_code == 200
        data = resp.json()
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_account_response_has_all_fields(self, client: AsyncClient):
        """Ответ /validate/account содержит все обязательные поля."""
        resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        assert resp.status_code == 200
        data = resp.json()
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_errors_is_list(self, client: AsyncClient):
        """Поле errors всегда список."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        data = resp.json()
        assert isinstance(data["errors"], list)

    @pytest.mark.asyncio
    async def test_error_item_has_code_and_message(self, client: AsyncClient):
        """Каждый элемент errors содержит code и message."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111112"})
        data = resp.json()
        for error in data["errors"]:
            assert "code" in error
            assert "message" in error

    @pytest.mark.asyncio
    async def test_hash_is_64_char_hex(self, client: AsyncClient):
        """ASSERT-05: hash — 64-символьная hex-строка."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        data = resp.json()
        assert len(data["hash"]) == 64
        # Проверяем, что это hex
        int(data["hash"], 16)

    @pytest.mark.asyncio
    async def test_mask_starts_with_first_4_chars(self, client: AsyncClient):
        """ASSERT-01: маска начинается с первых 4 символов нормализованного значения."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        data = resp.json()
        assert data["mask"].startswith(data["normalized"][:4])

    @pytest.mark.asyncio
    async def test_mask_ends_with_last_4_chars(self, client: AsyncClient):
        """ASSERT-01: маска заканчивается последними 4 символами нормализованного значения."""
        resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        data = resp.json()
        assert data["mask"].endswith(data["normalized"][-4:])

    @pytest.mark.asyncio
    async def test_identical_requisites_produce_same_hash(self, client: AsyncClient):
        """ASSERT-05: одинаковые реквизиты с разным форматированием дают одинаковый хэш."""
        resp1 = await client.post("/validate/card", json={"card_number": "4111-1111-1111-1111"})
        resp2 = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        assert resp1.json()["hash"] == resp2.json()["hash"]

    @pytest.mark.asyncio
    async def test_type_field_is_correct(self, client: AsyncClient):
        """Поле type соответствует типу реквизита."""
        card_resp = await client.post("/validate/card", json={"card_number": "4111111111111111"})
        assert card_resp.json()["type"] == "card"

        iban_resp = await client.post("/validate/iban", json={"iban": "DE89370400440532013000"})
        assert iban_resp.json()["type"] == "iban"

        acc_resp = await client.post("/validate/account", json={
            "bik": "044525225",
            "account": "40702810400000025200"
        })
        assert acc_resp.json()["type"] == "account"
