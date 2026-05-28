"""
Admin API Router — restricted to users with role='admin'.

Endpoints:
  GET  /admin/unresolved-questions          — list pending questions
  POST /admin/unresolved-questions/{id}/answer  — answer a question
  POST /admin/unresolved-questions/{id}/ignore  — dismiss a question
  GET  /admin/chat-history                  — view all chat history
  GET  /admin/users                         — list all registered users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.repositories.unresolved_question import UnresolvedQuestionRepository
from app.repositories.chat_history import ChatHistoryRepository
from app.repositories.user import UserRepository
from app.schemas.admin import (
    UnresolvedQuestionResponse,
    AdminAnswerRequest,
    ChatHistoryResponse,
)
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Unresolved Questions ──────────────────────────────────────────────────────

@router.get(
    "/unresolved-questions",
    response_model=list[UnresolvedQuestionResponse],
    summary="List unresolved questions",
    description=(
        "Returns questions that the AI could not answer confidently. "
        "Use `status=all` to include already-answered and ignored questions."
    ),
)
async def list_unresolved_questions(
    status: str = Query("pending", description="Filter: 'pending', 'answered', 'ignored', or 'all'"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UnresolvedQuestionResponse]:
    repo = UnresolvedQuestionRepository(db)
    if status == "all":
        questions = await repo.list_all()
    else:
        # Filter by the requested status
        from sqlalchemy.future import select
        from app.models.unresolved_question import UnresolvedQuestion
        result = await db.execute(
            select(UnresolvedQuestion)
            .where(UnresolvedQuestion.status == status)
            .order_by(UnresolvedQuestion.created_at.desc())
        )
        questions = result.scalars().all()
    return questions


@router.post(
    "/unresolved-questions/{question_id}/answer",
    response_model=UnresolvedQuestionResponse,
    summary="Answer an unresolved question",
    description=(
        "Provide a manual answer to an unresolved question. "
        "Once answered, the next student who asks a similar question will "
        "automatically receive this answer instead of going through the AI pipeline."
    ),
)
async def answer_question(
    question_id: UUID,
    body: AdminAnswerRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UnresolvedQuestionResponse:
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.answer(question_id, admin.id, body.answer)
    if not uq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unresolved question not found",
        )
    logger.info(f"Admin '{admin.email}' answered question {question_id}")
    return uq


@router.post(
    "/unresolved-questions/{question_id}/ignore",
    response_model=UnresolvedQuestionResponse,
    summary="Ignore an unresolved question",
    description="Mark a question as ignored — it won't appear in the pending list.",
)
async def ignore_question(
    question_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UnresolvedQuestionResponse:
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.ignore(question_id)
    if not uq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unresolved question not found",
        )
    return uq


# ── Chat History ──────────────────────────────────────────────────────────────

@router.get(
    "/chat-history",
    response_model=list[ChatHistoryResponse],
    summary="View all chat history",
    description="Returns the most recent 200 chat exchanges across all users.",
)
async def get_all_chat_history(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ChatHistoryResponse]:
    repo = ChatHistoryRepository(db)
    return await repo.get_all()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all registered users",
)
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    repo = UserRepository(db)
    users = await repo.list_users()
    return [UserResponse.from_orm(u) for u in users]
