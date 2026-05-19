"""
Chat / Q&A service.
Takes a plain-text question, finds the most relevant document chunks in
ChromaDB, and uses Gemini to generate a grounded answer.
"""
from typing import Optional
from loguru import logger

from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.chromadb_client import ChromaClient


async def ask_question(question: str) -> dict:
    """
    Full RAG pipeline for a single question:
      1. Embed the question with Gemini
      2. Search ChromaDB for the most relevant chunks
      3. Send context + question to Gemini for an answer
      4. Return the answer and the source passages

    Returns a dict with keys:
        answer      – the AI-generated answer (str)
        sources     – list of source text passages used (list[str])
        confidence  – rough similarity score of the best match (float 0–1)
        error       – error message if something failed (str | None)
    """

    # ── 1. Embed the question ────────────────────────────────────────────────
    try:
        embed_service = EmbeddingService()
        query_vector = embed_service.embed_query(question)
    except RuntimeError as e:
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
    metadatas_list = (results.get("metadatas") or [[]])[0]

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

    # Convert L2 distance to a 0–1 similarity score.
    # For unit-norm vectors: L2 distance ∈ [0, 2], similarity = 1 - dist/2
    def to_similarity(dist: float) -> float:
        return max(0.0, round(1.0 - dist / 2.0, 3))

    best_similarity = to_similarity(distances_list[0]) if distances_list else 0.0

    # Keep only passages above the confidence threshold
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
    context_text = "\n\n---\n\n".join(relevant[:5])  # max 5 passages

    prompt = f"""You are a helpful university assistant. Answer the student's question using ONLY the context below.
If the context does not contain enough information to fully answer the question, say so clearly — do not make up information.

=== CONTEXT FROM KNOWLEDGE BASE ===
{context_text}
=== END CONTEXT ===

Student question: {question}

Answer:"""

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        answer = response.text.strip()
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
        "sources": relevant[:3],   # return top 3 source passages to the frontend
        "confidence": best_similarity,
        "error": None,
    }
