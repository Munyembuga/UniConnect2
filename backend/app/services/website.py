"""
Website scraping and processing service.
Fetches page content, extracts text, and saves WebsiteSource records.
After scraping, the standalone process_website_pipeline() runs the full
chunk → embed → ChromaDB pipeline as a background task.
"""
import asyncio
from typing import Optional, Tuple
from uuid import UUID
from loguru import logger
from bs4 import BeautifulSoup
import requests

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.website import WebsiteRepository
from app.core.config import settings


def _extract_text_from_html(html: str) -> str:
    """Strip scripts/styles and return clean readable text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class WebsiteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WebsiteRepository(db)

    async def add_website(
        self, user_id: UUID, url: str
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Scrape a URL, save its content, and return a summary dict.
        Returns (result_dict, error_message). error_message is None on success.
        """
        try:
            # Check for duplicate URL
            existing = await self.repo.get_by_url(url)
            if existing:
                return None, f"URL already exists in the knowledge base (id={existing.id})"

            # Create placeholder record
            ws = await self.repo.create_website(user_id, url)

            # Fetch content (run in thread to avoid blocking the event loop)
            loop = asyncio.get_running_loop()
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, timeout=15, headers={"User-Agent": "UniConnect/1.0"}),
                )
                response.raise_for_status()
                html = response.text
            except Exception as fetch_err:
                logger.warning(f"Failed to fetch {url}: {fetch_err}")
                await self.repo.update_status(ws.id, "failed")
                return None, str(fetch_err)

            # Extract text
            cleaned = _extract_text_from_html(html)

            # Extract title and meta description
            soup = BeautifulSoup(html, "lxml")
            title = None
            if soup.title and soup.title.string:
                title = soup.title.string.strip()[:255]
            description = None
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Persist content (status stays "pending" — pipeline will set "completed")
            updated = await self.repo.update_content(
                ws.id, cleaned,
                title=title,
                description=description,
                status="pending",
            )

            logger.info(f"Website scraped: {url} ({len(cleaned)} chars)")
            return {
                "id": updated.id,
                "url": updated.url,
                "title": updated.title,
                "description": updated.description,
                "total_chunks": updated.total_chunks,
                "is_processed": updated.is_processed,
            }, None

        except Exception as exc:
            logger.error(f"Error adding website {url}: {exc}")
            return None, str(exc)

    async def get_website(self, website_id: UUID):
        return await self.repo.get_by_id(website_id)

    async def list_user_websites(self, user_id: UUID):
        return await self.repo.list_by_user(user_id)

    async def list_all_websites(self):
        return await self.repo.list_all()

    async def delete_website(self, website_id: UUID) -> bool:
        return await self.repo.delete(website_id)


# ---------------------------------------------------------------------------
# Standalone pipeline — runs as a FastAPI BackgroundTask with its own session
# ---------------------------------------------------------------------------

async def process_website_pipeline(website_id: UUID) -> None:
    """
    Full knowledge-base pipeline for a website source:
      1. Chunk the scraped content
      2. Generate Gemini embeddings
      3. Upsert into ChromaDB (no PostgreSQL chunk records needed for websites)
      4. Update total_chunks and mark as completed (or failed)

    Website chunks are stored directly in ChromaDB with IDs in the form
    "website_{website_id}_{index}", so upsert is always idempotent.
    """
    from app.db.database import AsyncSessionLocal
    from app.services.chunking import split_text
    from app.services.embeddings import EmbeddingService
    from app.services.chromadb_client import ChromaClient

    async with AsyncSessionLocal() as db:
        repo = WebsiteRepository(db)

        try:
            ws = await repo.get_by_id(website_id)
            if not ws:
                logger.error(f"Website pipeline: source {website_id} not found")
                return

            if not ws.content:
                logger.error(f"Website pipeline: no content for {website_id}")
                await repo.update_status(website_id, "failed")
                return

            await repo.update_status(website_id, "processing")

            # 1. Chunk
            chunks_text = split_text(ws.content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
            if not chunks_text:
                logger.error(f"Website pipeline: chunking produced nothing for {website_id}")
                await repo.update_status(website_id, "failed")
                return

            # 2 & 3. Embed + ChromaDB upsert
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

            vectors = embed_service.embed_texts(chunks_text)
            chroma.upsert(
                settings.CHROMA_COLLECTION_NAME,
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=chunks_text,
            )

            # 4. Mark complete
            await repo.update_content(
                website_id,
                ws.content,
                title=ws.title,
                description=ws.description,
                total_chunks=len(chunks_text),
                status="completed",
            )
            logger.info(
                f"Website pipeline complete: {website_id}, "
                f"{len(chunks_text)} chunks indexed"
            )

        except Exception as e:
            logger.error(f"Website pipeline failed for {website_id}: {e}")
            try:
                await repo.update_status(website_id, "failed")
            except Exception:
                pass
