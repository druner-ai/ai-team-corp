"""
Unit tests for base62 encoding/decoding.
"""

import pytest
from app.utils.base62 import encode_base62, decode_base62, BASE62_ALPHABET


class TestBase62Encode:
    """Tests for base62 encoding."""

    def test_encode_zero(self):
        """Zero should encode to '0'."""
        assert encode_base62(0) == "0"

    def test_encode_single_digit(self):
        """Single digits should encode correctly."""
        assert encode_base62(9) == "9"
        assert encode_base62(10) == "a"
        assert encode_base62(35) == "z"
        assert encode_base62(36) == "A"
        assert encode_base62(61) == "Z"

    def test_encode_two_digits(self):
        """Two-digit numbers should encode correctly."""
        assert encode_base62(62) == "10"
        assert encode_base62(123) == "1Z"
        assert encode_base62(3844) == "100"  # 62^2

    def test_encode_large_number(self):
        """Large numbers should encode correctly."""
        # 62^5 = 916132832
        assert encode_base62(916132832) == "100000"

    def test_encode_negative_raises(self):
        """Negative numbers should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            encode_base62(-1)

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding should return the original number."""
        test_numbers = [0, 1, 10, 61, 62, 100, 1000, 999999]
        for num in test_numbers:
            encoded = encode_base62(num)
            decoded = decode_base62(encoded)
            assert decoded == num, f"Failed for {num}: {encoded} -> {decoded}"


class TestBase62Decode:
    """Tests for base62 decoding."""

    def test_decode_zero(self):
        """'0' should decode to 0."""
        assert decode_base62("0") == 0

    def test_decode_single_char(self):
        """Single characters should decode correctly."""
        assert decode_base62("9") == 9
        assert decode_base62("a") == 10
        assert decode_base62("z") == 35
        assert decode_base62("A") == 36
        assert decode_base62("Z") == 61

    def test_decode_two_chars(self):
        """Two-character strings should decode correctly."""
        assert decode_base62("10") == 62
        assert decode_base62("1Z") == 123

    def test_decode_empty_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            decode_base62("")

    def test_decode_invalid_char_raises(self):
        """Invalid characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode_base62("!@#")

    def test_decode_all_valid_chars(self):
        """All base62 characters should be valid."""
        for i, char in enumerate(BASE62_ALPHABET):
            assert decode_base62(char) == i