"""
Repository for document_chunks operations.
"""
from typing import List, Optional, Tuple
from uuid import UUID
from hashlib import sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sql_delete, func, text
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

    async def keyword_search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        PostgreSQL full-text search using tsvector/tsquery.
        Returns list of (chunk, rank_score) sorted by relevance descending.
        Falls back to ILIKE if the query produces no FTS results.
        """
        try:
            # plainto_tsquery handles multi-word queries safely (no syntax errors)
            fts_query = func.plainto_tsquery("english", query)
            rank_col = func.ts_rank(
                func.to_tsvector("english", DocumentChunk.content),
                fts_query,
            )
            stmt = (
                select(DocumentChunk, rank_col.label("rank"))
                .where(
                    func.to_tsvector("english", DocumentChunk.content).op("@@")(fts_query)
                )
                .order_by(rank_col.desc())
                .limit(top_k)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            if rows:
                return [(row[0], float(row[1])) for row in rows]

            # Fallback: ILIKE substring match when FTS finds nothing
            pattern = f"%{query}%"
            stmt2 = (
                select(DocumentChunk)
                .where(DocumentChunk.content.ilike(pattern))
                .limit(top_k)
            )
            result2 = await self.db.execute(stmt2)
            chunks = result2.scalars().all()
            return [(c, 0.1) for c in chunks]

        except Exception as e:
            logger.warning(f"Keyword search error: {e}")
            return []
