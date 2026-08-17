"""ASSERT-05: валидатор IBAN — mod-97 + длина 15–34."""

import pytest
from app.domain.validators.iban_validator import IbanValidator


class TestIbanValidator:
    def test_valid_german_iban(self):
        """Валидный немецкий IBAN."""
        result = IbanValidator.validate("DE89370400440532013000")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_uk_iban(self):
        """Валидный британский IBAN."""
        result = IbanValidator.validate("GB29NWBK60161331926819")
        assert result.is_valid is True

    def test_invalid_checksum(self):
        """ASSERT-05: невалидная контрольная сумма — INVALID_CHECKSUM."""
        result = IbanValidator.validate("DE89370400440532013001")
        assert result.is_valid is False
        assert any(e.code == "INVALID_CHECKSUM" for e in result.errors)

    def test_too_short_iban(self):
        """Длина меньше 15 — INVALID_LENGTH."""
        result = IbanValidator.validate("DE8937040044")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)

    def test_too_long_iban(self):
        """Длина больше 34 — INVALID_LENGTH."""
        result = IbanValidator.validate("DE89370400440532013000DE8937040044")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)

    def test_invalid_country_code(self):
        """Неверный код страны — INVALID_FORMAT."""
        result = IbanValidator.validate("XX89370400440532013000")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_empty_string(self):
        """Пустая строка — INVALID_LENGTH."""
        result = IbanValidator.validate("")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)
