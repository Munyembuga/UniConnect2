"""
Document Upload API Router - v1
Endpoints for document upload, retrieval, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from app.db.session import get_db
from app.services.document import DocumentService
from app.services.user import UserService
from app.api.v1.auth import get_current_user
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentDeleteResponse,
)

# Create router
router = APIRouter(prefix="/documents", tags=["Documents"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """Dependency to provide DocumentService."""
    return DocumentService(db)


# ============================================================================
# ROUTES
# ============================================================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Upload a PDF, DOCX, or TXT file for processing",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, or TXT)"),
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """
    Upload a document.
    
    - **file**: PDF, DOCX, or TXT file (max 50MB)
    - **Authentication**: Required (Bearer token)
    
    Returns:
    - Document ID for future reference
    - Filename and file type
    - Processing status
    """
    try:
        # Verify user is admin
        user_service = UserService(db)
        user = await user_service.get_user(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        if not user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can upload documents",
            )
        
        # Upload document
        document, text_preview = await document_service.upload_document(
            user_id=current_user_id,
            file=file,
        )
        
        logger.info(f"Document uploaded: {document.filename} by user {current_user_id}")
        
        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            file_size=document.file_size,
            is_processed=document.is_processed,
            total_chunks=document.total_chunks,
            created_at=document.created_at,
        )
        
    except ValueError as e:
        logger.warning(f"File validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading document",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details",
    description="Retrieve detailed information about a document",
)
async def get_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    """
    Get details of a specific document.
    
    - **document_id**: UUID of the document
    - **Authentication**: Required
    
    Returns:
    - Document details including processing status
    """
    try:
        document = await document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        
        # Verify user is admin or document owner
        if document.user_id != current_user_id:
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


@router.get(
    "",
    response_model=list[DocumentListResponse],
    summary="List user documents",
    description="Get all documents uploaded by the current user",
)
async def list_documents(
    current_user_id: UUID = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentListResponse]:
    """
    List all documents uploaded by the current user.
    
    - **Authentication**: Required
    
    Returns:
    - List of documents with basic information
    """
    try:
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


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
    description="Delete a document and remove it from storage",
)
async def delete_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    """
    Delete a document.
    
    - **document_id**: UUID of document to delete
    - **Authentication**: Required
    
    Returns:
    - Success status
    """
    try:
        success = await document_service.delete_document(document_id, current_user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or not authorized",
            )
        
        logger.info(f"Document deleted: {document_id} by user {current_user_id}")
        
        return DocumentDeleteResponse(
            success=True,
            message="Document deleted successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document",
        )
