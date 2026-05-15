from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import ping_database

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_chroma_dir.mkdir(parents=True, exist_ok=True)

    database_ready = await ping_database()
    if database_ready:
        logger.info("Database connection check passed")
    else:
        logger.warning("Database connection check failed during startup")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready FastAPI backend for UniConnect - AI Student Support Chatbot.",
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
