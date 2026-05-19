"""
Website sources API router.
Endpoints for adding, listing, retrieving, and deleting website sources.
After a URL is added and scraped, the chunk→embed pipeline runs automatically
in the background so the content is searchable without extra steps.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.services.website import WebsiteService, process_website_pipeline
from app.services.user import UserService
from app.schemas.website import (
    WebsiteCreateRequest,
    WebsiteResponse,
    WebsiteListResponse,
    WebsiteDeleteResponse,
)

router = APIRouter(prefix="/websites", tags=["Websites"])


async def get_website_service(db: AsyncSession = Depends(get_db)) -> WebsiteService:
    return WebsiteService(db)


# ── helpers ──────────────────────────────────────────────────────────────────

async def _require_admin(current_user_id: UUID, db: AsyncSession) -> None:
    user_service = UserService(db)
    user = await user_service.repo.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage website sources",
        )


# ── routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/add",
    response_model=WebsiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a website URL to the knowledge base",
    description=(
        "Scrapes the URL, extracts text, then automatically chunks and embeds "
        "the content in the background. Poll GET /websites/{id} until "
        "is_processed == 'completed'."
    ),
)
async def add_website(
    req: WebsiteCreateRequest,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: WebsiteService = Depends(get_website_service),
):
    await _require_admin(current_user_id, db)

    url_str = str(req.url)
    result, err = await service.add_website(current_user_id, url_str)

    if err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to add website: {err}",
        )

    ws = await service.get_website(result["id"])
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Website was created but could not be retrieved",
        )

    # Auto-trigger the chunk→embed pipeline (background, non-blocking)
    background_tasks.add_task(process_website_pipeline, ws.id)
    logger.info(f"Website added: {url_str} — pipeline queued")

    return WebsiteResponse(
        id=ws.id,
        url=ws.url,
        title=ws.title,
        description=ws.description,
        total_chunks=ws.total_chunks,
        is_processed=ws.is_processed,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.get(
    "",
    response_model=list[WebsiteListResponse],
    summary="List website sources",
    description="Admins see all sources; students see sources added by themselves.",
)
async def list_websites(
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: WebsiteService = Depends(get_website_service),
):
    try:
        user_service = UserService(db)
        user = await user_service.repo.get_user_by_id(current_user_id)
        if user and user.is_admin():
            items = await service.list_all_websites()
        else:
            items = await service.list_user_websites(current_user_id)

        return [
            WebsiteListResponse(
                id=i.id,
                url=i.url,
                title=i.title,
                is_processed=i.is_processed,
                total_chunks=i.total_chunks,
                created_at=i.created_at,
            )
            for i in items
        ]
    except Exception as e:
        logger.error(f"Error listing websites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing websites",
        )


@router.get(
    "/{website_id}",
    response_model=WebsiteResponse,
    summary="Get website source details",
)
async def get_website(
    website_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    service: WebsiteService = Depends(get_website_service),
):
    try:
        ws = await service.get_website(website_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
        if ws.user_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return WebsiteResponse(
            id=ws.id,
            url=ws.url,
            title=ws.title,
            description=ws.description,
            total_chunks=ws.total_chunks,
            is_processed=ws.is_processed,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting website {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving website",
        )


@router.delete(
    "/{website_id}",
    response_model=WebsiteDeleteResponse,
    summary="Delete a website source",
)
async def delete_website(
    website_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: WebsiteService = Depends(get_website_service),
):
    await _require_admin(current_user_id, db)

    ws = await service.get_website(website_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")

    success = await service.delete_website(website_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete website",
        )
    return WebsiteDeleteResponse(success=True, message="Website deleted successfully")
