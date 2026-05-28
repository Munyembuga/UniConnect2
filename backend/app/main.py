from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import ping_database

setup_logging()


async def _create_tables() -> None:
    """Create all database tables if they don't exist yet."""
    try:
        from app.db.database import engine
        from app.db.base import Base

        import app.models.user                 # noqa: F401
        import app.models.document             # noqa: F401
        import app.models.document_chunk       # noqa: F401
        import app.models.chat_history         # noqa: F401
        import app.models.unresolved_question  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified successfully")
    except Exception as e:
        logger.warning(f"Table creation failed (non-fatal): {e}")


async def _seed_admin() -> None:
    """Create the default admin account if it does not exist yet."""
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
        "### Flow\n"
        "1. Admin uploads a document → background pipeline chunks + embeds it\n"
        "2. Students ask questions → AI searches the knowledge base\n"
        "3. Low-confidence answers are flagged for admin review\n"
        "4. Admin answers flagged questions → next student with the same question gets the admin answer\n"
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
