"""
Repository for ChatHistory database operations.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.models.chat_history import ChatHistory


class ChatHistoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: UUID,
        question: str,
        answer: Optional[str],
        sources: Optional[list],
        confidence_score: Optional[float],
        is_resolved: str = "resolved",
    ) -> ChatHistory:
        """Save a new chat exchange to the database."""
        chat = ChatHistory(
            user_id=user_id,
            question=question,
            answer=answer,
            sources=sources or [],
            confidence_score=confidence_score,
            is_resolved=is_resolved,
        )
        self.db.add(chat)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(chat)
        logger.debug(f"Chat history saved for user {user_id}")
        return chat

    async def get_by_user(self, user_id: UUID, limit: int = 50) -> List[ChatHistory]:
        """Return recent chat history for a specific user."""
        result = await self.db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all(self, limit: int = 200) -> List[ChatHistory]:
        """Return all chat history (admin view)."""
        result = await self.db.execute(
            select(ChatHistory)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
