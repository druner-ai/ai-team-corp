"""
URL validation utilities including SSRF protection.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional


# Private/internal IP ranges that should be blocked for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),       # Current network
]


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private/internal IP address.
    
    Args:
        hostname: Hostname or IP address to check
        
    Returns:
        bool: True if the IP is private/internal, False otherwise
        
    Note:
        This is a basic SSRF protection. In production, consider using
        a dedicated library or external service for more comprehensive protection.
    """
    try:
        # Try to parse as IP address first
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP, try DNS resolution
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        except (socket.gaierror, ValueError):
            # Cannot resolve, allow it (will fail at connection time)
            return False
    
    # Check against private ranges
    for private_range in PRIVATE_IP_RANGES:
        if ip in private_range:
            return True
    
    return False


def validate_url_safety(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL safety including SSRF protection.
    
    Args:
        url: The URL to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_safe, error_message)
        - is_safe: True if URL is safe to use
        - error_message: Error description if not safe, None otherwise
        
    Note:
        This performs additional safety checks beyond basic URL validation.
        Currently checks for private IP access (SSRF protection).
        Can be extended with additional checks as needed.
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"URL scheme '{parsed.scheme}' is not allowed"
        
        # Check for hostname
        if not parsed.hostname:
            return False, "URL has no valid hostname"
        
        # SSRF check: block private IPs
        if is_private_ip(parsed.hostname):
            return False, f"Access to private IP '{parsed.hostname}' is not allowed"
        
        return True, None
        
    except Exception as e:
        return False, f"URL validation failed: {str(e)}"