"""
Chat / Q&A service.

Flow:
  1. Detect if the question is general/conversational (greetings, identity, date, etc.)
     → answer directly with Gemini, no RAG needed.
  2. Otherwise run the full Hybrid RAG pipeline:
       a. Vector search  — embed question → ChromaDB semantic search
       b. Keyword search — PostgreSQL full-text search (tsvector/tsquery)
       c. RRF merge      — Reciprocal Rank Fusion combines both result lists
       d. Gemini         — generates grounded answer from merged top chunks
"""
import re
import time
from datetime import date
from typing import Dict, List, Tuple
from loguru import logger

from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.chromadb_client import ChromaClient


# ---------------------------------------------------------------------------
# General-question detection
# ---------------------------------------------------------------------------

# Patterns that classify a question as general/conversational.
# Checked against the lowercased, stripped question text.
_GENERAL_PATTERNS = [
    # greetings
    r"^(hi|hello|hey|hiya|howdy|greetings|yo)\b",
    r"^(good\s+(morning|afternoon|evening|night|day))\b",
    # farewells
    r"^(bye|goodbye|see\s+you|take\s+care|cya|see\s+ya)\b",
    # well-being
    r"\bhow\s+are\s+you\b",
    r"\bhow'?s\s+it\s+going\b",
    r"\bhow\s+do\s+you\s+do\b",
    r"\bare\s+you\s+(ok|okay|doing\s+well|fine|good)\b",
    # identity / capability
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+(is\s+)?your\s+name\b",
    r"\bwhat\s+are\s+you\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\btell\s+me\s+about\s+yourself\b",
    # date / time
    r"\bwhat\s+(is\s+|'?s\s+)?(today'?s?\s+)?date\b",
    r"\bwhat\s+day\s+is\s+(it|today)\b",
    r"\bwhat\s+time\s+is\s+it\b",
    r"\bcurrent\s+(date|time|day)\b",
    r"\btoday'?s?\s+date\b",
    # thanks
    r"^(thanks|thank\s+you|thank\s+u|thx|cheers|appreciated)\b",
    # help
    r"^help$",
    r"\bwhat\s+can\s+you\s+help\b",
]
_GENERAL_RE = [re.compile(p, re.IGNORECASE) for p in _GENERAL_PATTERNS]


def _is_general_question(question: str) -> bool:
    """Return True if the question is conversational and needs no knowledge base."""
    q = question.strip()
    return any(rx.search(q) for rx in _GENERAL_RE)


def _answer_general_question(question: str) -> dict:
    """
    Answer a conversational question directly with Gemini.
    No embedding or ChromaDB lookup needed.
    """
    today = date.today().strftime("%A, %B %d, %Y")

    prompt = (
        f"You are UniConnect, a friendly AI assistant for university students. "
        f"Today's date is {today}.\n\n"
        f"The student says: \"{question}\"\n\n"
        f"Reply naturally and concisely (1–3 sentences). "
        f"If asked who you are, say you are UniConnect, an AI assistant that helps "
        f"students by answering questions about uploaded university documents and general queries. "
        f"If asked what you can do, briefly describe: answer questions from uploaded documents, "
        f"provide the current date, and handle general conversation."
    )

    try:
        return {
            "answer": _call_gemini(prompt),
            "sources": [],
            "confidence": 1.0,
            "error": None,
        }
    except Exception as e:
        logger.error(f"General question Gemini call failed: {e}")
        fallback = _static_fallback(question, today)
        return {"answer": fallback, "sources": [], "confidence": 1.0, "error": None}


