"""
Custom application exceptions.
"""


class URLShortenerException(Exception):
    """Base exception for the application."""
    pass


class ShortIDCollisionError(URLShortenerException):
    """Raised when short_id generation fails after maximum retries."""
    pass


class URLNotFoundError(URLShortenerException):
    """Raised when a URL entry is not found or deleted."""
    pass


class RateLimitExceededError(URLShortenerException):
    """Raised when rate limit is exceeded. Middleware handles this."""
    pass