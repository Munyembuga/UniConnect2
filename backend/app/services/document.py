"""
Document service for handling document uploads, text extraction, and the full
knowledge-base pipeline (chunk → embed → store in ChromaDB).
"""

import io
from typing import Optional, Tuple
from uuid import UUID
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.models.document import Document, DocumentType
from app.core.config import settings


class DocumentService:
    """Service for document handling and text extraction."""

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.upload_dir = Path(settings.UPLOAD_DIRECTORY)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload_document(
        self,
        user_id: UUID,
        file: UploadFile,
    ) -> Tuple[Document, str]:
        """
        Validate, save, and extract text from an uploaded file.
        Returns (Document, extracted_text). Caller schedules pipeline.
        """
        try:
            self._validate_file(file)

            content = await file.read()
            file_size = len(content)

            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"File size {file_size / 1024 / 1024:.1f} MB exceeds "
                    f"maximum of {self.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
                )

            file_ext = Path(file.filename).suffix.lower()
            document_type = self._get_document_type(file_ext)

            file_path = await self._save_file(user_id, file.filename, content)

            # Extract FULL text (not just a preview)
            full_text = await self._extract_full_text(document_type, content)

            document = await self.repo.create_document(
                user_id=user_id,
                filename=file.filename,
                document_type=document_type,
                file_path=str(file_path),
                file_size=file_size,
                content_preview=full_text[:500] if full_text else None,
                extracted_text=full_text,
            )

            logger.info(
                f"Document uploaded: {file.filename} (ID: {document.id}, "
                f"text_len={len(full_text) if full_text else 0})"
            )
            return document, full_text or ""

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            raise

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        return await self.repo.get_document_by_id(document_id)

    async def get_user_documents(self, user_id: UUID) -> list:
        return await self.repo.get_documents_by_user(user_id)

    async def get_all_documents(self) -> list:
        return await self.repo.get_all_documents()

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        try:
            document = await self.repo.get_document_by_id(document_id)
            if not document:
                return False
            if document.user_id != user_id:
                logger.warning(f"User {user_id} not authorized to delete {document_id}")
                return False

            try:
                file_path = Path(document.file_path)
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete file on disk: {e}")

            return await self.repo.delete_document(document_id)

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise ValueError("Filename is required")
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{file_ext}' not allowed. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )
        if file.size and file.size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum of {self.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
            )

    @staticmethod
    def _get_document_type(file_ext: str) -> DocumentType:
        return {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".txt": DocumentType.TXT,
        }.get(file_ext.lower(), DocumentType.TXT)

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    async def _save_file(self, user_id: UUID, filename: str, content: bytes) -> Path:
        user_dir = self.upload_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{user_id}_{filename}"
        file_path = user_dir / safe_filename
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"File saved: {file_path}")
        return file_path

    # ------------------------------------------------------------------
    # Full-text extraction (NO page/char limits — complete document)
    # ------------------------------------------------------------------

    async def _extract_full_text(
        self, document_type: DocumentType, content: bytes
    ) -> Optional[str]:
        try:
            if document_type == DocumentType.TXT:
                return content.decode("utf-8", errors="ignore").strip()

            if document_type == DocumentType.PDF:
                return await self._extract_pdf_text(content)

            if document_type == DocumentType.DOCX:
                return await self._extract_docx_text(content)

        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
        return None

    async def _extract_pdf_text(self, content: bytes) -> Optional[str]:
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            parts = []
            for page in reader.pages:          # ALL pages, no limit
                text = page.extract_text()
                if text:
                    parts.append(text)
            result = "\n".join(parts).strip()
            return result or None
        except Exception as e:
            logger.warning(f"PDF extraction error: {e}")
            return None

    async def _extract_docx_text(self, content: bytes) -> Optional[str]:
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(io.BytesIO(content))
            parts = []
            for paragraph in doc.paragraphs:   # ALL paragraphs, no limit
                if paragraph.text.strip():
                    parts.append(paragraph.text)
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            parts.append(cell.text)
            result = "\n".join(parts).strip()
            return result or None
        except Exception as e:
            logger.warning(f"DOCX extraction error: {e}")
            return None


# ---------------------------------------------------------------------------
# Standalone pipeline — runs as a FastAPI BackgroundTask with its own session
# ---------------------------------------------------------------------------

async def process_document_pipeline(document_id: UUID) -> None:
    """
    Full knowledge-base pipeline for a document:
      1. Chunk the extracted text
      2. Delete any previously stored chunks (safe re-processing)
      3. Persist new chunks to PostgreSQL
      4. Generate Gemini embeddings
      5. Upsert vectors into ChromaDB
      6. Mark document as completed (or failed)

    Creates its own DB session so it can run safely as a background task
    after the HTTP request that triggered it has already returned.
    """
    from app.db.database import AsyncSessionLocal
    from app.services.chunking import split_text
    from app.services.embeddings import EmbeddingService
    from app.services.chromadb_client import ChromaClient

    async with AsyncSessionLocal() as db:
        doc_repo = DocumentRepository(db)
        chunk_repo = DocumentChunkRepository(db)

        try:
            doc = await doc_repo.get_document_by_id(document_id)
            if not doc:
                logger.error(f"Pipeline: document {document_id} not found")
                return

            if not doc.extracted_text:
                logger.error(f"Pipeline: no extracted text for document {document_id}")
                await doc_repo.update_document_status(document_id, "failed")
                return

            await doc_repo.update_document_status(document_id, "processing")

            # 1. Split into chunks
            chunks_text = split_text(
                doc.extracted_text,
                settings.CHUNK_SIZE,
                settings.CHUNK_OVERLAP,
            )
            if not chunks_text:
                logger.error(f"Pipeline: chunking produced no chunks for {document_id}")
                await doc_repo.update_document_status(document_id, "failed")
                return

            # 2. Remove old chunks (idempotent re-processing)
            await chunk_repo.delete_by_document(document_id)

            # 3. Persist chunks
            db_chunks = await chunk_repo.create_chunks(document_id, chunks_text)

            # 4 & 5. Embed + store in ChromaDB
            embed_service = EmbeddingService()
            chroma = ChromaClient()

            texts = [c.content for c in db_chunks]
            ids = [str(c.id) for c in db_chunks]
            metadatas = [
                {
                    "source_type": "document",
                    "document_id": str(document_id),
                    "filename": doc.filename,
                    "chunk_index": c.chunk_index,
                }
                for c in db_chunks
            ]

            vectors = embed_service.embed_texts(texts)
            chroma.upsert(
                settings.CHROMA_COLLECTION_NAME,
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=texts,
            )

            # 6. Mark complete
            await doc_repo.update_document_status(
                document_id, "completed", total_chunks=len(db_chunks)
            )
            logger.info(
                f"Pipeline complete: document {document_id}, "
                f"{len(db_chunks)} chunks indexed"
            )

        except Exception as e:
            logger.error(f"Pipeline failed for document {document_id}: {e}")
            try:
                await doc_repo.update_document_status(document_id, "failed")
            except Exception:
                pass
