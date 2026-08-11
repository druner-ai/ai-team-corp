"""
Unit tests for URL validation and security checks.
"""

import pytest
from app.core.security import validate_url, is_private_ip
from app.core.exceptions import InvalidURLException


class TestValidateURL:
    """Tests for URL validation."""

    def test_valid_https_url(self):
        """Valid HTTPS URL should pass validation."""
        result = validate_url("https://example.com/path")
        assert result == "https://example.com/path"

    def test_valid_http_url(self):
        """Valid HTTP URL should pass validation."""
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_url_with_query_params(self):
        """URL with query parameters should pass."""
        result = validate_url("https://example.com/path?key=value&foo=bar")
        assert "?key=value&foo=bar" in result

    def test_url_with_fragment(self):
        """URL with fragment should pass."""
        result = validate_url("https://example.com/page#section")
        assert "#section" in result

    def test_invalid_scheme_ftp(self):
        """FTP scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("ftp://example.com")

    def test_invalid_scheme_javascript(self):
        """javascript: scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("javascript:alert(1)")

    def test_no_scheme(self):
        """URL without scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("example.com")

    def test_empty_url(self):
        """Empty URL should be rejected."""
        with pytest.raises(InvalidURLException):
            validate_url("")

    def test_url_too_long(self):
        """URL exceeding 2048 characters should be rejected."""
        long_url = "https://example.com/" + "a" * 2040
        with pytest.raises(InvalidURLException, match="exceeds maximum length"):
            validate_url(long_url)

    def test_url_max_length(self):
        """URL at exactly 2048 characters should pass."""
        url = "https://example.com/" + "a" * 2020
        # Should be exactly 2048 chars
        assert len(url) == 2048
        result = validate_url(url)
        assert result == url

    def test_malformed_url(self):
        """Malformed URL should be rejected."""
        with pytest.raises(InvalidURLException):
            validate_url("not a url at all!!!")

    def test_url_without_host(self):
        """URL without host should be rejected."""
        with pytest.raises(InvalidURLException, match="valid domain"):
            validate_url("https://")


class TestPrivateIPBlocking:
    """Tests for private IP blocking (SSRF protection)."""

    def test_localhost_blocked(self):
        """localhost should be blocked."""
        assert is_private_ip("localhost") is True

    def test_loopback_ip_blocked(self):
        """127.0.0.1 should be blocked."""
        assert is_private_ip("127.0.0.1") is True

    def test_private_ip_blocked(self):
        """Private IP ranges should be blocked."""
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True

    def test_public_ip_allowed(self):
        """Public IP should be allowed."""
        # Note: This test might fail if DNS resolution is not available
        # In CI/CD, we should mock DNS resolution
        assert is_private_ip("8.8.8.8") is False

    def test_zero_ip_blocked(self):
        """0.0.0.0 should be blocked."""
        assert is_private_ip("0.0.0.0") is True

    def test_link_local_blocked(self):
        """169.254.x.x should be blocked."""
        assert is_private_ip("169.254.1.1") is True