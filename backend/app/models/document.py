"""
Document model for storing uploaded documents and their metadata.
"""

from datetime import datetime
from uuid import uuid4
from enum import Enum

from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class Document(Base):
    """
    Document model for storing uploaded documents.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: ID of admin who uploaded the document
        filename: Original filename
        document_type: Type of document (PDF, DOCX, TXT)
        file_path: Path where file is stored
        file_size: Size of file in bytes
        content_preview: Preview of document content
        extracted_text: Full extracted text from document
        total_chunks: Number of chunks created from this document
        is_processed: Whether document has been processed and chunked
        created_at: Upload timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(
        SQLEnum(DocumentType, name="documenttype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    content_preview = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    total_chunks = Column(Integer, default=0)
    is_processed = Column(String(50), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    uploaded_by = relationship("User", foreign_keys=[user_id])
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, type={self.document_type})>"
