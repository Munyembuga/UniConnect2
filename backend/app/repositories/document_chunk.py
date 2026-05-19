"""
Repository for document_chunks operations.
"""
from typing import List, Optional
from uuid import UUID
from hashlib import sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sql_delete
from loguru import logger

from app.models.document_chunk import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chunks(self, document_id: UUID, chunks: List[str]) -> List[DocumentChunk]:
        created = []
        for idx, text in enumerate(chunks):
            # Hash includes document_id + index so it is globally unique even when
            # the same text appears in multiple documents.
            h = sha256(f"{document_id}:{idx}:{text}".encode("utf-8")).hexdigest()
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                content=text,
                chunk_hash=h,
            )
            self.db.add(chunk)
            created.append(chunk)
        await self.db.flush()
        await self.db.commit()
        for c in created:
            await self.db.refresh(c)
        logger.info(f"Created {len(created)} chunks for document {document_id}")
        return created

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document. Safe to call before re-processing."""
        try:
            result = await self.db.execute(
                sql_delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            await self.db.commit()
            deleted = result.rowcount
            if deleted:
                logger.info(f"Deleted {deleted} existing chunks for document {document_id}")
            return deleted
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting chunks for document {document_id}: {e}")
            raise

    async def list_by_document(self, document_id: UUID) -> List[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()

    async def get_by_id(self, chunk_id: UUID) -> Optional[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        return result.scalar_one_or_none()
