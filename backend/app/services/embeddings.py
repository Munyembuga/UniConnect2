"""
Embedding service that generates vector embeddings using Gemini or OpenAI.
This module tries to use available SDKs; if not installed it raises informative errors.
"""
from typing import List, Optional
from loguru import logger
from app.core.config import settings

try:
    # try Google GenAI SDK
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

try:
    # try OpenAI
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


class EmbeddingService:
    def __init__(self):
        self.provider = None
        if GENAI_AVAILABLE and settings.GEMINI_API_KEY:
            self.provider = "genai"
            genai.configure(api_key=settings.GEMINI_API_KEY)
            logger.info("Using Google Generative AI for embeddings")
        elif OPENAI_AVAILABLE and getattr(settings, "OPENAI_API_KEY", None):
            self.provider = "openai"
            openai.api_key = settings.OPENAI_API_KEY
            logger.info("Using OpenAI for embeddings")
        else:
            logger.warning("No embedding provider configured (Gemini/OpenAI missing or no API key). Embeddings unavailable.")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for list of texts.
        Raises RuntimeError if no provider is available.
        """
        if self.provider == "genai":
            # Example using google-generativeai embeddings API
            # Note: actual call may vary depending on SDK version
            try:
                model = settings.GEMINI_EMBEDDING_MODEL if hasattr(settings, 'GEMINI_EMBEDDING_MODEL') else 'embed_text_v1'
                resp = genai.embeddings.create(model=model, input=texts)
                return [e.embedding for e in resp.embeddings]
            except Exception as e:
                logger.error(f"Gemini embedding error: {e}")
                raise
        elif self.provider == "openai":
            try:
                model = getattr(settings, 'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
                results = []
                for txt in texts:
                    r = openai.Embedding.create(model=model, input=txt)
                    results.append(r['data'][0]['embedding'])
                return results
            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                raise
        else:
            raise RuntimeError("No embedding provider configured. Set GEMINI_API_KEY or OPENAI_API_KEY in settings.")
