# =============================================================================
# Core Configuration - Pydantic Settings
# Loads all environment variables with validation and defaults
# =============================================================================

from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "UniConnect"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- PostgreSQL Database ---
    POSTGRES_USER: str = "uniconnect"
    POSTGRES_PASSWORD: str = "uniconnect_secret_2024"
    POSTGRES_DB: str = "uniconnect_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://uniconnect:uniconnect_secret_2024@db:5432/uniconnect_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """
        Render (and many hosting providers) supply a DATABASE_URL that starts
        with 'postgresql://' which maps to psycopg2 (not installed).
        Auto-convert to 'postgresql+asyncpg://' so the async driver is used.
        """
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # --- JWT Authentication ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_REFRESH_SECRET_KEY: str = "change-me-in-production-refresh"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Gemini AI ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- ChromaDB ---
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "uniconnect_knowledge"

    # --- File Uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"

    # --- RAG Configuration ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    SIMILARITY_TOP_K: int = 5
    CONFIDENCE_THRESHOLD: float = 0.65

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- CORS ---
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:5173","http://localhost:8080"]'

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse comma-separated extensions into a list."""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse JSON CORS origins string into a list."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    @property
    def resolved_upload_dir(self):
        """Get resolved upload directory path."""
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / self.UPLOAD_DIR

    @property
    def resolved_chroma_dir(self):
        """Get resolved ChromaDB directory path."""
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / "chroma_db"
    
    @property
    def UPLOAD_DIRECTORY(self) -> str:
        """Get upload directory path."""
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent
        return str(base_dir / self.UPLOAD_DIR)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()
