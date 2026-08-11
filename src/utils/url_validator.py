"""
Custom URL validation utilities.

Provides validation functions for ensuring URLs use allowed schemes
and are well-formed.
"""

from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def validate_url(url: str) -> str:
    """
    Validate that a URL uses an allowed scheme (http or https).

    Args:
        url: The URL string to validate.

    Returns:
        The validated URL string.

    Raises:
        ValueError: If the URL scheme is not http or https, or if the URL
                    is malformed.
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}") from e

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme must be one of {ALLOWED_SCHEMES}, got '{parsed.scheme}'"
        )

    if not parsed.netloc:
        raise ValueError("URL must contain a valid hostname")

    return url
