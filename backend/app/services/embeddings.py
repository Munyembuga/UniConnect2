"""
Embedding service — generates vector embeddings via Google Gemini or OpenAI.
"""
from typing import List
from loguru import logger
from app.core.config import settings

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# Gemini's text-embedding model name
_GEMINI_EMBEDDING_MODEL = "models/embedding-001"


class EmbeddingService:
    def __init__(self):
        self.provider = None

        if GENAI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.provider = "genai"
            logger.info("Embedding provider: Google Gemini")

        elif OPENAI_AVAILABLE and getattr(settings, "OPENAI_API_KEY", None):
            openai.api_key = settings.OPENAI_API_KEY
            self.provider = "openai"
            logger.info("Embedding provider: OpenAI")

        else:
            logger.warning(
                "No embedding provider configured — set GEMINI_API_KEY or "
                "OPENAI_API_KEY in .env. Embeddings will be unavailable."
            )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Return a list of embedding vectors, one per input text.
        Raises RuntimeError if no provider is configured.
        """
        if not texts:
            return []

        if self.provider == "genai":
            return self._embed_with_gemini(texts)

        if self.provider == "openai":
            return self._embed_with_openai(texts)

        raise RuntimeError(
            "No embedding provider configured. "
            "Add GEMINI_API_KEY or OPENAI_API_KEY to your .env file."
        )

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string (used at chat/search time)."""
        if self.provider == "genai":
            try:
                result = genai.embed_content(
                    model=_GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_query",
                )
                return result["embedding"]
            except Exception as e:
                logger.error(f"Gemini query embedding error: {e}")
                raise

        if self.provider == "openai":
            try:
                model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                r = openai.embeddings.create(model=model, input=[text])
                return r.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI query embedding error: {e}")
                raise

        raise RuntimeError("No embedding provider configured.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed_with_gemini(self, texts: List[str]) -> List[List[float]]:
        """
        Gemini embedding via google-generativeai SDK.
        The SDK does not support true batch embedding, so we loop.
        task_type="retrieval_document" is correct for knowledge-base content.
        """
        embeddings = []
        for text in texts:
            try:
                result = genai.embed_content(
                    model=_GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document",
                )
                embeddings.append(result["embedding"])
            except Exception as e:
                logger.error(f"Gemini embedding error on chunk: {e}")
                raise
        return embeddings

    def _embed_with_openai(self, texts: List[str]) -> List[List[float]]:
        """OpenAI batch embedding (supports true batching)."""
        try:
            model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            response = openai.embeddings.create(model=model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
