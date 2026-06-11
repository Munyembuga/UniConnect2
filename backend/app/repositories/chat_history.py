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
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> ChatHistory:
        chat = ChatHistory(
            user_id=user_id,
            question=question,
            answer=answer,
            sources=sources or [],
            confidence_score=confidence_score,
            is_resolved=is_resolved,
            session_id=session_id,
            category=category,
            response_time_ms=response_time_ms,
        )
        self.db.add(chat)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(chat)
        logger.debug(f"Chat history saved for user {user_id}")
        return chat

    async def get_by_user(self, user_id: UUID, limit: int = 50) -> List[ChatHistory]:
        result = await self.db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all(self, limit: int = 500) -> List[ChatHistory]:
        result = await self.db.execute(
            select(ChatHistory)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
