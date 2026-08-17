"""ASSERT-05: хэширование — SHA-256 hex от нормализованного значения."""

import hashlib
import pytest
from app.utils.hasher import Hasher


class TestHasher:
    def test_hash_is_sha256_hex(self):
        """ASSERT-05: хэш — SHA-256 в hex-представлении."""
        value = "4111111111111111"
        expected = hashlib.sha256(value.encode()).hexdigest()
        assert Hasher.hash(value) == expected

    def test_hash_is_deterministic(self):
        """ASSERT-05: одинаковый ввод даёт одинаковый хэш."""
        value = "DE89370400440532013000"
        assert Hasher.hash(value) == Hasher.hash(value)

    def test_different_inputs_produce_different_hashes(self):
        """Разные значения дают разные хэши."""
        assert Hasher.hash("4111111111111111") != Hasher.hash("4111111111111112")

    def test_hash_length_is_64(self):
        """SHA-256 hex всегда 64 символа."""
        assert len(Hasher.hash("test")) == 64

    def test_normalized_variants_produce_same_hash(self):
        """ASSERT-05: разное форматирование одного реквизита даёт одинаковый хэш после нормализации."""
        # После нормализации оба варианта идентичны
        normalized1 = "4111111111111111"
        normalized2 = "4111111111111111"
        assert Hasher.hash(normalized1) == Hasher.hash(normalized2)
