"""
Custom exceptions and FastAPI exception handlers.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.schemas.common import ErrorResponse


class URLNotFoundError(Exception):
    """Raised when a short code is not found."""
    pass

class URLDeletedError(Exception):
    """Raised when URL has been soft-deleted."""
    pass

class URLExpiredError(Exception):
    """Raised when URL has expired."""
    pass

class ShortCodeGenerationError(Exception):
    """Raised when short code generation fails after retries."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(URLNotFoundError)
    async def url_not_found_exception_handler(request: Request, exc: URLNotFoundError):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                detail="Short URL not found.",
                error_code="not_found",
                status_code=404,
            ).model_dump(),
        )

    @app.exception_handler(URLDeletedError)
    async def url_deleted_exception_handler(request: Request, exc: URLDeletedError):
        return JSONResponse(
            status_code=404,  # Document says 404 for deleted
            content=ErrorResponse(
                detail="Short URL has been deleted.",
                error_code="not_found",
                status_code=404,
            ).model_dump(),
        )

    @app.exception_handler(URLExpiredError)
    async def url_expired_exception_handler(request: Request, exc: URLExpiredError):
        return JSONResponse(
            status_code=410,
            content=ErrorResponse(
                detail="Short URL has expired.",
                error_code="gone",
                status_code=410,
            ).model_dump(),
        )

    @app.exception_handler(ShortCodeGenerationError)
    async def short_code_generation_error_handler(request: Request, exc: ShortCodeGenerationError):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail="Could not generate a unique short code. Try again later.",
                error_code="internal_error",
                status_code=500,
            ).model_dump(),
        )