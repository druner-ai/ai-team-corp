from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.url import URLCreate, URLResponse
from app.repositories.url_repository import URLRepository
from app.database import get_db
import secrets
import string

router = APIRouter()


def generate_slug(length=6):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def get_url_repository(db=Depends(get_db)) -> URLRepository:
    return URLRepository(db)


@router.post("/urls", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_url(url_data: URLCreate, repo: URLRepository = Depends(get_url_repository)):
    slug = url_data.custom_slug
    if slug:
        existing = await repo.get_url_by_slug(slug)
        if existing:
            raise HTTPException(status_code=400, detail="Slug already taken")
    else:
        while True:
            slug = generate_slug()
            if not await repo.get_url_by_slug(slug):
                break
    return await repo.create_url(str(url_data.url), slug)
