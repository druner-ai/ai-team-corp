# Исправлено: datetime.utcnow() заменён на datetime.now(datetime.UTC) для timezone-aware объектов

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from app.urls.repository import URLRepository


class URLService:
    def __init__(self, repository: URLRepository):
        self.repository = repository

    @staticmethod
    def generate_short_code(length: int = 6) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def create_short_url(self, original_url: str, custom_code: Optional[str] = None, expires_in_days: Optional[int] = None) -> dict:
        if custom_code:
            existing = await self.repository.get_url(custom_code)
            if existing:
                raise ValueError(f"Custom code '{custom_code}' already exists")
            short_code = custom_code
        else:
            while True:
                short_code = self.generate_short_code()
                existing = await self.repository.get_url(short_code)
                if not existing:
                    break

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now(datetime.UTC) + timedelta(days=expires_in_days)).isoformat().replace("+00:00", "Z")

        return await self.repository.create_url(short_code, original_url, expires_at)

    async def get_original_url(self, short_code: str) -> Optional[str]:
        url_data = await self.repository.get_url(short_code)
        if not url_data:
            return None
        
        if url_data.get("expires_at"):
            expires = datetime.fromisoformat(url_data["expires_at"].replace("Z", "+00:00"))
            if expires < datetime.now(datetime.UTC):
                return None
        
        await self.repository.increment_clicks(short_code)
        return url_data["original_url"]

    async def get_stats(self, short_code: str) -> Optional[dict]:
        return await self.repository.get_stats(short_code)
