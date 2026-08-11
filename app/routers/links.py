from fastapi import APIRouter, Depends, HTTPException, Request
from app.schemas import LinkCreate, LinkResponse
from app.services.link_service import LinkService
from app.dependencies import get_link_service, get_rate_limiter
from app.utils import RateLimiter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/links", response_model=LinkResponse, status_code=201)
async def create_link(
    request: Request,
    link_data: LinkCreate,
    service: LinkService = Depends(get_link_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    # Rate limiting: 10 requests per minute per IP
    client_ip = request.client.host
    if not rate_limiter.is_allowed(f"create:{client_ip}", limit=10, window=60):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    try:
        return await service.create_link(str(link_data.url), link_data.custom_slug)
    except ValueError as e:
        logger.warning(f"ValueError in create_link: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"RuntimeError in create_link: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
