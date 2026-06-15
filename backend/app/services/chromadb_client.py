"""
ChromaDB client wrapper.
Supports the ChromaDB HTTP service (Docker) and falls back to a local
persistent store, then to an in-memory client for development.
Uses upsert so re-processing a document is always safe.
"""
from typing import List, Optional
from loguru import logger
from app.core.config import settings

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except Exception:
    CHROMADB_AVAILABLE = False


class ChromaClient:
    def __init__(self):
        self._collection_cache: dict = {}

        if not CHROMADB_AVAILABLE:
            logger.warning("chromadb library not installed — vector operations are no-ops.")
            self.client = None
            return

        self.client = self._build_client()

    # ------------------------------------------------------------------
    # Collection access
    # ------------------------------------------------------------------

    def get_or_create_collection(self, name: str):
        if not CHROMADB_AVAILABLE or self.client is None:
            raise RuntimeError("ChromaDB is not available")

        if name not in self._collection_cache:
            try:
                self._collection_cache[name] = self.client.get_or_create_collection(name)
            except Exception as e:
                logger.error(f"ChromaDB get_or_create_collection failed: {e}")
                raise
        return self._collection_cache[name]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[dict]] = None,
        documents: Optional[List[str]] = None,
    ):
        """
        Insert or update vectors in the collection.
        Using upsert (not add) so re-processing never raises duplicate errors.
        """
        if not CHROMADB_AVAILABLE or self.client is None:
            raise RuntimeError("ChromaDB is not available")

        col = self.get_or_create_collection(collection_name)
        col.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.debug(f"Upserted {len(ids)} vectors into ChromaDB collection '{collection_name}'")

    # ------------------------------------------------------------------
    # Read / Search
    # ------------------------------------------------------------------

    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """
        Find the top_k most similar vectors to query_embedding.
        Returns the raw ChromaDB result dict with keys: ids, documents, metadatas, distances.
        """
        if not CHROMADB_AVAILABLE or self.client is None:
            raise RuntimeError("ChromaDB is not available")

        col = self.get_or_create_collection(collection_name)
        kwargs = {"query_embeddings": [query_embedding], "n_results": top_k}
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self):
        """
        Try clients in order of preference:
          1. HTTP client  → production Docker (CHROMA_HOST / CHROMA_PORT)
          2. PersistentClient → local directory (new API >= 0.4.0)
          3. Legacy Client  → older chromadb versions
          4. EphemeralClient → pure in-memory fallback
        """
        # 1. HTTP/HTTPS (Docker or Render)
        try:
            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                ssl=settings.CHROMA_SSL,
            )
            client.heartbeat()
            proto = "https" if settings.CHROMA_SSL else "http"
            logger.info(f"ChromaDB: connected via {proto} ({settings.CHROMA_HOST}:{settings.CHROMA_PORT})")
            return client
        except Exception:
            pass

        # 2. PersistentClient (chromadb >= 0.4.0, local)
        try:
            client = chromadb.PersistentClient(path=str(settings.resolved_chroma_dir))
            logger.info(f"ChromaDB: using PersistentClient at {settings.resolved_chroma_dir}")
            return client
        except AttributeError:
            pass

        # 3. Legacy API (chromadb < 0.4.0)
        try:
            from chromadb.config import Settings as ChromaSettings
            client = chromadb.Client(
                ChromaSettings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(settings.resolved_chroma_dir),
                    anonymized_telemetry=False,
                )
            )
            logger.info("ChromaDB: using legacy duckdb+parquet client")
            return client
        except Exception:
            pass

        # 4. In-memory fallback
        try:
            client = chromadb.EphemeralClient()
            logger.warning("ChromaDB: using in-memory EphemeralClient — data will not persist!")
            return client
        except AttributeError:
            client = chromadb.Client()
            logger.warning("ChromaDB: using in-memory Client — data will not persist!")
            return client
