"""
WebsiteSource model for storing website URLs added for training the chatbot.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class WebsiteSource(Base):
    """
    WebsiteSource model for storing website URLs for training.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: ID of admin who added the source
        url: Website URL
        title: Website title
        description: Website description
        content: Extracted text content from website
        total_chunks: Number of chunks created from content
        is_processed: Whether website has been scraped and processed
        created_at: When URL was added
        updated_at: Last update timestamp
    """
    
    __tablename__ = "website_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    total_chunks = Column(Integer, default=0)
    is_processed = Column(String(50), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    added_by = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<WebsiteSource(id={self.id}, url={self.url})>"
