"""
DocumentChunk model for storing text chunks extracted from documents.
These chunks are used for embedding and RAG.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentChunk(Base):
    """
    DocumentChunk model for storing text chunks from documents.
    
    Attributes:
        id: Unique identifier (UUID)
        document_id: ID of source document
        chunk_index: Index of chunk within document
        content: Text content of chunk
        embedding: Vector embedding (stored as JSON in ChromaDB, this is just metadata)
        chunk_hash: Hash of chunk content for deduplication
        created_at: Creation timestamp
    """
    
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(String(500), nullable=True)  # Placeholder for embedding ID from ChromaDB
    chunk_hash = Column(String(64), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", foreign_keys=[document_id], back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"
