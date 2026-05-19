"""
Chat / Q&A service.

Flow:
  1. Detect if the question is general/conversational (greetings, identity, date, etc.)
     → answer directly with Gemini, no RAG needed.
  2. Otherwise run the full RAG pipeline:
       a. Embed the question
       b. Search ChromaDB for relevant chunks
       c. Send context + question to Gemini for a grounded answer
"""
import re
import time
from datetime import date
from typing import Optional
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

def _call_gemini(prompt: str, retries: int = 2) -> str:
    """
    Call Gemini generate_content with automatic retry on 429 rate-limit errors.
    Waits the delay suggested by the API before retrying (max 2 retries).
    Raises the original exception if all retries are exhausted.
    """
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    last_exc = None
    for attempt in range(retries + 1):
        try:
            return model.generate_content(prompt).text.strip()
        except Exception as e:
            last_exc = e
            err_str = str(e)
            if "429" in err_str and attempt < retries:
                # Extract suggested retry delay from the error message if present
                wait = 15
                import re as _re
                m = _re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
                if m:
                    wait = min(int(m.group(1)), 60)
                logger.warning(f"Gemini 429 rate limit — waiting {wait}s before retry {attempt + 1}/{retries}")
                time.sleep(wait)
            else:
                raise
    raise last_exc


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def ask_question(question: str) -> dict:
    """
    Route the question:
      • general / conversational  → direct Gemini answer
      • knowledge-base question   → full RAG pipeline
    """

    # ── 0. General question shortcut ────────────────────────────────────────
    if _is_general_question(question):
        logger.info(f"General question detected, skipping RAG: '{question[:60]}'")
        return _answer_general_question(question)

    # ── 1. Embed the question ────────────────────────────────────────────────
    try:
        embed_service = EmbeddingService()
        query_vector = embed_service.embed_query(question)
    except RuntimeError:
        return {
            "answer": None,
            "sources": [],
            "confidence": 0.0,
            "error": (
                "Embedding service is not configured. "
                "Add your GEMINI_API_KEY to the .env file and restart."
            ),
        }
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return {
            "answer": None,
            "sources": [],
            "confidence": 0.0,
            "error": f"Failed to generate question embedding: {e}",
        }

    # ── 2. Search ChromaDB ───────────────────────────────────────────────────
    try:
        chroma = ChromaClient()
        results = chroma.query(
            settings.CHROMA_COLLECTION_NAME,
            query_embedding=query_vector,
            top_k=settings.SIMILARITY_TOP_K,
        )
    except Exception as e:
        logger.error(f"ChromaDB search failed: {e}")
        return {
            "answer": None,
            "sources": [],
            "confidence": 0.0,
            "error": (
                "Vector search failed. Make sure at least one document has been "
                "fully processed (is_processed == 'completed') before asking questions. "
                f"Detail: {e}"
            ),
        }

    # ── 3. Extract relevant passages ─────────────────────────────────────────
    documents_list = (results.get("documents") or [[]])[0]
    distances_list = (results.get("distances") or [[]])[0]

    if not documents_list:
        return {
            "answer": (
                "No documents have been indexed yet. "
                "Upload a document and wait for is_processed == 'completed', "
                "then try again."
            ),
            "sources": [],
            "confidence": 0.0,
            "error": None,
        }

    def to_similarity(dist: float) -> float:
        return max(0.0, round(1.0 - dist / 2.0, 3))

    best_similarity = to_similarity(distances_list[0]) if distances_list else 0.0

    relevant = [
        doc
        for doc, dist in zip(documents_list, distances_list)
        if to_similarity(dist) >= settings.CONFIDENCE_THRESHOLD
    ]

    if not relevant:
        return {
            "answer": (
                "I couldn't find information relevant enough to answer this question "
                "in the current knowledge base. "
                f"Best match similarity: {best_similarity:.0%}. "
                "Try rephrasing or upload more documents."
            ),
            "sources": [],
            "confidence": best_similarity,
            "error": None,
        }

    # ── 4. Build prompt & call Gemini ────────────────────────────────────────
    context_text = "\n\n---\n\n".join(relevant[:5])

    prompt = (
        "You are UniConnect, a helpful university assistant.\n\n"
        "Rules:\n"
        "- Answer using ONLY information found in the context below.\n"
        "- Be concise: 1–3 sentences maximum unless a list is clearly needed.\n"
        "- Answer the specific question asked — do not summarise the whole document.\n"
        "- If the context does not contain the answer, say so in one sentence.\n"
        "- Do not repeat the question or add unnecessary preamble.\n\n"
        "=== CONTEXT ===\n"
        f"{context_text}\n"
        "=== END CONTEXT ===\n\n"
        f"Question: {question}\n\n"
        "Concise answer:"
    )

    try:
        answer = _call_gemini(prompt)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return {
            "answer": None,
            "sources": relevant,
            "confidence": best_similarity,
            "error": f"AI generation failed: {e}",
        }

    return {
        "answer": answer,
        "sources": relevant[:3],
        "confidence": best_similarity,
        "error": None,
    }
