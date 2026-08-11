"""
Router for URL shortening endpoint.
"""
from fastapi import APIRouter, Request, status
from src.models.url import ShortenRequest, ShortenResponse
from src.services.url_service import UrlService
from src.database import DatabasePool

router = APIRouter(prefix="/api", tags=["shorten"])


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    body: ShortenRequest,
    request: Request,
):
    """
    Create a short URL from a long URL.
    """
    pool: DatabasePool = request.app.state.db_pool
    conn = await pool.acquire()
    try:
        service = UrlService(conn)
        result = await service.create_short_url(str(body.url))
        return result
    except Exception:
        # Re-raise to let FastAPI handle the exception, but ensure connection release
        raise
    finally:
        await pool.release(conn)
