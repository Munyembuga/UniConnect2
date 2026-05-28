"""
Pydantic schemas for admin endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UnresolvedQuestionResponse(BaseModel):
    id: UUID
    user_id: UUID
    question: str
    ai_attempt: Optional[str] = None
    confidence_score: Optional[float] = None
    status: str
    admin_answer: Optional[str] = None
    answered_by_admin_id: Optional[UUID] = None
    created_at: datetime
    answered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminAnswerRequest(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        description="Admin's answer to the unresolved question",
        example="The registration deadline is January 15th.",
    )


class ChatHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    question: str
    answer: Optional[str] = None
    confidence_score: Optional[float] = None
    is_resolved: str
    created_at: datetime

    class Config:
        from_attributes = True
