"""
Website sources API router — Admin only.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.services.website import WebsiteService, process_website_pipeline
from app.schemas.website import (
    WebsiteCreateRequest,
    WebsiteResponse,
    WebsiteListResponse,
    WebsiteDeleteResponse,
)

router = APIRouter(prefix="/websites", tags=["Websites"])


async def get_website_service(db: AsyncSession = Depends(get_db)) -> WebsiteService:
    return WebsiteService(db)


@router.post("/add", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def add_website(
    req: WebsiteCreateRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    service: WebsiteService = Depends(get_website_service),
):
    url_str = str(req.url)
    result, err = await service.add_website(admin.id, url_str)
    if err:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Failed to add website: {err}")
    ws = await service.get_website(result["id"])
    if not ws:
        raise HTTPException(status_code=500, detail="Website created but could not be retrieved")
    background_tasks.add_task(process_website_pipeline, ws.id)
    logger.info(f"Website added by admin '{admin.email}': {url_str}")
    return WebsiteResponse(id=ws.id, url=ws.url, title=ws.title, description=ws.description,
                           total_chunks=ws.total_chunks, is_processed=ws.is_processed,
                           created_at=ws.created_at, updated_at=ws.updated_at)


@router.get("", response_model=list[WebsiteListResponse])
async def list_websites(
    admin: User = Depends(require_admin),
    service: WebsiteService = Depends(get_website_service),
):
    items = await service.list_all_websites()
    return [WebsiteListResponse(id=i.id, url=i.url, title=i.title,
                                 is_processed=i.is_processed, total_chunks=i.total_chunks,
                                 created_at=i.created_at) for i in items]


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: UUID,
    admin: User = Depends(require_admin),
    service: WebsiteService = Depends(get_website_service),
):
    ws = await service.get_website(website_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Website not found")
    return WebsiteResponse(id=ws.id, url=ws.url, title=ws.title, description=ws.description,
                           total_chunks=ws.total_chunks, is_processed=ws.is_processed,
                           created_at=ws.created_at, updated_at=ws.updated_at)


@router.delete("/{website_id}", response_model=WebsiteDeleteResponse)
async def delete_website(
    website_id: UUID,
    admin: User = Depends(require_admin),
    service: WebsiteService = Depends(get_website_service),
):
    ws = await service.get_website(website_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Website not found")
    success = await service.delete_website(website_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete website")
    return WebsiteDeleteResponse(success=True, message="Website deleted successfully")
