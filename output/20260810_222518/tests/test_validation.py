"""
Tests for URL validation utilities.
"""
import pytest
from app.utils.url_validator import validate_url_safety, is_private_ip
from app.utils.short_id import generate_short_id, validate_short_id


class TestUrlSafety:
    """Tests for URL safety validation."""
    
    def test_valid_http_url(self):
        """Test that valid HTTP URL passes validation."""
        is_safe, error = validate_url_safety("http://example.com")
        assert is_safe is True
        assert error is None
    
    def test_valid_https_url(self):
        """Test that valid HTTPS URL passes validation."""
        is_safe, error = validate_url_safety("https://example.com/path?query=1")
        assert is_safe is True
        assert error is None
    
    def test_invalid_scheme_ftp(self):
        """Test that FTP URL is rejected."""
        is_safe, error = validate_url_safety("ftp://example.com/file")
        assert is_safe is False
        assert error is not None
    
    def test_invalid_scheme_javascript(self):
        """Test that javascript: URL is rejected."""
        is_safe, error = validate_url_safety("javascript:alert('xss')")
        assert is_safe is False
        assert error is not None
    
    def test_private_ip_blocked(self):
        """Test that private IP addresses are blocked (SSRF protection)."""
        is_safe, error = validate_url_safety("http://127.0.0.1/admin")
        assert is_safe is False
        assert "private IP" in error.lower() if error else False
    
    def test_localhost_blocked(self):
        """Test that localhost is blocked."""
        is_safe, error = validate_url_safety("http://localhost:8080")
        assert is_safe is False
        assert error is not None


class TestShortIdGeneration:
    """Tests for short ID generation and validation."""
    
    def test_generate_short_id_length(self):
        """Test that generated short ID has correct length."""
        short_id = generate_short_id(7)
        assert len(short_id) == 7
    
    def test_generate_short_id_alphanumeric(self):
        """Test that generated short ID contains only alphanumeric chars."""
        short_id = generate_short_id(7)
        assert short_id.isalnum()
    
    def test_generate_short_id_uniqueness(self):
        """Test that generated short IDs are unique."""
        ids = {generate_short_id(7) for _ in range(100)}
        assert len(ids) == 100  # All should be unique
    
    def test_validate_short_id_valid(self):
        """Test validation of valid short ID."""
        assert validate_short_id("abc1234", 7) is True
    
    def test_validate_short_id_invalid_length(self):
        """Test validation of short ID with wrong length."""
        assert validate_short_id("abc12", 7) is False
    
    def test_validate_short_id_invalid_chars(self):
        """Test validation of short ID with invalid characters."""
        assert validate_short_id("abc-123", 7) is False
    
    def test_validate_short_id_empty(self):
        """Test validation of empty short ID."""
        assert validate_short_id("", 7) is False