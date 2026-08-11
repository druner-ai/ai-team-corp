"""
Unit tests for URL validation utilities.
"""
import pytest
from app.utils.url_validator import is_private_url


def test_private_ip_url():
    assert is_private_url("http://127.0.0.1:8080") is True
    assert is_private_url("http://10.0.0.1") is True
    assert is_private_url("https://192.168.1.1") is True


def test_public_url():
    assert is_private_url("https://example.com") is False
    assert is_private_url("http://8.8.8.8") is False


def test_hostname_url():
    # Not an IP, so not private
    assert is_private_url("https://myprivate.local") is False