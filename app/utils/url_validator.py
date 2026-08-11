"""
URL validation and normalization utilities.

Ensures URLs are valid and safe (http/https only).
"""

import re
from urllib.parse import urlparse, urlunparse


# Allowed URL schemes
ALLOWED_SCHEMES = {"http", "https"}

# Blocked schemes for security
BLOCKED_SCHEMES = {"file", "ftp", "javascript", "data"}

# Maximum URL length (reasonable limit to prevent abuse)
MAX_URL_LENGTH = 2048


def validate_and_normalize_url(url: str) -> str:
    """
    Validate and normalize a URL.

    Checks:
    - Length does not exceed MAX_URL_LENGTH
    - Scheme is http or https (adds https:// if missing)
    - Blocks dangerous schemes (file, ftp, javascript, data)
    - URL has a valid netloc (domain)

    Args:
        url: The URL string to validate.

    Returns:
        Normalized URL string.

    Raises:
        ValueError: If the URL is invalid or uses a blocked scheme.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters")

    # Add scheme if missing
    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)

    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_SCHEMES:
        raise ValueError(f"URL scheme '{scheme}' is not allowed")
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme must be http or https, got '{scheme}'")

    # Must have a valid network location
    if not parsed.netloc:
        raise ValueError("URL must contain a valid domain")

    # Reconstruct normalized URL (lowercase scheme and netloc)
    normalized = urlunparse(
        (
            scheme,
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    return normalized
