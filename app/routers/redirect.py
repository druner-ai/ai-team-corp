from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.services.link_service import LinkService
from app.dependencies import get_link_service, get_rate_limiter
from app.utils import RateLimiter, mask_ip
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{slug}")
async def redirect(
    slug: str,
    request: Request,
    service: LinkService = Depends(get_link_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    # Rate limiting: 100 requests per minute per IP
    client_ip = request.client.host
    if not rate_limiter.is_allowed(f"redirect:{client_ip}", limit=100, window=60):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    original_url = await service.resolve_link(slug)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short link not found")

    # Record click (synchronous await is acceptable for SQLite)
    ip = request.headers.get("X-Forwarded-For", client_ip)
    user_agent = request.headers.get("User-Agent")
    masked_ip = mask_ip(ip)
    logger.info(f"Redirect: slug={slug}, ip={masked_ip}")
    await service.record_click(slug, ip, user_agent)

    return RedirectResponse(url=original_url, status_code=302)