def _static_fallback(question: str, today: str) -> str:
    """Return a canned answer when Gemini is unreachable."""
    q = question.lower()
    if any(w in q for w in ["date", "day", "time"]):
        return f"Today is {today}."
    if any(w in q for w in ["who are you", "your name", "what are you"]):
        return (
            "I'm UniConnect, an AI assistant that helps university students "
            "find answers in uploaded documents and handles general questions."
        )
    if any(w in q for w in ["what can you do", "how can you help", "what do you do"]):
        return (
            "I can help you in two ways: "
            "(1) answer questions about documents you upload to the knowledge base, and "
            "(2) handle general questions like greetings, today's date, or information about me. "
            "Upload a PDF, DOCX, or TXT file and then ask me anything about it!"
        )
    if any(w in q for w in ["bye", "goodbye"]):
        return "Goodbye! Feel free to come back whenever you have more questions."
    if any(w in q for w in ["thank"]):
        return "You're welcome! Let me know if there's anything else I can help with."
    # default greeting
    return "Hello! I'm UniConnect, your university AI assistant. How can I help you today?"


# ---------------------------------------------------------------------------
# Shared Gemini call with automatic 429 retry
# ---------------------------------------------------------------------------

_GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


def _call_gemini(prompt: str, retries: int = 3) -> str:
    """
    Call Gemini generateContent via direct REST API (v1beta).
    Retries on 429 (rate limit) and 503 (overload), then falls back to
    alternative models if the primary model keeps failing.
    """
    import requests as _requests

    models_to_try = [settings.GEMINI_MODEL] + [
        m for m in _GEMINI_FALLBACK_MODELS if m != settings.GEMINI_MODEL
    ]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
    }

    last_exc = None
    for model in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        for attempt in range(retries + 1):
            try:
                resp = _requests.post(
                    url,
                    params={"key": settings.GEMINI_API_KEY},
                    json=payload,
                    timeout=60,
                )
                if resp.status_code in (429, 503):
                    if attempt < retries:
                        wait = 10 if resp.status_code == 503 else 15
                        try:
                            for d in resp.json().get("error", {}).get("details", []):
                                secs = (d.get("retryDelay") or "").replace("s", "")
                                if secs.isdigit():
                                    wait = min(int(secs), 60)
                                    break
                        except Exception:
                            pass
                        logger.warning(
                            f"Gemini {resp.status_code} on {model} — "
                            f"waiting {wait}s (attempt {attempt + 1}/{retries})"
                        )
                        time.sleep(wait)
                        continue
                    # exhausted retries on this model — try next
                    last_exc = Exception(f"{resp.status_code} {resp.text[:200]}")
                    break
                resp.raise_for_status()
                data = resp.json()
                if model != settings.GEMINI_MODEL:
                    logger.info(f"Used fallback model: {model}")
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(5)
                    continue
                break  # try next model
    raise last_exc or RuntimeError("All Gemini models failed")


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (RRF)
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    vector_docs: List[str],
    keyword_docs: List[Tuple[str, float]],
    k: int = 60,
    top_n: int = 5,
) -> List[str]:
    """
    Merge vector-search results and keyword-search results into one ranked list.

    RRF score for a document = Σ  1 / (k + rank_in_source)

    A document appearing in both sources scores higher than one appearing
    in only one — naturally rewarding overlap between semantic and lexical matches.

    Args:
        vector_docs:   Ordered list of chunk texts from ChromaDB (index 0 = best).
        keyword_docs:  List of (chunk_text, bm25_score) from PostgreSQL FTS.
        k:             RRF constant (default 60 per the original paper).
        top_n:         How many merged results to return.
    """
    scores: Dict[str, float] = {}

    for rank, doc in enumerate(vector_docs):
        scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)

    for rank, (doc, _) in enumerate(keyword_docs):
        scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_n]]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def ask_question(question: str) -> dict:
    """
    Route the question:
      • general / conversational  → direct Gemini answer
      • knowledge-base question   → Hybrid RAG (vector + keyword, merged via RRF)
    """

    # ── 0. General question shortcut ────────────────────────────────────────
    if _is_general_question(question):
        logger.info(f"General question detected, skipping RAG: '{question[:60]}'")
        return _answer_general_question(question)

    # ── 1. Vector search (ChromaDB) ──────────────────────────────────────────
    vector_docs: List[str] = []
    best_similarity: float = 0.0

    try:
        embed_service = EmbeddingService()
        query_vector = embed_service.embed_query(question)
        chroma = ChromaClient()
        results = chroma.query(
            settings.CHROMA_COLLECTION_NAME,
            query_embedding=query_vector,
            top_k=settings.SIMILARITY_TOP_K,
        )
        documents_list = (results.get("documents") or [[]])[0]
        distances_list = (results.get("distances") or [[]])[0]

        def to_similarity(dist: float) -> float:
            return max(0.0, round(1.0 - dist / 2.0, 3))

        if distances_list:
            best_similarity = to_similarity(distances_list[0])

        vector_docs = [
            doc for doc, dist in zip(documents_list, distances_list)
            if to_similarity(dist) >= settings.CONFIDENCE_THRESHOLD
        ]
        logger.info(f"Vector search: {len(vector_docs)} relevant chunks (best={best_similarity:.0%})")

    except RuntimeError:
        return {
            "answer": None, "sources": [], "confidence": 0.0,
            "error": "Embedding service not configured. Add GEMINI_API_KEY and restart.",
        }
    except Exception as e:
        logger.warning(f"Vector search failed: {e} — falling back to keyword only")

    # ── 2. Keyword search (PostgreSQL full-text) ─────────────────────────────
    keyword_results: List[Tuple[str, float]] = []

    try:
        from app.db.database import AsyncSessionLocal
        from app.repositories.document_chunk import DocumentChunkRepository

        async with AsyncSessionLocal() as db:
            chunk_repo = DocumentChunkRepository(db)
            raw = await chunk_repo.keyword_search(question, top_k=settings.SIMILARITY_TOP_K)
            keyword_results = [(chunk.content, score) for chunk, score in raw]
        logger.info(f"Keyword search: {len(keyword_results)} chunks matched")

    except Exception as e:
        logger.warning(f"Keyword search failed: {e} — using vector results only")

    # ── 3. Check we have something ───────────────────────────────────────────
    if not vector_docs and not keyword_results:
        return {
            "answer": (
                "No relevant content found. Make sure at least one document is fully "
                "processed (is_processed == 'completed'), then try again."
            ),
            "sources": [], "confidence": best_similarity, "error": None,
        }

    # ── 4. Merge with Reciprocal Rank Fusion ─────────────────────────────────
    merged = _reciprocal_rank_fusion(vector_docs, keyword_results, top_n=5)

    # If RRF returned nothing (edge case), fall back to whichever list has data
    if not merged:
        merged = vector_docs[:5] or [doc for doc, _ in keyword_results[:5]]

    logger.info(
        f"Hybrid search merged {len(merged)} chunks "
        f"(vector={len(vector_docs)}, keyword={len(keyword_results)})"
    )

    # ── 5. Build prompt & call Gemini ─────────────────────────────────────────
    context_text = "\n\n---\n\n".join(merged)

    prompt = (
        "You are a strict document-based AI assistant.\n\n"
        "Answer questions using ONLY the context provided. Never use outside knowledge.\n\n"
        "## ANSWER LENGTH RULES (follow strictly):\n"
        "- Single value (ID, number, name, date, price) → ONE short sentence only.\n"
        "  Example: 'The National ID is 1200580041943090.'\n"
        "- Factual question → 1–2 sentences maximum.\n"
        "- List/explain question → 3–5 bullet points, one line each.\n"
        "- NEVER write more than is needed to answer the question.\n\n"
        "## OTHER RULES:\n"
        "- Use ONLY the relevant part of the context. Ignore unrelated text.\n"
        "- Do NOT copy large chunks of text from the context.\n"
        "- Do NOT repeat the question or add preamble like 'Based on the document...'.\n"
        "- If the answer is not in the context: 'I could not find the exact answer in the document.'\n"
        "- If the question is unclear: ask one clarification question.\n\n"
        "## CONTEXT:\n"
        f"{context_text}\n\n"
        f"## QUESTION:\n{question}\n\n"
        "## ANSWER (be as short as possible):"
    )

    try:
        answer = _call_gemini(prompt)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return {
            "answer": None,
            "sources": merged[:3],
            "confidence": best_similarity,
            "error": f"AI generation failed: {e}",
        }

    return {
        "answer": answer,
        "sources": merged[:3],
        "confidence": best_similarity,
        "error": None,
    }
