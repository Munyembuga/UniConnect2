"""
Admin API Router — restricted to users with role='admin'.
"""
import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.db.session import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.chat_history import ChatHistory
from app.models.document import Document
from app.models.unresolved_question import UnresolvedQuestion
from app.repositories.unresolved_question import UnresolvedQuestionRepository
from app.repositories.chat_history import ChatHistoryRepository
from app.repositories.user import UserRepository
from app.repositories.faq import FAQRepository
from app.repositories.settings import SettingsRepository
from app.schemas.admin import (
    UnresolvedQuestionResponse,
    AdminAnswerRequest,
    ChatHistoryResponse,
)
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "Admissions":     ["admission", "apply", "application", "entry", "requirement", "enroll", "join", "intake"],
    "Registration":   ["register", "registration", "semester", "course select", "add course", "drop course", "enrol"],
    "Scholarships":   ["scholarship", "bursary", "funding", "grant", "financial aid", "sponsorship", "award"],
    "Fees":           ["fee", "payment", "tuition", "cost", "pay", "invoice", "bill", "money"],
    "Programs":       ["program", "course", "department", "faculty", "degree", "bachelor", "master", "phd", "diploma", "study"],
    "Exams":          ["exam", "test", "quiz", "grade", "score", "result", "mark", "assessment", "continuous assessment"],
    "Accommodation":  ["hostel", "accommodation", "housing", "dormitory", "residence", "room"],
    "Campus Life":    ["campus", "library", "facility", "laboratory", "clinic", "health", "sports", "cafeteria", "internet", "wifi"],
    "Administration": ["transcript", "certificate", "document", "letter", "form", "request", "office", "administration", "record"],
}

_CATEGORY_COLORS = {
    "Admissions":     "#00628b",
    "Registration":   "#30a1c6",
    "Scholarships":   "#364f68",
    "Fees":           "#e8a800",
    "Programs":       "#0891b2",
    "Exams":          "#7c3aed",
    "Accommodation":  "#db2777",
    "Campus Life":    "#059669",
    "Administration": "#9ca3af",
    "General":        "#64748b",
    "Other":          "#6b7280",
}


def _categorize(question: str) -> str:
    q = question.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return category
    return "Other"


