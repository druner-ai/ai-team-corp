"""
Unit tests for base62 ID generation.
"""
import pytest
from app.utils.id_generator import encode_base62, generate_short_id

def test_encode_base62_zero():
    assert encode_base62(0) == "0"

def test_generate_short_id_length_and_chars():
    from app.utils.id_generator import BASE62_ALPHABET
    id_str = generate_short_id()
    assert len(id_str) == 7
    for ch in id_str:
        assert ch in BASE62_ALPHABET

def test_generate_short_id_uniqueness():
    ids = {generate_short_id() for _ in range(1000)}
    assert len(ids) == 1000