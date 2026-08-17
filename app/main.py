from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.routers import card, iban, account
from app.api.schemas.common import ErrorResponse, ErrorItem
from app.utils.logging_filter import MaskingFilter
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Add masking filter to all handlers
for handler in logging.root.handlers:
    handler.addFilter(MaskingFilter())

app = FastAPI()

# Include routers
app.include_router(card.router)
app.include_router(iban.router)
app.include_router(account.router)

# Exception handler for validation errors (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed"
            },
            "detail": errors
        }
    )

# Catch-all route for 404
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(request: Request, path: str):
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "ROUTE_NOT_FOUND",
                "message": f"Route '{request.method} {request.url.path}' not found"
            }
        }
    )

# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response
