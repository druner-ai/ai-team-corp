"""
Unit tests for short_id generator.
"""
from src.utils.short_id import generate_short_id, SHORT_ID_LENGTH, BASE62_ALPHABET


def test_generate_short_id_length():
    """Generated ID must have exactly 7 characters."""
    sid = generate_short_id()
    assert len(sid) == SHORT_ID_LENGTH


def test_generate_short_id_characters():
    """All characters must be from the base62 alphabet."""
    for _ in range(100):
        sid = generate_short_id()
        for ch in sid:
            assert ch in BASE62_ALPHABET


def test_generate_short_id_uniqueness():
    """Generate many IDs and ensure no duplicates appear."""
    ids = set()
    for _ in range(1000):
        sid = generate_short_id()
        assert sid not in ids
        ids.add(sid)