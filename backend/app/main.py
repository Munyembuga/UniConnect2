from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import ping_database

setup_logging()


def _run_migrations() -> None:
    """Run Alembic migrations on startup so the DB is always up to date."""
    try:
        from alembic.config import Config
        from alembic import command
        from pathlib import Path

        alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option(
            "script_location",
            str(Path(__file__).resolve().parent.parent / "alembic"),
        )
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.warning(f"Alembic migration failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_chroma_dir.mkdir(parents=True, exist_ok=True)

    _run_migrations()

    database_ready = await ping_database()
    if database_ready:
        logger.info("Database connection check passed")
    else:
        logger.warning("Database connection check failed during startup")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "## UniConnect — AI Student Support Chatbot\n\n"
        "> **DEV / TESTING MODE** — No authentication required. "
        "All endpoints work directly without tokens or login.\n\n"
        "### Quick test flow\n"
        "1. **Upload a document** → `POST /api/v1/documents/upload` "
        "(attach a PDF, DOCX, or TXT file). "
        "The response includes `text_preview` (first 500 chars) to confirm extraction.\n"
        "2. **Poll until processed** → `GET /api/v1/documents/{id}` "
        "until `is_processed` is `completed`.\n"
        "3. **Ask a question** → `POST /api/v1/chat/ask` with "
        "`{\"question\": \"...\"}`. Returns an AI-generated answer, "
        "source passages, and a confidence score.\n\n"
        "No `Authorization` header needed anywhere."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", summary="Service root")
async def root() -> dict[str, str]:
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
