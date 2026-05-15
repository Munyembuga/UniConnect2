"""
Document repository for database operations on documents.
Handles document CRUD operations with async SQLAlchemy.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from loguru import logger

from app.models.document import Document, DocumentType
from app.schemas.document import DocumentUploadResponse


class DocumentRepository:
    """Repository for document database operations."""
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_document(
        self,
        user_id: UUID,
        filename: str,
        document_type: DocumentType,
        file_path: str,
        file_size: int,
        content_preview: Optional[str] = None,
    ) -> Document:
        """
        Create a new document record in the database.
        
        Args:
            user_id: ID of admin uploading document
            filename: Original filename
            document_type: Type of document (PDF, DOCX, TXT)
            file_path: Path where file is stored
            file_size: Size of file in bytes
            content_preview: Optional preview of content
            
        Returns:
            Created Document object
        """
        try:
            db_document = Document(
                user_id=user_id,
                filename=filename,
                document_type=document_type,
                file_path=file_path,
                file_size=file_size,
                content_preview=content_preview,
                is_processed="pending",
                total_chunks=0,
            )
            
            self.db.add(db_document)
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(db_document)
            
            logger.info(f"Document created: {db_document.filename} (ID: {db_document.id})")
            return db_document
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating document: {e}")
            raise

    async def get_document_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        Retrieve document by ID.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document object if found, None otherwise
        """
        try:
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    async def get_documents_by_user(self, user_id: UUID) -> List[Document]:
        """
        Retrieve all documents uploaded by a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of Document objects
        """
        try:
            result = await self.db.execute(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error retrieving documents for user {user_id}: {e}")
            return []

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        total_chunks: int = None,
        extracted_text: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Update document processing status and chunks.
        
        Args:
            document_id: Document UUID
            status: New processing status
            total_chunks: Number of chunks created
            extracted_text: Extracted text content
            
        Returns:
            Updated Document object if found
        """
        try:
            document = await self.get_document_by_id(document_id)
            if not document:
                logger.warning(f"Document not found for update: {document_id}")
                return None
            
            document.is_processed = status
            if total_chunks is not None:
                document.total_chunks = total_chunks
            if extracted_text is not None:
                document.extracted_text = extracted_text
            
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
            
            logger.info(f"Document updated: {document_id}, status: {status}")
            return document
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating document {document_id}: {e}")
            raise

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete a document by ID.
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            document = await self.get_document_by_id(document_id)
            if not document:
                logger.warning(f"Document not found for deletion: {document_id}")
                return False
            
            await self.db.delete(document)
            await self.db.commit()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting document {document_id}: {e}")
            raise

    async def get_all_documents(self) -> List[Document]:
        """
        Retrieve all documents (admin only).
        
        Returns:
            List of all Document objects
        """
        try:
            result = await self.db.execute(
                select(Document).order_by(Document.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            return []
