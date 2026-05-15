"""
Embeddings API router - endpoints to generate embeddings and upsert to ChromaDB.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.api.v1.auth import get_current_user
from app.services.embeddings import EmbeddingService
from app.services.chromadb_client import ChromaClient
from app.repositories.document_chunk import DocumentChunkRepository

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


async def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


async def get_chroma_client() -> ChromaClient:
    return ChromaClient()


@router.post("/document/{document_id}")
async def embed_document(document_id: UUID, current_user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Generate embeddings for all chunks of a document and upsert into chroma
    embed_service = EmbeddingService()
    chroma = ChromaClient()
    repo = DocumentChunkRepository(db)

    chunks = await repo.list_by_document(document_id)
    if not chunks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found for document")

    texts = [c.content for c in chunks]
    ids = [str(c.id) for c in chunks]

    try:
        vectors = embed_service.embed_texts(texts)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embedding generation failed")

    try:
        chroma.upsert(settings.CHROMA_COLLECTION_NAME, ids=ids, embeddings=vectors, metadatas=[{"document_id": str(document_id), "chunk_index": c.chunk_index} for c in chunks], documents=texts)
    except Exception as e:
        logger.error(f"ChromaDB upsert failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ChromaDB upsert failed")

    return {"document_id": str(document_id), "indexed_chunks": len(ids)}


@router.post("/website/{website_id}")
async def embed_website(website_id: UUID, current_user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Similar to document embedding but using website id as reference
    embed_service = EmbeddingService()
    chroma = ChromaClient()
    repo = DocumentChunkRepository(db)

    chunks = await repo.list_by_document(website_id)  # we stored website chunks using website id
    if not chunks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found for website")

    texts = [c.content for c in chunks]
    ids = [str(c.id) for c in chunks]

    try:
        vectors = embed_service.embed_texts(texts)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embedding generation failed")

    try:
        chroma.upsert(settings.CHROMA_COLLECTION_NAME, ids=ids, embeddings=vectors, metadatas=[{"website_id": str(website_id), "chunk_index": c.chunk_index} for c in chunks], documents=texts)
    except Exception as e:
        logger.error(f"ChromaDB upsert failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ChromaDB upsert failed")

    return {"website_id": str(website_id), "indexed_chunks": len(ids)}
