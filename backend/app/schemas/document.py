"""
Pydantic schemas for document endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after upload. Pipeline runs in background."""

    id: UUID = Field(..., description="Document ID — use this to poll processing status")
    filename: str
    document_type: DocumentType
    file_size: int = Field(..., description="File size in bytes")
    is_processed: str = Field(
        ...,
        description="Processing status: pending → processing → completed | failed",
    )
    total_chunks: int = Field(..., description="Number of chunks (0 until pipeline completes)")
    created_at: datetime
    text_preview: Optional[str] = Field(
        None,
        description="First 500 chars of extracted text — proves extraction succeeded",
    )
    message: str = Field(
        default="Document uploaded. Processing started in background.",
        description="Human-readable status hint for the frontend",
    )

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
                "created_at": "2026-05-19T10:30:00",
                "message": "Document uploaded. Processing started in background.",
            }
        }


class DocumentListResponse(BaseModel):
    """Compact document entry for list views."""

    id: UUID
    filename: str
    document_type: DocumentType
    file_size: int
    is_processed: str
    total_chunks: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """Full document details including content preview."""

    id: UUID
    filename: str
    document_type: DocumentType
    file_size: int
    content_preview: Optional[str] = Field(None, description="First 500 characters of extracted text")
    is_processed: str
    total_chunks: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDeleteResponse(BaseModel):
    success: bool
    message: str

    class Config:
        json_schema_extra = {"example": {"success": True, "message": "Document deleted successfully"}}
