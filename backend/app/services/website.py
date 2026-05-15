"""
Website scraping and processing service.
Fetches page content, extracts text, and saves WebsiteSource records.
"""
import asyncio
from typing import Optional
from uuid import UUID
from loguru import logger
from bs4 import BeautifulSoup
import requests

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.website import WebsiteRepository
from app.core.config import settings


def _clean_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts and styles
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    text = soup.get_text(separator=" \n ")
    # Basic normalization
    lines = [line.strip() for line in text.splitlines()]
    chunks = [chunk for line in lines for chunk in line.split("  ") if chunk]
    cleaned = "\n".join([c for c in chunks if c])
    return cleaned


class WebsiteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WebsiteRepository(db)

    async def add_website(self, user_id: UUID, url: str) -> tuple[Optional[dict], Optional[Exception]]:
        """Add website and attempt to scrape content asynchronously."""
        try:
            # Create placeholder record with pending status
            ws = await self.repo.create_website(user_id, url)

            # Fetch content in thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            try:
                html = await loop.run_in_executor(None, lambda: requests.get(url, timeout=15).text)
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                return None, e

            # Clean text
            cleaned = _clean_text_from_html(html)

            # Extract title and meta description
            soup = BeautifulSoup(html, "lxml")
            title = soup.title.string.strip() if soup.title and soup.title.string else None
            description = None
            if soup.find("meta", attrs={"name": "description"}):
                description = soup.find("meta", attrs={"name": "description"}).get("content")

            # Update record with content
            updated = await self.repo.update_content(ws.id, cleaned, title=title, description=description)

            # Optionally trigger chunking/embedding pipeline later
            return {
                "id": updated.id,
                "url": updated.url,
                "title": updated.title,
                "description": updated.description,
                "total_chunks": updated.total_chunks,
            }, None

        except Exception as exc:
            logger.error(f"Error adding website {url}: {exc}")
            return None, exc

    async def get_website(self, website_id: UUID):
        return await self.repo.get_by_id(website_id)

    async def list_user_websites(self, user_id: UUID):
        return await self.repo.list_by_user(user_id)

    async def delete_website(self, website_id: UUID) -> bool:
        return await self.repo.delete(website_id)
