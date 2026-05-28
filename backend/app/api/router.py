from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.websites import router as websites_router
from app.api.v1.processing import router as processing_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)          # register, login, refresh, profile
api_router.include_router(documents_router)
api_router.include_router(websites_router)
api_router.include_router(processing_router)
api_router.include_router(embeddings_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router)
