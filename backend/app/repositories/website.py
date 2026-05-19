"""
Repository for website_sources table operations.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.models.website_source import WebsiteSource


class WebsiteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_website(
        self,
        user_id: UUID,
        url: str,
        title: str | None = None,
        description: str | None = None,
        content: str | None = None,
    ) -> WebsiteSource:
        ws = WebsiteSource(
            user_id=user_id,
            url=url,
            title=title,
            description=description,
            content=content,
            is_processed="pending",
            total_chunks=0,
        )
        self.db.add(ws)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(ws)
        logger.info(f"Website source created: {url} (id={ws.id})")
        return ws

    async def get_by_id(self, website_id: UUID) -> Optional[WebsiteSource]:
        result = await self.db.execute(
            select(WebsiteSource).where(WebsiteSource.id == website_id)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> Optional[WebsiteSource]:
        result = await self.db.execute(
            select(WebsiteSource).where(WebsiteSource.url == url)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> List[WebsiteSource]:
        result = await self.db.execute(
            select(WebsiteSource)
            .where(WebsiteSource.user_id == user_id)
            .order_by(WebsiteSource.created_at.desc())
        )
        return result.scalars().all()

    async def list_all(self) -> List[WebsiteSource]:
        result = await self.db.execute(
            select(WebsiteSource).order_by(WebsiteSource.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(self, website_id: UUID, status: str) -> Optional[WebsiteSource]:
        """Update only the processing status of a website."""
        ws = await self.get_by_id(website_id)
        if not ws:
            return None
        ws.is_processed = status
        self.db.add(ws)
        await self.db.commit()
        await self.db.refresh(ws)
        logger.info(f"Website {website_id} status → {status}")
        return ws

    async def update_content(
        self,
        website_id: UUID,
        content: str,
        title: str | None = None,
        description: str | None = None,
        total_chunks: int | None = None,
        status: str = "completed",
    ) -> Optional[WebsiteSource]:
        ws = await self.get_by_id(website_id)
        if not ws:
            return None
        ws.content = content
        if title is not None:
            ws.title = title
        if description is not None:
            ws.description = description
        if total_chunks is not None:
            ws.total_chunks = total_chunks
        ws.is_processed = status
        self.db.add(ws)
        await self.db.commit()
        await self.db.refresh(ws)
        logger.info(f"Website source updated: {website_id}")
        return ws

    async def delete(self, website_id: UUID) -> bool:
        ws = await self.get_by_id(website_id)
        if not ws:
            return False
        await self.db.delete(ws)
        await self.db.commit()
        logger.info(f"Website source deleted: {website_id}")
        return True
