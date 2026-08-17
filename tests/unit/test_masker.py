"""ASSERT-01: маскирование — первые 4 + звёздочки + последние 4 символа."""

import pytest
from app.utils.masker import Masker


class TestMasker:
    def test_mask_standard_card_length(self):
        """ASSERT-01: 16-значная карта маскируется как 1234********5678."""
        masked = Masker.mask("4111111111111111")
        assert masked == "4111********1111"

    def test_mask_iban(self):
        """ASSERT-01: IBAN маскируется: первые 4 + звёздочки + последние 4."""
        masked = Masker.mask("DE89370400440532013000")
        assert masked == "DE89****************3000"

    def test_mask_account(self):
        """ASSERT-01: расчётный счёт маскируется."""
        masked = Masker.mask("044525225|40702810400000025200")
        assert masked == "0445********25200"

    def test_mask_exactly_8_chars(self):
        """ASSERT-01: ровно 8 символов — первые 4 + последние 4, без звёздочек."""
        masked = Masker.mask("12345678")
        assert masked == "12345678"

    def test_mask_less_than_8_chars(self):
        """Короткая строка возвращается как есть."""
        masked = Masker.mask("1234567")
        assert masked == "1234567"

    def test_mask_empty_string(self):
        """Пустая строка возвращает пустую строку."""
        masked = Masker.mask("")
        assert masked == ""
