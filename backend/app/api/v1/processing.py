"""
Processing API router — manually trigger the chunk→embed→ChromaDB pipeline
for a document or website that is stuck in pending/failed state.
No authentication required (dev mode).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.repositories.document import DocumentRepository
from app.repositories.website import WebsiteRepository
from app.services.document import process_document_pipeline
from app.services.website import process_website_pipeline

router = APIRouter(prefix="/process", tags=["Processing"])


@router.post(
    "/document/{document_id}",
    summary="Re-run pipeline for a document",
    description="Triggers chunk → embed → ChromaDB for a document. Useful if the background task failed after upload.",
)
async def process_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not doc.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no extracted text — re-upload the file first.",
        )
    background_tasks.add_task(process_document_pipeline, document_id)
    logger.info(f"Manual pipeline triggered for document {document_id}")
    return {"document_id": str(document_id), "status": "pipeline queued"}


@router.post(
    "/website/{website_id}",
    summary="Re-run pipeline for a website",
    description="Triggers chunk → embed → ChromaDB for a website source. Useful if the background task failed.",
)
async def process_website(
    website_id: UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = WebsiteRepository(db)
    ws = await repo.get_by_id(website_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    if not ws.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Website has no scraped content — re-add the URL first.",
        )
    background_tasks.add_task(process_website_pipeline, website_id)
    logger.info(f"Manual pipeline triggered for website {website_id}")
    return {"website_id": str(website_id), "status": "pipeline queued"}


@router.get(
    "/chunks/{document_id}",
    summary="List chunks for a document",
    description="Returns the first 400 chars of each stored chunk — useful for verifying chunking.",
)
async def list_chunks(document_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.repositories.document_chunk import DocumentChunkRepository
    repo = DocumentChunkRepository(db)
    items = await repo.list_by_document(document_id)
    return [{"id": str(i.id), "index": i.chunk_index, "content": i.content[:400]} for i in items]
