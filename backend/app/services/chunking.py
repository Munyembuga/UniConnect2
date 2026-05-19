"""
Text splitting utilities used by both the document and website pipelines.
"""
from typing import List
from loguru import logger


def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks.

    Tries LangChain's RecursiveCharacterTextSplitter first for semantically
    aware splitting; falls back to a simple word-based splitter if LangChain
    is not installed.
    """
    if not text or not text.strip():
        return []

    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
        )
        chunks = splitter.split_text(text)
        return [c for c in chunks if c.strip()]
    except Exception:
        logger.debug("LangChain unavailable — using simple word splitter")
        return _simple_word_split(text, chunk_size, overlap)


def _simple_word_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Word-based fallback splitter."""
    words = text.split()
    if not words:
        return []

    # Convert char-based sizes to approximate word counts
    words_per_chunk = max(1, chunk_size // 6)
    overlap_words = max(0, overlap // 6)

    chunks = []
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap_words
    return chunks
