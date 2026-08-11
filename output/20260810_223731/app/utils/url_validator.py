"""
Custom URL validation beyond what pydantic HttpUrl provides.
(Could be extended for SSRF protection, private IP blocking, etc.)
"""

import ipaddress
from urllib.parse import urlparse

PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1"),
    ipaddress.ip_network("fc00::/7"),
]


def is_private_url(url: str) -> bool:
    """
    Check if the URL points to a private/reserved IP address.
    This is an optional SSRF protection – not used by default.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # Hostname might not be an IP; could resolve DNS (not done here)
        return False
    return any(ip in network for network in PRIVATE_IP_RANGES)