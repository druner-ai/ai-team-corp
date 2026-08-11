"""
Security utilities: URL validation and SSRF protection.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings


# Private IP ranges to block (SSRF protection)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
]

# Blocked hostnames
BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0"}


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private IP address.

    Args:
        hostname: The hostname to check.

    Returns:
        True if the hostname resolves to a private IP, False otherwise.
    """
    if not settings.block_private_ips:
        return False

    # Check if hostname is in blocked list
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return True

    try:
        # Try to parse as IP address first
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        # Not an IP address, try DNS resolution
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved_ip)
            return any(ip in network for network in PRIVATE_IP_RANGES)
        except (socket.gaierror, ValueError):
            # If we can't resolve, assume it's safe
            # Note: This could be a potential bypass, but blocking unresolvable
            # hosts would break legitimate use cases
            return False


def validate_url(url: str) -> str:
    """
    Validate a URL for safety and correctness.

    Checks:
    - Scheme is http or https
    - URL has a valid netloc (domain)
    - URL length is within limits (2048 chars)
    - Host does not resolve to private IP (if BLOCK_PRIVATE_IPS is enabled)

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string.

    Raises:
        InvalidURLException: If the URL fails validation.
    """
    from app.core.exceptions import InvalidURLException

    # Check length
    if len(url) > 2048:
        raise InvalidURLException(url, "URL exceeds maximum length of 2048 characters")

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise InvalidURLException(url, "Could not parse URL")

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLException(url, "Only http and https schemes are allowed")

    # Check netloc (domain)
    if not parsed.netloc:
        raise InvalidURLException(url, "URL must have a valid domain")

    # Extract hostname (remove port if present)
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLException(url, "Could not extract hostname from URL")

    # Check for private IPs
    if is_private_ip(hostname):
        raise InvalidURLException(url, "URL resolves to a private/internal IP address")

    return url