# ─────────────────────────────────────────────────────────────────────────────
# Stats — Dashboard KPI cards
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="Dashboard KPI statistics")
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    today    = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    total_users     = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    student_count   = (await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.STUDENT)
    )).scalar() or 0
    active_users    = (await db.execute(
        select(func.count(func.distinct(ChatHistory.user_id))).where(ChatHistory.created_at >= month_ago)
    )).scalar() or 0
    total_queries   = (await db.execute(select(func.count()).select_from(ChatHistory))).scalar() or 0
    queries_today   = (await db.execute(
        select(func.count()).select_from(ChatHistory).where(func.date(ChatHistory.created_at) == today)
    )).scalar() or 0
    queries_week    = (await db.execute(
        select(func.count()).select_from(ChatHistory).where(ChatHistory.created_at >= week_ago)
    )).scalar() or 0
    answered        = (await db.execute(
        select(func.count()).select_from(ChatHistory).where(ChatHistory.is_resolved == "resolved")
    )).scalar() or 0
    pending_uq      = (await db.execute(
        select(func.count()).select_from(UnresolvedQuestion).where(UnresolvedQuestion.status == "pending")
    )).scalar() or 0
    total_docs      = (await db.execute(select(func.count()).select_from(Document))).scalar() or 0
    processed_docs  = (await db.execute(
        select(func.count()).select_from(Document).where(Document.is_processed == "completed")
    )).scalar() or 0
    faq_count       = await FAQRepository(db).count()

    # Average response time (ms) — only for rows that have it recorded
    avg_rt_result = (await db.execute(
        select(func.avg(ChatHistory.response_time_ms)).where(ChatHistory.response_time_ms.isnot(None))
    )).scalar()
    avg_response_time_ms = round(avg_rt_result) if avg_rt_result else None

    answer_rate = round(answered / total_queries, 3) if total_queries else 0.0

    return {
        "total_users":            total_users,
        "student_count":          student_count,
        "active_users":           active_users,
        "total_queries":          total_queries,
        "queries_today":          queries_today,
        "queries_this_week":      queries_week,
        "answered_queries":       answered,
        "unanswered_queries":     total_queries - answered,
        "pending_reviews":        pending_uq,
        "answer_rate":            answer_rate,
        "total_documents":        total_docs,
        "processed_documents":    processed_docs,
        "faq_count":              faq_count,
        "avg_response_time_ms":   avg_response_time_ms,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/analytics/query-trend", summary="Daily query volume — last N days")
async def query_trend(
    days: int = Query(7, ge=1, le=90),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (await db.execute(
        select(
            func.date(ChatHistory.created_at).label("day"),
            func.count().label("count"),
        )
        .where(ChatHistory.created_at >= since)
        .group_by(func.date(ChatHistory.created_at))
        .order_by(func.date(ChatHistory.created_at))
    )).all()

    date_map = {str(r.day): r.count for r in rows}
    result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).date()
        result.append({"day": d.strftime("%a %d"), "date": str(d), "queries": date_map.get(str(d), 0)})
    return result


@router.get("/analytics/category-breakdown", summary="Query category pie chart")
async def category_breakdown(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    # Use stored category column when available, fall back to keyword classification
    stored_rows = (await db.execute(
        select(ChatHistory.category, func.count().label("cnt"))
        .where(ChatHistory.category.isnot(None))
        .group_by(ChatHistory.category)
    )).all()

    if stored_rows:
        counts = {r.category: r.cnt for r in stored_rows}
    else:
        # Legacy fallback: classify in Python
        rows = (await db.execute(select(ChatHistory.question).limit(2000))).scalars().all()
        counts: dict[str, int] = {}
        for q in rows:
            cat = _categorize(q)
            counts[cat] = counts.get(cat, 0) + 1

    return [
        {"name": k, "value": v, "color": _CATEGORY_COLORS.get(k, "#6b7280")}
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
        if v > 0
    ]


@router.get("/analytics/top-topics", summary="Top topics bar chart")
async def top_topics(
    limit: int = Query(8, ge=3, le=20),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stored_rows = (await db.execute(
        select(ChatHistory.category, func.count().label("cnt"))
        .where(ChatHistory.category.isnot(None))
        .group_by(ChatHistory.category)
        .order_by(func.count().desc())
        .limit(limit)
    )).all()

    if stored_rows:
        return [{"topic": r.category, "count": r.cnt} for r in stored_rows]

    # Legacy fallback
    rows = (await db.execute(select(ChatHistory.question).limit(2000))).scalars().all()
    topic_counts: dict[str, int] = {}
    for q in rows:
        cat = _categorize(q)
        topic_counts[cat] = topic_counts.get(cat, 0) + 1
    sorted_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:limit]
    return [{"topic": t, "count": c} for t, c in sorted_topics]


@router.get("/analytics/recent-activity", summary="Live recent activity feed")
async def recent_activity(
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    activities = []

    chats = (await db.execute(
        select(ChatHistory).order_by(ChatHistory.created_at.desc()).limit(limit)
    )).scalars().all()
    for c in chats:
        activities.append({
            "type":      "query",
            "text":      c.question[:80] + ("…" if len(c.question) > 80 else ""),
            "status":    c.is_resolved,
            "timestamp": c.created_at.isoformat(),
            "ok":        c.is_resolved == "resolved",
        })

    docs = (await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(5)
    )).scalars().all()
    for d in docs:
        activities.append({
            "type":      "upload",
            "text":      f"Document uploaded: {d.filename}",
            "status":    d.is_processed,
            "timestamp": d.created_at.isoformat(),
            "ok":        d.is_processed == "completed",
        })

    users = (await db.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )).scalars().all()
    for u in users:
        activities.append({
            "type":      "user",
            "text":      f"New user registered: {u.full_name}",
            "status":    "active" if u.is_active else "inactive",
            "timestamp": u.created_at.isoformat(),
            "ok":        u.is_active,
        })

    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Unresolved Questions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/unresolved-questions", response_model=list[UnresolvedQuestionResponse])
async def list_unresolved_questions(
    status: str = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UnresolvedQuestionResponse]:
    repo = UnresolvedQuestionRepository(db)
    if status == "all":
        return await repo.list_all()
    result = await db.execute(
        select(UnresolvedQuestion)
        .where(UnresolvedQuestion.status == status)
        .order_by(UnresolvedQuestion.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/unresolved-questions/{question_id}/answer",
             response_model=UnresolvedQuestionResponse)
async def answer_question(
    question_id: UUID,
    body: AdminAnswerRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UnresolvedQuestionResponse:
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.answer(question_id, admin.id, body.answer)
    if not uq:
        raise HTTPException(status_code=404, detail="Unresolved question not found")
    logger.info(f"Admin '{admin.email}' answered question {question_id}")
    return uq


@router.post("/unresolved-questions/{question_id}/ignore",
             response_model=UnresolvedQuestionResponse)
async def ignore_question(
    question_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UnresolvedQuestionResponse:
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.ignore(question_id)
    if not uq:
        raise HTTPException(status_code=404, detail="Unresolved question not found")
    return uq


@router.post("/unresolved-questions/{question_id}/status",
             response_model=UnresolvedQuestionResponse)
async def set_question_status(
    question_id: UUID,
    body: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UnresolvedQuestionResponse:
    """Set status: pending | under_review | added_to_kb | resolved | ignored"""
    allowed = {"pending", "under_review", "added_to_kb", "resolved", "ignored", "answered"}
    new_status = body.get("status", "")
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {allowed}")
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.set_status(question_id, new_status)
    if not uq:
        raise HTTPException(status_code=404, detail="Unresolved question not found")
    return uq


@router.post("/unresolved-questions/{question_id}/push-to-faq",
             response_model=dict)
async def push_to_faq(
    question_id: UUID,
    body: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Push an unanswered query directly into the FAQ library."""
    repo = UnresolvedQuestionRepository(db)
    uq = await repo.get_by_id(question_id)
    if not uq:
        raise HTTPException(status_code=404, detail="Unresolved question not found")

    answer = body.get("answer") or uq.admin_answer
    if not answer:
        raise HTTPException(status_code=400, detail="Provide an answer to add to FAQ")

    category = body.get("category") or uq.category or "General"
    faq_repo = FAQRepository(db)
    faq = await faq_repo.create(
        question=uq.question,
        answer=answer,
        category=category,
        status="active",
        created_by=admin.id,
    )
    # Mark the unanswered query as resolved
    await repo.set_status(question_id, "resolved")
    logger.info(f"Admin '{admin.email}' pushed question {question_id} to FAQ {faq.id}")
    return {"faq_id": str(faq.id), "message": "Question added to FAQ successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# Chat History
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/chat-history", response_model=list[ChatHistoryResponse])
async def get_all_chat_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ChatHistoryResponse]:
    repo = ChatHistoryRepository(db)
    result = await db.execute(
        select(ChatHistory)
        .order_by(ChatHistory.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/users/{user_id}/query-history")
async def user_query_history(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return query history for a specific user."""
    rows = (await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [
        {
            "id": str(r.id),
            "question": r.question,
            "answer": r.answer,
            "category": r.category,
            "confidence_score": r.confidence_score,
            "response_time_ms": r.response_time_ms,
            "is_resolved": r.is_resolved,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/users/{user_id}/stats")
async def user_stats(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return per-user statistics."""
    total = (await db.execute(
        select(func.count()).select_from(ChatHistory).where(ChatHistory.user_id == user_id)
    )).scalar() or 0
    answered = (await db.execute(
        select(func.count()).select_from(ChatHistory)
        .where(ChatHistory.user_id == user_id, ChatHistory.is_resolved == "resolved")
    )).scalar() or 0
    avg_conf = (await db.execute(
        select(func.avg(ChatHistory.confidence_score))
        .where(ChatHistory.user_id == user_id, ChatHistory.confidence_score.isnot(None))
    )).scalar()
    last_active = (await db.execute(
        select(func.max(ChatHistory.created_at)).where(ChatHistory.user_id == user_id)
    )).scalar()
    return {
        "total_queries": total,
        "answered_queries": answered,
        "avg_confidence": round(float(avg_conf), 3) if avg_conf else None,
        "last_active": last_active.isoformat() if last_active else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2)
    password: str  = Field(..., min_length=8)
    role: str      = Field(default="student")


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str]      = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str]   = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    q = select(User)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            User.email.ilike(pattern) | User.full_name.ilike(pattern)
        )
    if role in ("admin", "student"):
        role_enum = UserRole.ADMIN if role == "admin" else UserRole.STUDENT
        q = q.where(User.role == role_enum)
    elif role == "active":
        q = q.where(User.is_active == True)
    elif role == "inactive":
        q = q.where(User.is_active == False)
    q = q.order_by(User.created_at.desc()).offset(skip).limit(limit)
    users = (await db.execute(q)).scalars().all()
    return [UserResponse.from_orm(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    existing = await repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    role = UserRole.ADMIN if body.role == "admin" else UserRole.STUDENT
    from app.schemas.auth import UserRegisterRequest
    req = UserRegisterRequest(email=body.email, full_name=body.full_name, password=body.password)
    user = await repo.create_user(req, role=role)
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if "role" in updates:
        updates["role"] = UserRole.ADMIN if updates["role"] == "admin" else UserRole.STUDENT
    user = await repo.update_user(user_id, **updates)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


@router.post("/users/{user_id}/reset-password", status_code=200)
async def reset_user_password(
    user_id: UUID,
    body: ResetPasswordRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = UserRepository(db)
    user = await repo.update_user(user_id, hashed_password=hash_password(body.new_password))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Admin '{admin.email}' reset password for user {user_id}")
    return {"message": "Password reset successfully"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    repo = UserRepository(db)
    deleted = await repo.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/users/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")
    repo = UserRepository(db)
    user = await repo.update_user(user_id, is_active=False)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.update_user(user_id, is_active=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_orm(user)


# ─────────────────────────────────────────────────────────────────────────────
# FAQ Management
# ─────────────────────────────────────────────────────────────────────────────

class FAQRequest(BaseModel):
    question: str = Field(..., min_length=5)
    answer:   str = Field(..., min_length=5)
    category: str = Field(default="General")
    status:   str = Field(default="active")


class FAQResponse(BaseModel):
    id:         UUID
    question:   str
    answer:     str
    category:   str
    status:     str
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/faqs", response_model=list[FAQResponse])
async def list_faqs(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[FAQResponse]:
    from app.models.faq import FAQ
    q = select(FAQ).order_by(FAQ.created_at.desc())
    if status:
        q = q.where(FAQ.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.where(FAQ.question.ilike(pattern) | FAQ.answer.ilike(pattern))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/faqs", response_model=FAQResponse, status_code=201)
async def create_faq(
    body: FAQRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    return await FAQRepository(db).create(
        question=body.question, answer=body.answer,
        category=body.category, status=body.status,
        created_by=admin.id,
    )


@router.put("/faqs/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: UUID,
    body: FAQRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    faq = await FAQRepository(db).update(
        faq_id,
        question=body.question, answer=body.answer,
        category=body.category, status=body.status,
    )
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq


@router.delete("/faqs/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await FAQRepository(db).delete(faq_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FAQ not found")


# ─────────────────────────────────────────────────────────────────────────────
# Export Logs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export/queries")
async def export_queries_csv(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    status:     Optional[str] = Query(None, description="resolved|unresolved"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export chat history as CSV with optional date range and status filter."""
    q = select(ChatHistory).order_by(ChatHistory.created_at.desc())
    if start_date:
        q = q.where(ChatHistory.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        q = q.where(ChatHistory.created_at <= datetime.fromisoformat(end_date + "T23:59:59"))
    if status == "resolved":
        q = q.where(ChatHistory.is_resolved == "resolved")
    elif status == "unresolved":
        q = q.where(ChatHistory.is_resolved != "resolved")
    rows = (await db.execute(q)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Question", "Answer", "Category", "Status", "Confidence", "Response Time (ms)"])
    for r in rows:
        writer.writerow([
            r.created_at.isoformat(),
            r.question,
            (r.answer or "")[:500],
            r.category or "",
            r.is_resolved,
            f"{r.confidence_score:.3f}" if r.confidence_score is not None else "",
            r.response_time_ms or "",
        ])
    output.seek(0)
    filename = f"queries_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/users")
async def export_users_csv(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export user list as CSV."""
    users = (await db.execute(
        select(User).order_by(User.created_at.desc())
    )).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Role", "Status", "Registered"])
    for u in users:
        writer.writerow([
            u.full_name, u.email,
            u.role.value if hasattr(u.role, "value") else u.role,
            "Active" if u.is_active else "Suspended",
            u.created_at.isoformat(),
        ])
    output.seek(0)
    filename = f"users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/unanswered")
async def export_unanswered_csv(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export unanswered queries as CSV."""
    rows = (await db.execute(
        select(UnresolvedQuestion).order_by(UnresolvedQuestion.created_at.desc())
    )).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Question", "Category", "Status", "Confidence", "Admin Answer"])
    for r in rows:
        writer.writerow([
            r.created_at.isoformat(),
            r.question,
            r.category or "",
            r.status,
            f"{r.confidence_score:.3f}" if r.confidence_score is not None else "",
            r.admin_answer or "",
        ])
    output.seek(0)
    filename = f"unanswered_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

class SettingsUpdateRequest(BaseModel):
    settings: dict = Field(..., description="Key-value pairs to update")


@router.get("/settings", summary="Get all system settings")
async def get_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await SettingsRepository(db).get_all()


@router.put("/settings", summary="Update system settings")
async def update_settings(
    body: SettingsUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await SettingsRepository(db).bulk_set(body.settings)
