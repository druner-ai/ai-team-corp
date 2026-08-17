"""ASSERT-05: нормализация удаляет пробелы, дефисы, переводит в верхний регистр."""

import pytest
from app.utils.normalizer import Normalizer


class TestNormalizer:
    def test_strips_whitespace(self):
        """ASSERT-05: пробелы по краям удаляются."""
        assert Normalizer.normalize("  4111111111111111  ") == "4111111111111111"

    def test_removes_internal_spaces(self):
        """ASSERT-05: внутренние пробелы удаляются."""
        assert Normalizer.normalize("4111 1111 1111 1111") == "4111111111111111"

    def test_removes_hyphens(self):
        """ASSERT-05: дефисы удаляются."""
        assert Normalizer.normalize("4111-1111-1111-1111") == "4111111111111111"

    def test_converts_to_uppercase(self):
        """ASSERT-05: буквы переводятся в верхний регистр."""
        assert Normalizer.normalize("de89370400440532013000") == "DE89370400440532013000"

    def test_handles_mixed_formatting(self):
        """ASSERT-05: смешанное форматирование (пробелы + дефисы + нижний регистр)."""
        assert Normalizer.normalize("  de89-3704 0044 0532-0130 00 ") == "DE89370400440532013000"

    def test_empty_string_returns_empty(self):
        """Пустая строка остаётся пустой."""
        assert Normalizer.normalize("") == ""

    def test_only_separators_returns_empty(self):
        """Строка из одних разделителей становится пустой."""
        assert Normalizer.normalize("  - -  ") == ""
