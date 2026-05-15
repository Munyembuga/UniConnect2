"""
Document service for handling document uploads and text extraction.
Manages file upload processing and extraction business logic.
"""

import os
import io
from typing import Optional, Tuple
from uuid import UUID
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.document import DocumentRepository
from app.models.document import Document, DocumentType
from app.core.config import settings


class DocumentService:
    """Service for document handling and text extraction."""
    
    # Maximum file size in bytes (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session and repository."""
        self.db = db
        self.repo = DocumentRepository(db)
        self.upload_dir = Path(settings.UPLOAD_DIRECTORY)
        
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        user_id: UUID,
        file: UploadFile,
    ) -> Tuple[Document, str]:
        """
        Handle document upload and save to storage.
        
        Args:
            user_id: ID of admin uploading document
            file: Uploaded file object
            
        Returns:
            Tuple of (Document object, extracted text preview)
            
        Raises:
            ValueError: If file validation fails
        """
        try:
            # Validate file
            self._validate_file(file)
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Determine document type
            file_ext = Path(file.filename).suffix.lower()
            document_type = self._get_document_type(file_ext)
            
            # Generate file path
            file_path = await self._save_file(user_id, file.filename, content)
            
            # Extract text preview
            text_preview = await self._extract_text_preview(
                document_type,
                content,
                file.filename,
            )
            
            # Create document record
            document = await self.repo.create_document(
                user_id=user_id,
                filename=file.filename,
                document_type=document_type,
                file_path=str(file_path),
                file_size=file_size,
                content_preview=text_preview[:500] if text_preview else None,
            )
            
            logger.info(f"Document uploaded successfully: {file.filename} (ID: {document.id})")
            return document, text_preview
            
        except ValueError as e:
            logger.warning(f"File validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during document upload: {e}")
            raise

    def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file.
        
        Args:
            file: Uploaded file to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check filename
        if not file.filename:
            raise ValueError("Filename is required")
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type {file_ext} not allowed. Allowed: {self.ALLOWED_EXTENSIONS}")
        
        # Check file size (will be checked after reading)
        if file.size and file.size > self.MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum of {self.MAX_FILE_SIZE / 1024 / 1024:.1f}MB")

    def _get_document_type(self, file_ext: str) -> DocumentType:
        """
        Determine document type from file extension.
        
        Args:
            file_ext: File extension (e.g., '.pdf')
            
        Returns:
            DocumentType enum value
        """
        extension_map = {
            '.pdf': DocumentType.PDF,
            '.docx': DocumentType.DOCX,
            '.txt': DocumentType.TXT,
        }
        return extension_map.get(file_ext.lower(), DocumentType.TXT)

    async def _save_file(self, user_id: UUID, filename: str, content: bytes) -> Path:
        """
        Save uploaded file to storage.
        
        Args:
            user_id: User ID for organizing files
            filename: Original filename
            content: File content as bytes
            
        Returns:
            Path to saved file
        """
        try:
            # Create user directory
            user_dir = self.upload_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_filename = f"{user_id}_{filename}"
            file_path = user_dir / safe_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"File saved to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise

    async def _extract_text_preview(
        self,
        document_type: DocumentType,
        content: bytes,
        filename: str,
    ) -> Optional[str]:
        """
        Extract text preview from document.
        
        Args:
            document_type: Type of document
            content: File content as bytes
            filename: Original filename
            
        Returns:
            Extracted text preview, or None if extraction fails
        """
        try:
            if document_type == DocumentType.TXT:
                # Simple text extraction for TXT files
                return content.decode('utf-8', errors='ignore')[:500]
            
            elif document_type == DocumentType.DOCX:
                # DOCX extraction
                return await self._extract_docx_text(content)
            
            elif document_type == DocumentType.PDF:
                # PDF extraction
                return await self._extract_pdf_text(content)
            
            else:
                logger.warning(f"Unknown document type: {document_type}")
                return None
                
        except Exception as e:
            logger.warning(f"Error extracting text preview: {e}")
            return None

    async def _extract_pdf_text(self, content: bytes) -> Optional[str]:
        """
        Extract text from PDF file.
        
        Args:
            content: PDF file content as bytes
            
        Returns:
            Extracted text, or None if extraction fails
        """
        try:
            from PyPDF2 import PdfReader
            
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            
            text = ""
            # Extract text from first 5 pages max for preview
            for i, page in enumerate(reader.pages[:5]):
                text += page.extract_text()
                if len(text) > 2000:
                    break
            
            return text[:500] if text else None
            
        except Exception as e:
            logger.warning(f"Error extracting PDF text: {e}")
            return None

    async def _extract_docx_text(self, content: bytes) -> Optional[str]:
        """
        Extract text from DOCX file.
        
        Args:
            content: DOCX file content as bytes
            
        Returns:
            Extracted text, or None if extraction fails
        """
        try:
            from docx import Document as DocxDocument
            
            docx_file = io.BytesIO(content)
            doc = DocxDocument(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
                if len(text) > 2000:
                    break
            
            return text[:500] if text else None
            
        except Exception as e:
            logger.warning(f"Error extracting DOCX text: {e}")
            return None

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        Retrieve document by ID.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document object if found
        """
        return await self.repo.get_document_by_id(document_id)

    async def get_user_documents(self, user_id: UUID) -> list:
        """
        Get all documents uploaded by a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of documents
        """
        return await self.repo.get_documents_by_user(user_id)

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """
        Delete a document (verify user ownership).
        
        Args:
            document_id: Document UUID
            user_id: User UUID (for ownership verification)
            
        Returns:
            True if deleted successfully
        """
        try:
            document = await self.repo.get_document_by_id(document_id)
            if not document:
                logger.warning(f"Document not found: {document_id}")
                return False
            
            # Verify ownership
            if document.user_id != user_id:
                logger.warning(f"User {user_id} not authorized to delete document {document_id}")
                return False
            
            # Delete file from storage
            try:
                file_path = Path(document.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"File deleted: {file_path}")
            except Exception as e:
                logger.warning(f"Error deleting file: {e}")
            
            # Delete from database
            return await self.repo.delete_document(document_id)
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
