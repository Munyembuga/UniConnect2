"""
Chat / Q&A API — ask questions about uploaded documents.
Requires authentication (Bearer token).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from app.db.session import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.services.chat import ask_question

router = APIRouter(prefix="/chat", tags=["Chat / Q&A"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="The question you want to ask about the uploaded documents",
        example="What are the admission requirements?",
    )


class AskResponse(BaseModel):
    question: str
    answer: Optional[str] = Field(None, description="AI-generated or admin-provided answer")
    sources: List[str] = Field(
        default_factory=list,
        description="Relevant passages from the knowledge base",
    )
    confidence: float = Field(0.0, description="Similarity score of the best matching passage (0–1)")
    answered_by: Optional[str] = Field(
        None,
        description="Who answered: 'ai', 'admin', 'static', or 'system'",
    )
    error: Optional[str] = Field(None, description="Error message if something went wrong")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate_sources(sources: List[str], max_chars: int = 180) -> List[str]:
    out = []
    for s in sources:
        s = s.strip()
        out.append(s[:max_chars] + "…" if len(s) > max_chars else s)
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about the knowledge base",
    description=(
        "**Requires authentication.** Send a Bearer token in the Authorization header.\n\n"
        "**How to use:**\n\n"
        "1. Register → `POST /api/v1/auth/register`\n"
        "2. Login → `POST /api/v1/auth/login` (copy the `access_token`)\n"
        "3. Set header: `Authorization: Bearer <access_token>`\n"
        "4. Upload a document via **POST /documents/upload** (admin only)\n"
        "5. Call this endpoint with your question\n\n"
        "If confidence is low the question is automatically flagged for admin review."
    ),
)
async def ask(
    body: AskRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> AskResponse:
    try:
        result = await ask_question(body.question, current_user.id if current_user else None, db)
        return AskResponse(
            question=body.question,
            answer=result["answer"],
            sources=_truncate_sources(result.get("sources", [])),
            confidence=result["confidence"],
            answered_by=result.get("answered_by"),
            error=result["error"],
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {e}",
        )


@router.get(
    "/history",
    summary="Get your chat history",
    description="Returns the last 50 questions you have asked.",
)
async def my_chat_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    from app.repositories.chat_history import ChatHistoryRepository
    repo = ChatHistoryRepository(db)
    history = await repo.get_by_user(current_user.id, limit=50)
    return [
        {
            "id": str(h.id),
            "question": h.question,
            "answer": h.answer,
            "confidence": h.confidence_score,
            "is_resolved": h.is_resolved,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]


@router.get(
    "/status",
    summary="Check if the chat service is ready",
)
async def chat_status() -> dict:
    from app.core.config import settings
    from app.services.embeddings import EmbeddingService
    from app.services.chromadb_client import CHROMADB_AVAILABLE

    embed_ok = False
    embed_provider = "none"
    try:
        svc = EmbeddingService()
        if svc.provider:
            embed_ok = True
            embed_provider = svc.provider
    except Exception:
        pass

    return {
        "embedding_service": embed_provider,
        "embedding_ready": embed_ok,
        "chromadb_available": CHROMADB_AVAILABLE,
        "gemini_key_set": bool(settings.GEMINI_API_KEY),
        "ready_to_chat": embed_ok and CHROMADB_AVAILABLE,
    }
