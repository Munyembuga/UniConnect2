"""
ChromaDB client wrapper.
Wraps chromadb client usage so rest of code can import safely.
"""
from typing import List, Optional
from loguru import logger
from app.core.config import settings

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.api import Collection
    CHROMADB_AVAILABLE = True
except Exception:
    CHROMADB_AVAILABLE = False


class ChromaClient:
    def __init__(self):
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB is not installed; operations will be no-ops.")
            self.client = None
            self._collection = None
            return

        # Default client: local persistent directory or in-memory
        try:
            self.client = chromadb.Client(ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=settings.CHROMA_PERSIST_DIR if hasattr(settings,'CHROMA_PERSIST_DIR') else None))
        except Exception:
            # Fallback to default client
            self.client = chromadb.Client()

        self._collection = None

    def get_or_create_collection(self, name: str):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB library is not available")

        if self._collection is None:
            try:
                self._collection = self.client.get_collection(name)
            except Exception:
                self._collection = self.client.create_collection(name)
        return self._collection

    def upsert(self, collection_name: str, ids: List[str], embeddings: List[List[float]], metadatas: Optional[List[dict]] = None, documents: Optional[List[str]] = None):
        """Upsert embeddings into chroma collection."""
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB library is not available")

        col = self.get_or_create_collection(collection_name)
        return col.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(self, collection_name: str, query_embeddings: List[float], top_k: int = 5):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB library is not available")
        col = self.get_or_create_collection(collection_name)
        return col.query(query_embeddings=[query_embeddings], n_results=top_k)
