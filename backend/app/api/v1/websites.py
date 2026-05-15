"""
Website sources API router.
Endpoints for adding, listing, retrieving, and deleting website sources.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger
import asyncio

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.services.website import WebsiteService
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
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: WebsiteService = Depends(get_website_service),
):
    # Only admins may add sources
    user = await service.repo.db.execute  # quick check to keep linter quiet
    try:
        # Scrape and add
        result, err = await service.add_website(current_user_id, req.url)
        if err:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to fetch url: {err}")

        ws = await service.get_website(result["id"]) if result else None
        if not ws:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create website source")

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
        logger.error(f"Error in add_website: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error adding website")


@router.get("", response_model=list[WebsiteListResponse])
async def list_websites(
    current_user_id: UUID = Depends(get_current_user),
    service: WebsiteService = Depends(get_website_service),
):
    try:
        items = await service.list_user_websites(current_user_id)
        return [WebsiteListResponse(
            id=i.id,
            url=i.url,
            title=i.title,
            is_processed=i.is_processed,
            total_chunks=i.total_chunks,
            created_at=i.created_at,
        ) for i in items]
    except Exception as e:
        logger.error(f"Error listing websites: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing websites")


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(website_id: UUID, current_user_id: UUID = Depends(get_current_user), service: WebsiteService = Depends(get_website_service)):
    try:
        ws = await service.get_website(website_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found")
        # verify ownership
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
        logger.error(f"Error getting website: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving website")


@router.delete("/{website_id}", response_model=WebsiteDeleteResponse)
async def delete_website(website_id: UUID, current_user_id: UUID = Depends(get_current_user), service: WebsiteService = Depends(get_website_service)):
    try:
        ws = await service.get_website(website_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found")
        if ws.user_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        success = await service.delete_website(website_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete website")
        return WebsiteDeleteResponse(success=True, message="Website deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting website: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting website")
