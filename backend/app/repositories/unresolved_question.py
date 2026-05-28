"""
Repository for UnresolvedQuestion database operations.

Flow:
  1. Chat service saves low-confidence questions here (status='pending').
  2. Admin views pending questions and provides answers (status='answered').
  3. Before next RAG call, chat service checks for similar answered questions
     and returns the admin answer directly.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from loguru import logger

from app.models.unresolved_question import UnresolvedQuestion


class UnresolvedQuestionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        chat_history_id: UUID,
        user_id: UUID,
        question: str,
        ai_attempt: Optional[str],
        confidence_score: Optional[float],
    ) -> UnresolvedQuestion:
        """Save a new unresolved question."""
        uq = UnresolvedQuestion(
            chat_history_id=chat_history_id,
            user_id=user_id,
            question=question,
            ai_attempt=ai_attempt,
            confidence_score=confidence_score,
            status="pending",
        )
        self.db.add(uq)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(uq)
        logger.info(f"Unresolved question flagged: '{question[:60]}'")
        return uq

    async def find_answered_similar(self, question: str) -> Optional[UnresolvedQuestion]:
        """
        Search admin-answered questions for one similar to the given question.
        Uses PostgreSQL full-text search (plainto_tsquery) for matching.
        Returns the most recently answered match, or None.
        """
        try:
            fts_query = func.plainto_tsquery("english", question)
            stmt = (
                select(UnresolvedQuestion)
                .where(
                    UnresolvedQuestion.status == "answered",
                    func.to_tsvector("english", UnresolvedQuestion.question).op("@@")(fts_query),
                )
                .order_by(UnresolvedQuestion.answered_at.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            match = result.scalar_one_or_none()
            if match:
                logger.info(f"Found admin-answered match for: '{question[:60]}'")
            return match
        except Exception as e:
            logger.warning(f"Similar-question search failed: {e}")
            return None

    async def list_pending(self) -> List[UnresolvedQuestion]:
        """Return all questions waiting for an admin answer."""
        result = await self.db.execute(
            select(UnresolvedQuestion)
            .where(UnresolvedQuestion.status == "pending")
            .order_by(UnresolvedQuestion.created_at.desc())
        )
        return result.scalars().all()

    async def list_all(self) -> List[UnresolvedQuestion]:
        """Return all unresolved questions (any status)."""
        result = await self.db.execute(
            select(UnresolvedQuestion)
            .order_by(UnresolvedQuestion.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, uq_id: UUID) -> Optional[UnresolvedQuestion]:
        result = await self.db.execute(
            select(UnresolvedQuestion).where(UnresolvedQuestion.id == uq_id)
        )
        return result.scalar_one_or_none()

    async def answer(
        self,
        uq_id: UUID,
        admin_id: UUID,
        admin_answer: str,
    ) -> Optional[UnresolvedQuestion]:
        """Admin provides the answer for an unresolved question."""
        uq = await self.get_by_id(uq_id)
        if not uq:
            return None
        uq.admin_answer = admin_answer
        uq.answered_by_admin_id = admin_id
        uq.status = "answered"
        uq.answered_at = datetime.utcnow()
        self.db.add(uq)
        await self.db.commit()
        await self.db.refresh(uq)
        logger.info(f"Admin {admin_id} answered question {uq_id}")
        return uq

    async def ignore(self, uq_id: UUID) -> Optional[UnresolvedQuestion]:
        """Mark a question as ignored (not worth answering)."""
        uq = await self.get_by_id(uq_id)
        if not uq:
            return None
        uq.status = "ignored"
        self.db.add(uq)
        await self.db.commit()
        await self.db.refresh(uq)
        return uq
