"""
URL validation utilities, especially SSRF protection.
"""
from urllib.parse import urlparse
import ipaddress
import socket

# Private and reserved IP ranges to block
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),   # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local addresses
    ipaddress.ip_network("fe80::/10"), # IPv6 link-local
]

BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}

def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP string is in the blocked ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in BLOCKED_IP_NETWORKS)

def validate_url_no_ssrf(url: str) -> None:
    """
    Validate that a URL does not point to local/private resources.
    Raises ValueError if the host is a blocked IP or hostname.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL")
    # Check if it's a blocked hostname
    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"URL points to forbidden hostname: {hostname}")
    # Try to resolve hostname to IP and check
    try:
        ip = socket.getaddrinfo(hostname, None)[0][4][0]
    except (socket.gaierror, IndexError):
        # If resolution fails, allow (or block? We'll allow for now)
        # In production, you might want to block unresolved hosts or use a stricter approach.
        return
    if is_ip_blocked(ip):
        raise ValueError(f"URL resolves to a blocked IP address: {ip}")
    # Also check if the direct hostname is already an IP (e.g., http://127.0.0.1)
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if is_ip_blocked(hostname):
            raise ValueError(f"URL contains a blocked IP address: {hostname}")