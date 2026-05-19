"""
Chat / Q&A API — ask questions about uploaded documents.
No authentication required (dev mode).
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from app.services.chat import ask_question

router = APIRouter(prefix="/chat", tags=["Chat / Q&A"])


# ── Request / Response schemas ────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="The question you want to ask about the uploaded documents",
        example="What are the main topics covered in this document?",
    )


class AskResponse(BaseModel):
    question: str
    answer: Optional[str] = Field(None, description="AI-generated answer")
    sources: List[str] = Field(
        default_factory=list,
        description="Relevant passages from the knowledge base used to generate the answer",
    )
    confidence: float = Field(
        0.0,
        description="Similarity score of the best matching passage (0–1). "
                    "Values below 0.65 mean the answer may be unreliable.",
    )
    error: Optional[str] = Field(
        None,
        description="Set if something went wrong (null on success)",
    )


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about the knowledge base",
    description=(
        "**How to use:**\n\n"
        "1. Upload a document via **POST /documents/upload**\n"
        "2. Wait until **GET /documents/{id}** returns `is_processed == 'completed'`\n"
        "3. Call this endpoint with your question\n\n"
        "The AI will search the indexed document chunks and generate a grounded answer."
    ),
)
async def ask(body: AskRequest) -> AskResponse:
    try:
        result = await ask_question(body.question)
        return AskResponse(
            question=body.question,
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
            error=result["error"],
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {e}",
        )


@router.get(
    "/status",
    summary="Check if the chat service is ready",
    description="Returns whether the embedding service and ChromaDB are configured.",
)
async def chat_status() -> dict:
    """Quick sanity check so you know if the chat service will work."""
    from app.core.config import settings
    from app.services.embeddings import EmbeddingService
    from app.services.chromadb_client import ChromaClient, CHROMADB_AVAILABLE

    embed_ok = False
    embed_provider = "none"
    try:
        svc = EmbeddingService()
        if svc.provider:
            embed_ok = True
            embed_provider = svc.provider
    except Exception:
        pass

    chroma_ok = CHROMADB_AVAILABLE

    return {
        "embedding_service": embed_provider,
        "embedding_ready": embed_ok,
        "chromadb_available": chroma_ok,
        "gemini_key_set": bool(settings.GEMINI_API_KEY),
        "ready_to_chat": embed_ok and chroma_ok,
        "tip": (
            "All systems ready — upload a document and ask away!"
            if (embed_ok and chroma_ok)
            else "Set GEMINI_API_KEY in your .env file and restart the server."
        ),
    }
