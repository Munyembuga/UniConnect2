"""
Chat / Q&A service.

Flow for every question:
  0. Check if an admin has already answered a similar question → return admin answer.
  1. Detect general/conversational questions → answer directly (no RAG needed).
  2. Hybrid RAG pipeline:
       a. Vector search  — embed question → ChromaDB semantic search
       b. Keyword search — PostgreSQL full-text search (tsvector/tsquery)
       c. RRF merge      — Reciprocal Rank Fusion combines both result lists
       d. Gemini — generates grounded answer from merged top chunks
  3. Save result to chat_history.
  4. If confidence is low or no answer found → flag as unresolved question for admin.
"""
import re
import time
from datetime import date
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.chromadb_client import ChromaClient


# ---------------------------------------------------------------------------
# General-question detection
# ---------------------------------------------------------------------------

_GENERAL_PATTERNS = [
    r"^(hi|hello|hey|hiya|howdy|greetings|yo)\b",
    r"^(good\s+(morning|afternoon|evening|night|day))\b",
    r"^(bye|goodbye|see\s+you|take\s+care|cya|see\s+ya)\b",
    r"\bhow\s+are\s+you\b",
    r"\bhow'?s\s+it\s+going\b",
    r"\bhow\s+do\s+you\s+do\b",
    r"\bare\s+you\s+(ok|okay|doing\s+well|fine|good)\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+(is\s+)?your\s+name\b",
    r"\bwhat\s+are\s+you\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\btell\s+me\s+about\s+yourself\b",
    r"\bwhat\s+(is\s+|'?s\s+)?(today'?s?\s+)?date\b",
    r"\bwhat\s+day\s+is\s+(it|today)\b",
    r"\bwhat\s+time\s+is\s+it\b",
    r"\bcurrent\s+(date|time|day)\b",
    r"\btoday'?s?\s+date\b",
    r"^(thanks|thank\s+you|thank\s+u|thx|cheers|appreciated)\b",
    r"^help$",
    r"\bwhat\s+can\s+you\s+help\b",
]
_GENERAL_RE = [re.compile(p, re.IGNORECASE) for p in _GENERAL_PATTERNS]


def _is_general_question(question: str) -> bool:
    q = question.strip()
    return any(rx.search(q) for rx in _GENERAL_RE)


def _static_fallback(question: str, today: str) -> str:
    """Canned answer when all AI providers are unreachable."""
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
            "(1) answer questions about documents uploaded to the knowledge base, and "
            "(2) handle general questions like greetings, today's date, or who I am. "
            "Ask me anything about your university documents!"
        )
    if any(w in q for w in ["bye", "goodbye"]):
        return "Goodbye! Feel free to come back whenever you have more questions."
    if any(w in q for w in ["thank"]):
        return "You're welcome! Let me know if there's anything else I can help with."
    return "Hello! I'm UniConnect, your university AI assistant. How can I help you today?"


def _answer_general_question(question: str) -> dict:
    """Answer a conversational question — tries AI, falls back to static."""
    today = date.today().strftime("%A, %B %d, %Y")
    fallback = _static_fallback(question, today)

    prompt = (
        f"You are UniConnect, a friendly AI assistant for university students. "
        f"Today's date is {today}.\n\n"
        f"IMPORTANT: Detect the language the student is using and respond in that exact same language.\n\n"
        f"The student says: \"{question}\"\n\n"
        f"Reply naturally and concisely (1–3 sentences) in the same language the student used. "
        f"If asked who you are, say you are UniConnect, an AI assistant that helps "
        f"students by answering questions about uploaded university documents and general queries. "
        f"If asked what you can do, briefly describe: answer questions from uploaded documents, "
        f"provide the current date, and handle general conversation."
    )
    try:
        return {
            "answer": _call_ai(prompt),
            "sources": [],
            "confidence": 1.0,
            "error": None,
            "answered_by": "ai",
        }
    except Exception as e:
        logger.warning(f"AI unavailable for general question, using static fallback: {e}")
        return {"answer": fallback, "sources": [], "confidence": 1.0, "error": None, "answered_by": "static"}


