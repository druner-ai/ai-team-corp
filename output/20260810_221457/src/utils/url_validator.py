"""
    URL validation with anti-SSRF checks.
"""
import ipaddress
from urllib.parse import urlparse
from fastapi import HTTPException, status
from src.config import settings

MAX_URL_LENGTH = 2048

def validate_url(url: str) -> str:
    if not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must be a string")
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"URL exceeds {MAX_URL_LENGTH} characters")
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL format")
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must have scheme and host")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only HTTP/HTTPS allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hostname")
    # SSRF protection: block private/local addresses
    blocked = settings.blocked_hosts_list
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private IP not allowed")
        # If it's an IP, also check blocked list for exact match or network
        for block in blocked:
            # block could be an IP or network prefix; we only handle simple cases
            if block == hostname or ('.' in block and hostname.startswith(block)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Blocked host")
    except ValueError:
        # Not an IP – domain name; check exact match
        for block in blocked:
            if hostname == block:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Blocked host")
    return url