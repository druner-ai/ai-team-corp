"""
Unit tests for URL validation schemas.
"""
import pytest
from pydantic import ValidationError

from src.schemas.url import ShortenRequest


def test_valid_url():
    """Accept standard HTTP/HTTPS URLs."""
    data = ShortenRequest(url="https://example.com/path?query=1")
    assert str(data.url) == "https://example.com/path?query=1"


def test_invalid_url_scheme():
    """Reject non-HTTP schemes."""
    with pytest.raises(ValidationError):
        ShortenRequest(url="ftp://example.com/file")
    with pytest.raises(ValidationError):
        ShortenRequest(url="javascript:alert(1)")


def test_url_too_long():
    """Reject URLs exceeding 2048 characters."""
    long_url = "https://example.com/" + "a" * 2040  # > 2048 total
    with pytest.raises(ValidationError):
        ShortenRequest(url=long_url)


def test_missing_url():
    """Reject missing url field."""
    with pytest.raises(ValidationError):
        ShortenRequest()