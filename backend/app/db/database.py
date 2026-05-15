# =============================================================================
# Database Engine & Base - Async SQLAlchemy Setup
# Creates the async engine, session factory, and declarative base
# =============================================================================

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from loguru import logger


# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,           # Log SQL queries in debug mode
    pool_size=20,                   # Max persistent connections
    max_overflow=10,                # Extra connections beyond pool_size
    pool_pre_ping=True,             # Test connections before use
    pool_recycle=3600,              # Recycle connections every hour
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,         # Don't expire objects after commit
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy models."""
    pass


async def init_db() -> None:
    """Initialize database tables (for development only; use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully")


async def close_db() -> None:
    """Close the database engine and all connections."""
    await engine.dispose()
    logger.info("Database connections closed")
