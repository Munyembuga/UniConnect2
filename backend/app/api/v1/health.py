from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health", summary="Check API and database health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    database_status = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    return {"status": "ok", "database": database_status}
