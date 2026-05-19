"""
Document Upload API Router - v1
Endpoints for document upload, retrieval, and management.

After a file is uploaded, the chunk→embed pipeline runs automatically as a
background task — the frontend only needs to call POST /documents/upload once,
then poll GET /documents/{id} until is_processed == "completed".
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.services.document import DocumentService, process_document_pipeline
from app.services.user import UserService
from app.api.v1.auth import get_current_user
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


async def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


# ── helpers ──────────────────────────────────────────────────────────────────

async def _require_admin(current_user_id: UUID, db: AsyncSession):
    user_service = UserService(db)
    user = await user_service.repo.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload documents",
        )
    return user


# ── routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to the knowledge base",
    description=(
        "Upload a PDF, DOCX, or TXT file (max 50 MB). "
        "Full text is extracted immediately and the chunk→embed pipeline "
        "runs in the background. Poll GET /documents/{id} until "
        "is_processed == 'completed' before using the document in chat."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    await _require_admin(current_user_id, db)

    try:
        document, _text = await document_service.upload_document(
            user_id=current_user_id,
            file=file,
        )

        # Auto-trigger the chunk→embed pipeline (non-blocking background task)
        background_tasks.add_task(process_document_pipeline, document.id)
        logger.info(f"Document uploaded: {document.filename} — pipeline queued")

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            file_size=document.file_size,
            is_processed=document.is_processed,
            total_chunks=document.total_chunks,
            created_at=document.created_at,
            message="Document uploaded. Processing started in background.",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading document",
        )


@router.get(
    "",
    response_model=list[DocumentListResponse],
    summary="List documents",
    description="Admins see all documents; students see only their own.",
)
async def list_documents(
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentListResponse]:
    try:
        user_service = UserService(db)
        user = await user_service.repo.get_user_by_id(current_user_id)

        if user and user.is_admin():
            documents = await document_service.get_all_documents()
        else:
            documents = await document_service.get_user_documents(current_user_id)

        return [
            DocumentListResponse(
                id=doc.id,
                filename=doc.filename,
                document_type=doc.document_type,
                file_size=doc.file_size,
                is_processed=doc.is_processed,
                total_chunks=doc.total_chunks,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing documents",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details",
)
async def get_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    try:
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Admins can see any document; others only their own
        user_service = UserService(db)
        user = await user_service.repo.get_user_by_id(current_user_id)
        if not (user and user.is_admin()) and document.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this document",
            )

        return DocumentDetailResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            file_size=document.file_size,
            content_preview=document.content_preview,
            is_processed=document.is_processed,
            total_chunks=document.total_chunks,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document",
        )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    await _require_admin(current_user_id, db)

    try:
        success = await document_service.delete_document(document_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or not authorized",
            )
        logger.info(f"Document deleted: {document_id}")
        return DocumentDeleteResponse(success=True, message="Document deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document",
        )
