"""
Embedding service — generates vector embeddings via Google Gemini REST API or OpenAI.

Gemini embeddings use the v1 REST endpoint directly because the google-generativeai
SDK (0.8.x) routes embed_content calls to v1beta, where text-embedding-004 is not
supported.
"""
import requests
from typing import List
from loguru import logger
from app.core.config import settings

# Gemini v1beta REST endpoint — text-embedding-004 is broadly available on free-tier keys
_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
_GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:embedContent"
)

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False


class EmbeddingService:
    def __init__(self):
        self.provider = None

        if settings.GEMINI_API_KEY:
            self.provider = "genai"
            logger.info("Embedding provider: Google Gemini (text-embedding-004 via REST v1beta)")

        elif OPENAI_AVAILABLE and getattr(settings, "OPENAI_API_KEY", None):
            import openai as _openai
            _openai.api_key = settings.OPENAI_API_KEY
            self.provider = "openai"
            logger.info("Embedding provider: OpenAI")

        else:
            logger.warning(
                "No embedding provider configured — set GEMINI_API_KEY or "
                "OPENAI_API_KEY in .env. Embeddings will be unavailable."
            )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.provider == "genai":
            return self._embed_with_gemini(texts, task_type="RETRIEVAL_DOCUMENT")
        if self.provider == "openai":
            return self._embed_with_openai(texts)
        raise RuntimeError(
            "Embedding service is not configured. "
            "Add your GEMINI_API_KEY to the .env file and restart."
        )

    def embed_query(self, text: str) -> List[float]:
        if self.provider == "genai":
            results = self._embed_with_gemini([text], task_type="RETRIEVAL_QUERY")
            return results[0]
        if self.provider == "openai":
            import openai as _openai
            model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
            try:
                r = _openai.embeddings.create(model=model, input=[text])
                return r.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI query embedding error: {e}")
                raise
        raise RuntimeError("Embedding service is not configured.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed_with_gemini(self, texts: List[str], task_type: str) -> List[List[float]]:
        """
        Call the Gemini REST API for each text.
        Retries on 429 rate-limit errors with exponential back-off.
        Processes in batches of 10 with a 1-second pause between batches
        to stay within free-tier limits.
        """
        import time as _time

        BATCH_SIZE = 10
        MAX_RETRIES = 3
        embeddings = []

        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch = texts[batch_start: batch_start + BATCH_SIZE]
            for text in batch:
                last_exc = None
                for attempt in range(MAX_RETRIES):
                    try:
                        response = requests.post(
                            _GEMINI_EMBED_URL,
                            params={"key": settings.GEMINI_API_KEY},
                            json={
                                "model": _GEMINI_EMBED_MODEL,
                                "content": {"parts": [{"text": text}]},
                                "taskType": task_type,
                            },
                            timeout=30,
                        )
                        if response.status_code == 429:
                            wait = 15 * (attempt + 1)
                            try:
                                for d in response.json().get("error", {}).get("details", []):
                                    secs = (d.get("retryDelay") or "").replace("s", "")
                                    if secs.isdigit():
                                        wait = min(int(secs), 60)
                                        break
                            except Exception:
                                pass
                            logger.warning(
                                f"Embedding 429 rate limit — waiting {wait}s "
                                f"(attempt {attempt + 1}/{MAX_RETRIES})"
                            )
                            _time.sleep(wait)
                            continue
                        response.raise_for_status()
                        embeddings.append(response.json()["embedding"]["values"])
                        break
                    except Exception as e:
                        last_exc = e
                        if attempt < MAX_RETRIES - 1:
                            _time.sleep(5)
                        else:
                            logger.error(f"Gemini embedding error after {MAX_RETRIES} attempts: {e}")
                            raise
            # Brief pause between batches to respect rate limits
            if batch_start + BATCH_SIZE < len(texts):
                _time.sleep(1)

        return embeddings

    def _embed_with_openai(self, texts: List[str]) -> List[List[float]]:
        import openai as _openai
        model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        try:
            response = _openai.embeddings.create(model=model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
