"""
Custom exceptions and exception handlers for the URL Shortener service.
"""

from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse


class URLShortenerException(Exception):
    """Base exception for URL Shortener service."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class URLNotFoundException(URLShortenerException):
    """Raised when a short code is not found."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' not found",
            status_code=404,
        )


class URLAlreadyDeletedException(URLShortenerException):
    """Raised when attempting to delete an already deleted URL."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' is already deleted",
            status_code=409,
        )


class URLExpiredException(URLShortenerException):
    """Raised when a URL has expired."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' has expired",
            status_code=410,
        )


class URLAlreadyExistsException(URLShortenerException):
    """Raised when a URL already has a short code."""

    def __init__(self, short_code: str, original_url: str):
        self.short_code = short_code
        self.original_url = original_url
        super().__init__(
            message=f"URL already shortened with code '{short_code}'",
            status_code=409,
        )


class InvalidURLException(URLShortenerException):
    """Raised when the provided URL is invalid."""

    def __init__(self, url: str, reason: str = ""):
        detail = f"Invalid URL: {url}"
        if reason:
            detail += f" - {reason}"
        super().__init__(message=detail, status_code=400)


class ServiceUnavailableException(URLShortenerException):
    """Raised when a required service (DB, Redis) is unavailable."""

    def __init__(self, service: str):
        super().__init__(
            message=f"Service unavailable: {service} is not accessible",
            status_code=503,
        )


async def url_shortener_exception_handler(
    request: Request, exc: URLShortenerException
) -> JSONResponse:
    """Global exception handler for URLShortenerException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Global exception handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )