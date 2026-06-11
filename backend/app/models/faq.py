from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class FAQ(Base):
    __tablename__ = "faqs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    question   = Column(Text, nullable=False)
    answer     = Column(Text, nullable=False)
    category   = Column(String(100), nullable=True, default="General")
    status     = Column(String(20), default="active")   # active | draft | archived
    view_count = Column(Integer, default=0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
