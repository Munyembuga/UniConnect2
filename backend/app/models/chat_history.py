"""
ChatHistory model for storing conversation history between students and the AI chatbot.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChatHistory(Base):
    """
    ChatHistory model for storing chat conversations.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: ID of student asking the question
        question: Student's question
        answer: AI-generated answer
        sources: List of document chunks used for generating answer
        confidence_score: Confidence score of answer (0-1)
        is_resolved: Whether question was resolved
        created_at: Timestamp of question
        updated_at: Last update timestamp
    """
    
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)  # List of source chunk IDs
    confidence_score = Column(Float, nullable=True)  # 0-1
    is_resolved = Column(String(50), default="pending")  # pending, resolved, unresolved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, resolved={self.is_resolved})>"
