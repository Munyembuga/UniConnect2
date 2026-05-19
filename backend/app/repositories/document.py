"""
Document repository for database operations on documents.
Handles document CRUD operations with async SQLAlchemy.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from loguru import logger

from app.models.document import Document, DocumentType


class DocumentRepository:
    """Repository for document database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(
        self,
        user_id: UUID,
        filename: str,
        document_type: DocumentType,
        file_path: str,
        file_size: int,
        content_preview: Optional[str] = None,
        extracted_text: Optional[str] = None,
    ) -> Document:
        """Create a new document record, storing the full extracted text."""
        try:
            db_document = Document(
                user_id=user_id,
                filename=filename,
                document_type=document_type,
                file_path=file_path,
                file_size=file_size,
                content_preview=content_preview,
                extracted_text=extracted_text,
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
        try:
            result = await self.db.execute(
                select(Document).where(Document.id == document_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    async def get_documents_by_user(self, user_id: UUID) -> List[Document]:
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

    async def get_all_documents(self) -> List[Document]:
        try:
            result = await self.db.execute(
                select(Document).order_by(Document.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error retrieving all documents: {e}")
            return []

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        total_chunks: int = None,
        extracted_text: Optional[str] = None,
    ) -> Optional[Document]:
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
