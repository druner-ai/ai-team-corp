from typing import Optional
import aiosqlite
from app.schemas.url import URLResponse, StatsResponse, VisitDetail


class URLRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create_url(self, original_url: str, slug: str) -> URLResponse:
        cursor = await self.db.execute(
            "INSERT INTO urls (original_url, slug) VALUES (?, ?)",
            (original_url, slug)
        )
        await self.db.commit()
        url_id = cursor.lastrowid
        cursor = await self.db.execute("SELECT * FROM urls WHERE id = ?", (url_id,))
        row = await cursor.fetchone()
        return URLResponse(
            id=row["id"],
            slug=row["slug"],
            original_url=row["original_url"],
            created_at=row["created_at"]
        )

    async def get_url_by_slug(self, slug: str) -> Optional[dict]:
        cursor = await self.db.execute("SELECT * FROM urls WHERE slug = ?", (slug,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def increment_visit(self, url_id: int, ip_address: Optional[str] = None):
        await self.db.execute(
            "INSERT INTO visits (url_id, ip_address) VALUES (?, ?)",
            (url_id, ip_address)
        )
        await self.db.commit()

    async def get_stats(self, slug: str) -> Optional[StatsResponse]:
        url = await self.get_url_by_slug(slug)
        if not url:
            return None
        cursor = await self.db.execute(
            "SELECT COUNT(*) as count FROM visits WHERE url_id = ?",
            (url["id"],)
        )
        row = await cursor.fetchone()
        visit_count = row["count"]
        cursor = await self.db.execute(
            "SELECT visited_at, ip_address FROM visits WHERE url_id = ? ORDER BY visited_at DESC",
            (url["id"],)
        )
        visits = [
            VisitDetail(visited_at=row["visited_at"], ip_address=row["ip_address"])
            async for row in cursor
        ]
        return StatsResponse(
            slug=url["slug"],
            original_url=url["original_url"],
            created_at=url["created_at"],
            visit_count=visit_count,
            visits=visits
        )
