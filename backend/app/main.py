import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import ping_database

setup_logging()

# ── In-process rate-limit store (resets on restart; use Redis for multi-worker) ──
_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW = 60.0  # seconds


async def _create_tables() -> None:
    try:
        from app.db.database import engine
        from app.db.base import Base
        from sqlalchemy import text

        import app.models.user                 # noqa: F401
        import app.models.document             # noqa: F401
        import app.models.document_chunk       # noqa: F401
        import app.models.chat_history         # noqa: F401
        import app.models.unresolved_question  # noqa: F401
        import app.models.faq                  # noqa: F401
        import app.models.settings             # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Safe incremental column/type migrations
        migrations = [
            "ALTER TYPE documenttype ADD VALUE IF NOT EXISTS 'url'",
        ]
        column_migrations = [
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url VARCHAR(1000)",
            "ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS session_id VARCHAR(100)",
            "ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
            "ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS response_time_ms INTEGER",
            "ALTER TABLE unresolved_questions ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
        ]

        for stmt in migrations:
            try:
                async with engine.connect() as conn:
                    await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(stmt))
            except Exception as e:
                logger.warning(f"Migration (non-fatal): {e}")

        for stmt in column_migrations:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Column migration (non-fatal): {e}")

        # Indexes for new columns
        index_migrations = [
            "CREATE INDEX IF NOT EXISTS ix_chat_history_category ON chat_history(category)",
            "CREATE INDEX IF NOT EXISTS ix_chat_history_is_resolved ON chat_history(is_resolved)",
            "CREATE INDEX IF NOT EXISTS ix_unresolved_questions_status ON unresolved_questions(status)",
        ]
        for stmt in index_migrations:
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Index migration (non-fatal): {e}")

        logger.info("Database tables and migrations applied successfully")
    except Exception as e:
        logger.warning(f"Table creation failed (non-fatal): {e}")


async def _seed_admin() -> None:
    ADMIN_EMAIL    = "admin@uniconnect.com"
    ADMIN_PASSWORD = "Admin@1234"
    ADMIN_NAME     = "UniConnect Admin"

    try:
        from app.db.database import AsyncSessionLocal
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        from sqlalchemy.future import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
            if not result.scalar_one_or_none():
                admin = User(
                    email=ADMIN_EMAIL,
                    full_name=ADMIN_NAME,
                    hashed_password=hash_password(ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                    is_active=True,
                    is_verified=True,
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Default admin created: {ADMIN_EMAIL}")
            else:
                logger.info(f"Admin account already exists: {ADMIN_EMAIL}")
    except Exception as e:
        logger.warning(f"Admin seeding failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_chroma_dir.mkdir(parents=True, exist_ok=True)

    await _create_tables()
    await _seed_admin()

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
        "### Authentication\n"
        "1. **Register** → `POST /api/v1/auth/register`\n"
        "2. **Login** → `POST /api/v1/auth/login` — copy the `access_token`\n"
        "3. Click **Authorize** (🔒) and enter: `Bearer <access_token>`\n\n"
        "### Roles\n"
        "| Role | Permissions |\n"
        "|------|-------------|\n"
        "| **Admin** | Upload/list/delete documents, view all chat history, answer unresolved questions |\n"
        "| **Student** | Ask questions, view own chat history |\n\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rate limiting middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next) -> Response:
    # Only rate-limit the chat ask endpoint to protect AI costs
    if request.url.path.endswith("/chat/ask") and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - _RATE_WINDOW
        # Purge old timestamps
        _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > window_start]
        limit = settings.RATE_LIMIT_PER_MINUTE
        if len(_rate_store[client_ip]) >= limit:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Maximum {limit} requests per minute."},
                headers={"Retry-After": "60"},
            )
        _rate_store[client_ip].append(now)
    return await call_next(request)


app.include_router(api_router)


@app.get("/", summary="Service root")
async def root() -> dict[str, str]:
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
