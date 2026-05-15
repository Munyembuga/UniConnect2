"""
Processing API router to trigger chunking for documents and websites.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.services.chunking import ChunkingService

router = APIRouter(prefix="/process", tags=["Processing"])


async def get_chunking_service(db: AsyncSession = Depends(get_db)) -> ChunkingService:
    return ChunkingService(db)


@router.post("/document/{document_id}")
async def process_document(document_id: UUID, current_user_id: UUID = Depends(get_current_user), service: ChunkingService = Depends(get_chunking_service)):
    try:
        count = await service.process_document(document_id)
        return {"document_id": document_id, "chunks_created": count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing document")


@router.post("/website/{website_id}")
async def process_website(website_id: UUID, current_user_id: UUID = Depends(get_current_user), service: ChunkingService = Depends(get_chunking_service)):
    try:
        count = await service.process_website(website_id)
        return {"website_id": website_id, "chunks_created": count}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing website {website_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing website")


@router.get("/chunks/{document_id}")
async def list_chunks(document_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.repositories.document_chunk import DocumentChunkRepository
    repo = DocumentChunkRepository(db)
    items = await repo.list_by_document(document_id)
    return [{"id": str(i.id), "index": i.chunk_index, "content": i.content[:400]} for i in items]
