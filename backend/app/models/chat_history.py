"""
ChatHistory model for storing conversation history between students and the AI chatbot.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id       = Column(String(100), nullable=True, index=True)
    question         = Column(Text, nullable=False)
    answer           = Column(Text, nullable=True)
    sources          = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    category         = Column(String(100), nullable=True, index=True)
    response_time_ms = Column(Integer, nullable=True)
    is_resolved      = Column(String(50), default="pending", index=True)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<ChatHistory(id={self.id}, user_id={self.user_id}, resolved={self.is_resolved})>"
