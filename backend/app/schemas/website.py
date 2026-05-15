"""
Website source schemas for Pydantic validation.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class WebsiteCreateRequest(BaseModel):
    url: HttpUrl = Field(..., description="Website URL to add as a source")


class WebsiteResponse(BaseModel):
    id: UUID
    url: str
    title: Optional[str]
    description: Optional[str]
    total_chunks: int
    is_processed: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebsiteListResponse(BaseModel):
    id: UUID
    url: str
    title: Optional[str]
    is_processed: str
    total_chunks: int
    created_at: datetime

    class Config:
        from_attributes = True


class WebsiteDeleteResponse(BaseModel):
    success: bool
    message: str
