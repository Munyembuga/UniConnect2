"""
Embeddings API router — generate embeddings and upsert to ChromaDB.
These endpoints are kept for manual re-processing; the normal flow
triggers embedding automatically after upload/website-add.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.chromadb_client import ChromaClient
from app.repositories.document_chunk import DocumentChunkRepository

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


@router.post("/document/{document_id}", summary="Re-embed a document manually")
async def embed_document(
    document_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate embeddings for all chunks of a document and upsert into ChromaDB.
    Useful if the pipeline failed or the embedding model changed.
    """
    repo = DocumentChunkRepository(db)
    chunks = await repo.list_by_document(document_id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chunks found for this document. Process the document first.",
        )

    texts = [c.content for c in chunks]
    ids = [str(c.id) for c in chunks]
    metadatas = [
        {"source_type": "document", "document_id": str(document_id), "chunk_index": c.chunk_index}
        for c in chunks
    ]

    embed_service = EmbeddingService()
    chroma = ChromaClient()

    try:
        vectors = embed_service.embed_texts(texts)
    except Exception as e:
        logger.error(f"Embedding generation failed for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {e}",
        )

    try:
        chroma.upsert(
            settings.CHROMA_COLLECTION_NAME,
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas,
            documents=texts,
        )
    except Exception as e:
        logger.error(f"ChromaDB upsert failed for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ChromaDB upsert failed: {e}",
        )

    return {"document_id": str(document_id), "indexed_chunks": len(ids)}


@router.post("/website/{website_id}", summary="Re-embed a website manually")
async def embed_website(
    website_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-chunk and re-embed a website's content into ChromaDB.
    Useful if the pipeline failed or the embedding model changed.
    """
    from app.repositories.website import WebsiteRepository
    from app.services.chunking import split_text

    website_repo = WebsiteRepository(db)
    ws = await website_repo.get_by_id(website_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    if not ws.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Website has no scraped content yet.",
        )

    chunks_text = split_text(ws.content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunking produced no content from this website.",
        )

    ids = [f"website_{website_id}_{i}" for i in range(len(chunks_text))]
    metadatas = [
        {
            "source_type": "website",
            "website_id": str(website_id),
            "url": ws.url,
            "title": ws.title or "",
            "chunk_index": i,
        }
        for i in range(len(chunks_text))
    ]

    embed_service = EmbeddingService()
    chroma = ChromaClient()

    try:
        vectors = embed_service.embed_texts(chunks_text)
    except Exception as e:
        logger.error(f"Embedding generation failed for website {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {e}",
        )

    try:
        chroma.upsert(
            settings.CHROMA_COLLECTION_NAME,
            ids=ids,
            embeddings=vectors,
            metadatas=metadatas,
            documents=chunks_text,
        )
    except Exception as e:
        logger.error(f"ChromaDB upsert failed for website {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ChromaDB upsert failed: {e}",
        )

    await website_repo.update_content(
        website_id, ws.content,
        title=ws.title, description=ws.description,
        total_chunks=len(chunks_text),
    )

    return {"website_id": str(website_id), "indexed_chunks": len(ids)}
