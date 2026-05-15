"""
File upload schemas for document handling.
Pydantic models for file upload requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    
    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    document_type: DocumentType = Field(..., description="Document type")
    file_size: int = Field(..., description="File size in bytes")
    is_processed: str = Field(..., description="Processing status")
    total_chunks: int = Field(..., description="Number of chunks created")
    created_at: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "course_notes.pdf",
                "document_type": "pdf",
                "file_size": 2048576,
                "is_processed": "pending",
                "total_chunks": 0,
                "created_at": "2026-05-14T10:30:00+00:00",
            }
        }


class DocumentListResponse(BaseModel):
    """Response model for document list."""
    
    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    document_type: DocumentType = Field(..., description="Document type")
    file_size: int = Field(..., description="File size in bytes")
    is_processed: str = Field(..., description="Processing status")
    total_chunks: int = Field(..., description="Number of chunks")
    created_at: datetime = Field(..., description="Upload timestamp")
    
    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """Detailed document response."""
    
    id: UUID = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    document_type: DocumentType = Field(..., description="Document type")
    file_size: int = Field(..., description="File size in bytes")
    content_preview: Optional[str] = Field(None, description="Content preview (first 500 chars)")
    is_processed: str = Field(..., description="Processing status")
    total_chunks: int = Field(..., description="Number of chunks")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""
    
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Document deleted successfully",
            }
        }