# ---------------------------------------------------------------------------
# AI generation — OpenRouter (primary) → Gemini (fallback)
# ---------------------------------------------------------------------------

_GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
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
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }

    last_exc = None
    for model in models_to_try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        try:
            resp = _requests.post(
                url,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
                timeout=60,
            )
            if resp.status_code in (429, 503):
                last_exc = Exception(f"{resp.status_code} {resp.text[:200]}")
                logger.warning(f"Gemini {resp.status_code} on {model} — trying next model")
                continue
            resp.raise_for_status()
            data = resp.json()
            if model != settings.GEMINI_MODEL:
                logger.info(f"Used fallback model: {model}")
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            last_exc = e
            continue

    raise last_exc or RuntimeError("All Gemini models failed")


def _call_openrouter(prompt: str) -> str:
    """Call OpenRouter chat completions (OpenAI-compatible API)."""
    import openai as _openai

    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    client = _openai.OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def _call_ai(prompt: str) -> str:
    """Try OpenRouter first; fall back to Gemini if it fails."""
    if settings.OPENROUTER_API_KEY:
        try:
            return _call_openrouter(prompt)
        except Exception as e:
            logger.warning(f"OpenRouter failed ({e}), falling back to Gemini")
    return _call_gemini(prompt)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (RRF)
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    vector_docs: List[str],
    keyword_docs: List[Tuple[str, float]],
    k: int = 60,
    top_n: int = 5,
) -> List[str]:
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

