"""
Pydantic-модели для валидации запросов и ответов API.
"""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class URLCreateRequest(BaseModel):
    """Запрос на создание короткой ссылки."""

    url: HttpUrl


class URLCreateResponse(BaseModel):
    """Ответ с созданной короткой ссылкой."""

    short_url: str
    short_code: str
    original_url: str


class URLStatsResponse(BaseModel):
    """Ответ со статистикой по ссылке."""

    short_code: str
    original_url: str
    created_at: datetime
    last_accessed_at: datetime | None
    access_count: int
