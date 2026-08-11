"""
Router for redirect endpoint.
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from src.services.redirect_service import RedirectService
from src.database import DatabasePool

router = APIRouter(tags=["redirect"])


@router.get("/{code}")
async def redirect_to_original(
    code: str,
    request: Request,
):
    """
    Redirect to the original URL based on the short code.
    Records click metadata (IP, User-Agent).
    """
    pool: DatabasePool = request.app.state.db_pool
    conn = await pool.acquire()
    try:
        service = RedirectService(conn)
        original_url = await service.get_original_url_and_log(
            code=code,
            ip_address=request.client.host if request.client and request.client.host else None,
            user_agent=request.headers.get("user-agent"),
        )
        if original_url is None:
            raise HTTPException(status_code=404, detail="Short URL not found")
        # Use 307 Temporary Redirect to preserve method and avoid caching (for accurate stats)
        return RedirectResponse(url=original_url, status_code=307)
    except Exception:
        raise
    finally:
        await pool.release(conn)
