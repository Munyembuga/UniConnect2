"""
Document Upload API Router - v1

AUTH MODE: DEV BYPASS (no token required — swap dependency to restore auth)
  current: Depends(get_dev_user_id)
  restore: Depends(get_current_user)
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.services.document import DocumentService, process_document_pipeline
from app.api.v1.dev_auth import get_dev_user_id          # ← DEV: swap for get_current_user to restore auth
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
    summary="Upload a document to the knowledge base",
    description=(
        "Upload a PDF, DOCX, or TXT file (max 50 MB). "
        "Full text is extracted immediately and returned as `text_preview`. "
        "Chunking + embedding runs in the background. "
        "Poll **GET /documents/{id}** until `is_processed == 'completed'` "
        "before querying with **/chat/ask**."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    current_user_id: UUID = Depends(get_dev_user_id),   # ← DEV bypass
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    try:
        document, extracted_text = await document_service.upload_document(
            user_id=current_user_id,
            file=file,
        )

        # Trigger the chunk → embed → ChromaDB pipeline in the background
        background_tasks.add_task(process_document_pipeline, document.id)
        logger.info(f"Document uploaded: {document.filename} — pipeline queued")

        # Return first 500 chars of extracted text so you can verify extraction
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
                "✓ Text extracted successfully. "
                "Pipeline (chunk → embed) is running in the background. "
                "Poll GET /documents/{id} until is_processed == 'completed', "
                "then use POST /chat/ask to query the document."
                if preview
                else
                "⚠ Text extraction produced no content. Check the file format."
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
    summary="List all documents",
)
async def list_documents(
    current_user_id: UUID = Depends(get_dev_user_id),   # ← DEV bypass
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
    description="Poll this endpoint until `is_processed` becomes `completed` or `failed`.",
)
async def get_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_dev_user_id),   # ← DEV bypass
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
    summary="Delete a document",
)
async def delete_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_dev_user_id),   # ← DEV bypass
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    try:
        success = await document_service.delete_document(document_id, current_user_id)
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
