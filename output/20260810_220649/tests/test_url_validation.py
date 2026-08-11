import pytest
from app.core.url_validator import validate_url

valid_cases = [
    "http://example.com",
    "https://example.com/path?q=1",
    "https://sub.domain.example.com:8080/path",
]

invalid_cases = [
    ("", "URL is required"),
    ("ftp://example.com", "Only HTTP and HTTPS schemes are allowed"),
    ("http://localhost", "URL points to a forbidden address"),
    ("http://127.0.0.1", "URL points to a forbidden address"),
    ("http://0.0.0.0", "URL points to a forbidden address"),
    ("http://10.0.0.1", "URL points to a private or reserved IP address"),
    ("http://192.168.1.1", "URL points to a private or reserved IP address"),
    ("http://[::1]", "URL points to a forbidden address"),
    ("not a url", "Invalid URL format"),
    ("a"*2049 + "https://a.com", "URL exceeds maximum length"),
]

def test_valid_urls():
    for url in valid_cases:
        assert validate_url(url) == url

def test_invalid_urls():
    for url, expected_msg in invalid_cases:
        with pytest.raises(ValueError, match=expected_msg):
            validate_url(url)