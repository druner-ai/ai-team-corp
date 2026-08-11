"""
URL validation with SSRF protection.
Only allows http/https schemes, rejects localhost and private IPs.
"""
import ipaddress
import re
from urllib.parse import urlparse

# List of blacklisted hostnames (case-insensitive)
BLACKLISTED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",  # IPv6 loopback
}


def validate_url(url: str) -> str:
    """
    Validate and sanitize a URL.
    Raises ValueError if invalid.
    """
    if not url:
        raise ValueError("URL is required")
    if len(url) > 2048:
        raise ValueError("URL exceeds maximum length of 2048 characters")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL format")
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid hostname")

    # Check blacklist
    if hostname.lower() in BLACKLISTED_HOSTNAMES:
        raise ValueError("URL points to a forbidden address")

    # Check if hostname is an IP address in private/loopback ranges
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP, skip address validation
        pass
    else:
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError("URL points to a private or reserved IP address")

    return url