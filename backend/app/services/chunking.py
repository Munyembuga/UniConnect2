"""
Chunking service: split document or website text into chunks for embeddings.
Uses simple fallback splitter; will use LangChain splitters if available.
"""
from typing import List
from uuid import UUID
import math
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.document import DocumentRepository
from app.repositories.website import WebsiteRepository
from app.models.document import Document


def _simple_text_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


class ChunkingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.website_repo = WebsiteRepository(db)

    async def process_document(self, document_id: UUID) -> int:
        """Load document, extract text, split into chunks, save chunks, update document metadata."""
        # Get document
        doc = await self.doc_repo.get_document_by_id(document_id)
        if not doc:
            raise ValueError("Document not found")

        # Mark processing
        await self.doc_repo.update_document_status(document_id, status="processing")

        text = doc.extracted_text
        if not text:
            # Try to read file content from storage as fallback
            try:
                with open(doc.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                text = None

        if not text:
            await self.doc_repo.update_document_status(document_id, status="failed")
            raise ValueError("No text available to chunk")

        # Use LangChain TextSplitter if available, otherwise fallback
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
            LangChainChunks = splitter.split_text(text)
            chunks = [c for c in LangChainChunks if c.strip()]
        except Exception:
            chunks = _simple_text_split(text, chunk_size=chunk_size // 5, overlap=overlap // 5)

        # Persist chunks
        created = await self.chunk_repo.create_chunks(document_id, chunks)

        # Update document metadata
        await self.doc_repo.update_document_status(document_id, status="completed", total_chunks=len(created), extracted_text=doc.extracted_text)

        return len(created)

    async def process_website(self, website_id: UUID) -> int:
        ws = await self.website_repo.get_by_id(website_id)
        if not ws:
            raise ValueError("Website not found")
        text = ws.content
        if not text:
            raise ValueError("No content to chunk")

        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP

        try:
            from langchain.text_splitter import CharacterTextSplitter
            splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
            chunks = splitter.split_text(text)
        except Exception:
            chunks = _simple_text_split(text, chunk_size=chunk_size // 5, overlap=overlap // 5)

        # For website chunks, create DocumentChunk entries with a synthetic document_id using website id namespace
        # We'll store website chunks in document_chunks with document_id set to None or website id - but model requires document_id
        # Practical approach: create entries with document_id = UUID of website (reusing the field)
        created = await self.chunk_repo.create_chunks(website_id, chunks)

        # Update website metadata
        await self.website_repo.update_content(website_id, ws.content, title=ws.title, description=ws.description, total_chunks=len(created))

        return len(created)
