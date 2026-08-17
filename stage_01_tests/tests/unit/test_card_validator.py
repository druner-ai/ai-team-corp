"""ASSERT-05: валидатор карт — Luhn + длина 13–19."""

import pytest
from app.domain.validators.card_validator import CardValidator


class TestCardValidator:
    def test_valid_16_digit_card(self):
        """Валидная 16-значная карта (4111111111111111)."""
        result = CardValidator.validate("4111111111111111")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_13_digit_card(self):
        """Валидная 13-значная карта."""
        # 13-digit Visa: 4222222222222 (Luhn-валидная)
        result = CardValidator.validate("4222222222222")
        assert result.is_valid is True

    def test_invalid_checksum(self):
        """ASSERT-05: невалидная контрольная сумма — INVALID_CHECKSUM."""
        result = CardValidator.validate("4111111111111112")
        assert result.is_valid is False
        assert any(e.code == "INVALID_CHECKSUM" for e in result.errors)

    def test_too_short_card(self):
        """Длина меньше 13 — INVALID_LENGTH."""
        result = CardValidator.validate("411111111111")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)

    def test_too_long_card(self):
        """Длина больше 19 — INVALID_LENGTH."""
        result = CardValidator.validate("41111111111111111111")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)

    def test_non_digit_characters(self):
        """Нецифровые символы — INVALID_FORMAT."""
        result = CardValidator.validate("4111AAAA11111111")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_empty_string(self):
        """Пустая строка — INVALID_LENGTH."""
        result = CardValidator.validate("")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)
