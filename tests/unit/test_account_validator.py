"""ASSERT-05: валидатор расчётных счетов — БИК (9 цифр) + счёт (20 или 28 цифр)."""

import pytest
from app.domain.validators.account_validator import AccountValidator


class TestAccountValidator:
    def test_valid_ru_account(self):
        """Валидный российский счёт (БИК 9 цифр, счёт 20 цифр)."""
        result = AccountValidator.validate("044525225", "40702810400000025200")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_by_account(self):
        """Валидный белорусский счёт (БИК 9 цифр, счёт 28 цифр)."""
        result = AccountValidator.validate("153001795", "3012012345678000000000000000")
        assert result.is_valid is True

    def test_invalid_bik_length(self):
        """БИК не 9 цифр — INVALID_FORMAT."""
        result = AccountValidator.validate("04452522", "40702810400000025200")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_invalid_bik_non_digit(self):
        """БИК содержит нецифровые символы — INVALID_FORMAT."""
        result = AccountValidator.validate("04452522A", "40702810400000025200")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_invalid_account_length(self):
        """Счёт не 20 и не 28 цифр — INVALID_LENGTH."""
        result = AccountValidator.validate("044525225", "4070281040000002520")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)

    def test_invalid_account_non_digit(self):
        """Счёт содержит нецифровые символы — INVALID_FORMAT."""
        result = AccountValidator.validate("044525225", "4070281040000002520A")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_invalid_checksum(self):
        """ASSERT-05: невалидная контрольная сумма — INVALID_CHECKSUM."""
        result = AccountValidator.validate("044525225", "40702810400000025201")
        assert result.is_valid is False
        assert any(e.code == "INVALID_CHECKSUM" for e in result.errors)

    def test_empty_bik(self):
        """Пустой БИК — INVALID_FORMAT."""
        result = AccountValidator.validate("", "40702810400000025200")
        assert result.is_valid is False
        assert any(e.code == "INVALID_FORMAT" for e in result.errors)

    def test_empty_account(self):
        """Пустой счёт — INVALID_LENGTH."""
        result = AccountValidator.validate("044525225", "")
        assert result.is_valid is False
        assert any(e.code == "INVALID_LENGTH" for e in result.errors)
