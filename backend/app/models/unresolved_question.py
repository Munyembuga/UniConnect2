"""
UnresolvedQuestion model for storing questions that the AI couldn't answer satisfactorily.
Admins can manually answer these, and the system learns from them.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UnresolvedQuestion(Base):
    """
    UnresolvedQuestion model for storing low-confidence questions.
    
    Attributes:
        id: Unique identifier (UUID)
        chat_history_id: ID of related chat history
        user_id: ID of student asking the question
        question: The question that couldn't be resolved
        ai_attempt: Initial AI attempt
        confidence_score: Low confidence score of AI answer
        status: Status of resolution (pending, answered, ignored)
        admin_answer: Manual answer provided by admin (if any)
        answered_by_admin_id: ID of admin who answered
        created_at: Timestamp of unresolved question
        answered_at: Timestamp when admin answered
        updated_at: Last update timestamp
    """
    
    __tablename__ = "unresolved_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    chat_history_id = Column(UUID(as_uuid=True), ForeignKey("chat_history.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    ai_attempt = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    status = Column(String(50), default="pending")  # pending, answered, ignored
    admin_answer = Column(Text, nullable=True)
    answered_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    answered_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[answered_by_admin_id])

    def __repr__(self) -> str:
        return f"<UnresolvedQuestion(id={self.id}, status={self.status})>"
