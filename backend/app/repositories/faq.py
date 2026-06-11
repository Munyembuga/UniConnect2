from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.models.faq import FAQ


class FAQRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, status: Optional[str] = None) -> list[FAQ]:
        try:
            q = select(FAQ).order_by(FAQ.created_at.desc())
            if status:
                q = q.where(FAQ.status == status)
            result = await self.db.execute(q)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error listing FAQs: {e}")
            return []

    async def get_by_id(self, faq_id: UUID) -> Optional[FAQ]:
        try:
            result = await self.db.execute(select(FAQ).where(FAQ.id == faq_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting FAQ {faq_id}: {e}")
            return None

    async def create(self, question: str, answer: str, category: str,
                     status: str, created_by: Optional[UUID] = None) -> FAQ:
        faq = FAQ(question=question, answer=answer, category=category,
                  status=status, created_by=created_by)
        self.db.add(faq)
        await self.db.commit()
        await self.db.refresh(faq)
        return faq

    async def update(self, faq_id: UUID, **kwargs) -> Optional[FAQ]:
        faq = await self.get_by_id(faq_id)
        if not faq:
            return None
        for k, v in kwargs.items():
            if hasattr(faq, k):
                setattr(faq, k, v)
        await self.db.commit()
        await self.db.refresh(faq)
        return faq

    async def delete(self, faq_id: UUID) -> bool:
        faq = await self.get_by_id(faq_id)
        if not faq:
            return False
        await self.db.delete(faq)
        await self.db.commit()
        return True

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(FAQ).where(FAQ.status == "active")
        )
        return result.scalar() or 0
