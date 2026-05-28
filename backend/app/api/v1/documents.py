"""
Document Upload API Router - v1

Auth rules:
  - Upload / List / Delete  → Admin only  (require_admin)
  - Get document details    → Any authenticated user (get_current_user)
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.services.document import DocumentService, process_document_pipeline
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


async def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


# ── routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to the knowledge base (Admin only)",
    description=(
        "**Admin only.** Upload a PDF, DOCX, or TXT file (max 50 MB). "
        "Full text is extracted immediately. "
        "Chunking + embedding runs in the background. "
        "Poll **GET /documents/{id}** until `is_processed == 'completed'`."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        document, extracted_text = await document_service.upload_document(
            user_id=admin.id,
            file=file,
        )
        background_tasks.add_task(process_document_pipeline, document.id)
        logger.info(f"Document uploaded by admin '{admin.email}': {document.filename}")

        preview = extracted_text[:500].strip() if extracted_text else None

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            file_size=document.file_size,
            is_processed=document.is_processed,
            total_chunks=document.total_chunks,
            created_at=document.created_at,
            text_preview=preview,
            message=(
                "✓ Text extracted. Pipeline (chunk → embed) running in background. "
                "Poll GET /documents/{id} until is_processed == 'completed'."
                if preview
                else "⚠ Text extraction produced no content. Check the file format."
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {e}",
        )


@router.get(
    "",
    response_model=list[DocumentListResponse],
    summary="List all documents (Admin only)",
)
async def list_documents(
    admin: User = Depends(require_admin),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentListResponse]:
    try:
        documents = await document_service.get_all_documents()
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
    summary="Get document details / check processing status",
    description="Any authenticated user can poll this to check processing status.",
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    try:
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

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
    summary="Delete a document (Admin only)",
)
async def delete_document(
    document_id: UUID,
    admin: User = Depends(require_admin),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    try:
        success = await document_service.delete_document(document_id, admin.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        return DocumentDeleteResponse(success=True, message="Document deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document",
        )