async def ask_question(
    question: str,
    user_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Route the question through the full pipeline and save results.

    Args:
        question:  The student's question.
        user_id:   ID of the authenticated user asking the question.
        db:        Async DB session (used for chat history + unresolved questions).

    Returns:
        dict with keys: answer, sources, confidence, error, answered_by
    """
    from app.repositories.chat_history import ChatHistoryRepository
    from app.repositories.unresolved_question import UnresolvedQuestionRepository

    ch_repo = ChatHistoryRepository(db)
    uq_repo = UnresolvedQuestionRepository(db)

    # ── 0. Check admin-answered questions ────────────────────────────────────
    try:
        admin_match = await uq_repo.find_answered_similar(question)
    except Exception:
        admin_match = None

    if admin_match:
        logger.info(f"Returning admin answer for: '{question[:60]}'")
        await ch_repo.create(
            user_id=user_id,
            question=question,
            answer=admin_match.admin_answer,
            sources=[],
            confidence_score=1.0,
            is_resolved="resolved",
        )
        return {
            "answer": admin_match.admin_answer,
            "sources": [],
            "confidence": 1.0,
            "error": None,
            "answered_by": "admin",
        }

    # ── 1. General question shortcut ─────────────────────────────────────────
    if _is_general_question(question):
        logger.info(f"General question detected, skipping RAG: '{question[:60]}'")
        result = _answer_general_question(question)
        await ch_repo.create(
            user_id=user_id,
            question=question,
            answer=result["answer"],
            sources=[],
            confidence_score=1.0,
            is_resolved="resolved",
        )
        return result

    # ── 2. Vector search (ChromaDB) ──────────────────────────────────────────
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
            "error": "Embedding service not configured. Add GEMINI_API_KEY or OPENAI_API_KEY and restart.",
            "answered_by": "error",
        }
    except Exception as e:
        logger.warning(f"Vector search failed: {e} — falling back to keyword only")

    # ── 3. Keyword search (PostgreSQL full-text) ─────────────────────────────
    keyword_results: List[Tuple[str, float]] = []
    try:
        from app.repositories.document_chunk import DocumentChunkRepository
        chunk_repo = DocumentChunkRepository(db)
        raw = await chunk_repo.keyword_search(question, top_k=settings.SIMILARITY_TOP_K)
        keyword_results = [(chunk.content, score) for chunk, score in raw]
        logger.info(f"Keyword search: {len(keyword_results)} chunks matched")
    except Exception as e:
        logger.warning(f"Keyword search failed: {e} — using vector results only")

    # ── 4. Check we have context ─────────────────────────────────────────────
    if not vector_docs and not keyword_results:
        no_answer = (
            "No relevant content found in the knowledge base. "
            "Please make sure a document has been uploaded and fully processed."
        )
        chat = await ch_repo.create(
            user_id=user_id,
            question=question,
            answer=no_answer,
            sources=[],
            confidence_score=best_similarity,
            is_resolved="unresolved",
        )
        await uq_repo.create(
            chat_history_id=chat.id,
            user_id=user_id,
            question=question,
            ai_attempt=no_answer,
            confidence_score=best_similarity,
        )
        return {
            "answer": no_answer,
            "sources": [], "confidence": best_similarity, "error": None,
            "answered_by": "system",
        }

    # ── 5. Merge with RRF ────────────────────────────────────────────────────
    merged = _reciprocal_rank_fusion(vector_docs, keyword_results, top_n=5)
    if not merged:
        merged = vector_docs[:5] or [doc for doc, _ in keyword_results[:5]]
    logger.info(
        f"Hybrid search merged {len(merged)} chunks "
        f"(vector={len(vector_docs)}, keyword={len(keyword_results)})"
    )

    # ── 6. Build prompt & call AI ─────────────────────────────────────────────
    context_text = "\n\n---\n\n".join(merged)
    prompt = (
        "You are an expert academic assistant helping university students understand documents.\n\n"
        "You have been given relevant excerpts from a document. Your job is to READ and REASON "
        "over these excerpts to provide a clear, well-structured answer to the student's question.\n\n"
        "IMPORTANT: Detect the language the student used in their question and write your entire "
        "answer in that same language (e.g. if they wrote in French, answer in French; "
        "if Kinyarwanda, answer in Kinyarwanda; if English, answer in English).\n\n"
        "## INSTRUCTIONS:\n"
        "- Analyse the context carefully and synthesise the information — do NOT just copy or paste text.\n"
        "- Use your reasoning to explain concepts, steps, or findings in your own words.\n"
        "- Structure your answer clearly:\n"
        "  • For procedures/steps: use a numbered list.\n"
        "  • For explanations/concepts: use short paragraphs or bullet points.\n"
        "  • For simple factual questions (name, date, number): one concise sentence.\n"
        "- Write in plain, clear language that a student can easily understand.\n"
        "- Do NOT copy large raw text chunks from the context.\n"
        "- Do NOT repeat or rephrase the question.\n"
        "- ONLY use information found in the provided context — do not add outside knowledge.\n"
        "- If the context does not contain enough information to answer: say so in the same "
        "language the student used.\n\n"
        f"## DOCUMENT EXCERPTS:\n{context_text}\n\n"
        f"## STUDENT QUESTION:\n{question}\n\n"
        "## YOUR ANSWER:"
    )

    answer: Optional[str] = None
    ai_error: Optional[str] = None
    try:
        answer = _call_ai(prompt)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        ai_error = f"AI generation failed: {e}"

    # ── 7. Determine resolution status ───────────────────────────────────────
    is_unresolved = (
        answer is None
        or best_similarity < settings.CONFIDENCE_THRESHOLD
        or (answer and "could not find" in answer.lower())
    )
    is_resolved = "unresolved" if is_unresolved else "resolved"

    # ── 8. Save to chat history ───────────────────────────────────────────────
    chat = await ch_repo.create(
        user_id=user_id,
        question=question,
        answer=answer,
        sources=merged[:3],
        confidence_score=best_similarity,
        is_resolved=is_resolved,
    )

    # ── 9. Flag as unresolved if needed ──────────────────────────────────────
    if is_unresolved:
        try:
            await uq_repo.create(
                chat_history_id=chat.id,
                user_id=user_id,
                question=question,
                ai_attempt=answer,
                confidence_score=best_similarity,
            )
            logger.info(f"Question flagged as unresolved for admin review: '{question[:60]}'")
        except Exception as e:
            logger.warning(f"Failed to save unresolved question: {e}")

    return {
        "answer": answer,
        "sources": merged[:3],
        "confidence": best_similarity,
        "error": ai_error,
        "answered_by": "ai",
    }
