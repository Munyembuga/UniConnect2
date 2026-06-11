from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.models.settings import SystemSetting

# Default settings seeded on first load
DEFAULTS = {
    "system_name":          ("UniConnect", "Display name for the system"),
    "system_description":   ("University of Rwanda AI Assistant", "Short description"),
    "gemini_model":         ("gemini-2.0-flash", "Gemini generation model"),
    "openrouter_model":     ("google/gemini-3.5-flash", "OpenRouter generation model"),
    "chunk_size":           ("1000", "RAG chunk size in characters"),
    "chunk_overlap":        ("200", "RAG chunk overlap in characters"),
    "similarity_top_k":     ("5", "Number of chunks to retrieve"),
    "confidence_threshold": ("0.40", "Minimum confidence to consider answered"),
    "max_tokens":           ("4096", "Max tokens for AI response"),
    "temperature":          ("0.3", "AI generation temperature"),
    "rate_limit":           ("30", "Max requests per minute per user"),
    "allow_registration":   ("true", "Allow new user self-registration"),
    "default_role":         ("student", "Default role for new users"),
}


class SettingsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> dict:
        """Return all settings as a key→value dict, seeding defaults for missing keys."""
        try:
            result = await self.db.execute(select(SystemSetting))
            rows = {r.key: r.value for r in result.scalars().all()}
            # Seed any missing defaults
            for key, (default_val, desc) in DEFAULTS.items():
                if key not in rows:
                    rows[key] = default_val
            return rows
        except Exception as e:
            logger.error(f"Error fetching settings: {e}")
            return {k: v for k, (v, _) in DEFAULTS.items()}

    async def get(self, key: str) -> Optional[str]:
        try:
            result = await self.db.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            row = result.scalar_one_or_none()
            if row:
                return row.value
            return DEFAULTS.get(key, (None, None))[0]
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return None

    async def set(self, key: str, value: str) -> SystemSetting:
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        row = result.scalar_one_or_none()
        desc = DEFAULTS.get(key, (None, ""))[1]
        if row:
            row.value = value
        else:
            row = SystemSetting(key=key, value=value, description=desc)
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def bulk_set(self, updates: dict) -> dict:
        for key, value in updates.items():
            await self.set(key, str(value))
        return await self.get_all()
