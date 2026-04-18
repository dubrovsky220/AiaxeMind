"""
Citation validation and source metadata utilities.

This module provides utilities for validating citation format and building
source metadata for RAG responses.

Key Features:
- Citation number validation
- Source metadata construction
- Logging support for citation quality monitoring

Usage:
    from src.generation.citations import validate_citation_numbers, build_sources_metadata

    # Validate citations
    is_valid = validate_citation_numbers(answer, num_sources)

    # Build metadata
    sources = build_sources_metadata(context_chunks)
"""

import re

from src.core.logging_config import get_logger
from src.generation.models import ContextChunk

logger = get_logger(__name__)


def validate_citation_numbers(answer: str, num_sources: int) -> bool:
    """
    Validate that citation numbers in answer are within valid range.

    Checks that all citation numbers [1], [2], etc. in the answer are:
    - Greater than 0
    - Less than or equal to num_sources

    Args:
        answer: Generated answer text
        num_sources: Number of available source chunks

    Returns:
        True if no citations OR all citations are valid
        False if any citation number is out of range

    Example:
        >>> validate_citation_numbers("ML is AI subset [1].", 2)
        True
        >>> validate_citation_numbers("ML is AI subset [5].", 2)
        False
        >>> validate_citation_numbers("ML is AI subset.", 2)
        True
    """
    pattern = re.compile(r'\[(\d+)\]')
    citations = pattern.findall(answer)

    if not citations:
        return True  # No citations is valid (e.g., "no information" response)

    for cite_num in citations:
        num = int(cite_num)
        if num > num_sources or num < 1:
            logger.warning(
                "Invalid citation number found",
                extra={
                    "citation_number": num,
                    "num_sources": num_sources,
                    "answer_preview": answer[:200],
                },
            )
            return False

    return True


def has_citations(answer: str) -> bool:
    """
    Check if answer contains any citations.

    Args:
        answer: Generated answer text

    Returns:
        True if answer contains at least one citation [N]
        False otherwise

    Example:
        >>> has_citations("ML is AI subset [1].")
        True
        >>> has_citations("ML is AI subset.")
        False
    """
    pattern = re.compile(r'\[\d+\]')
    return bool(pattern.search(answer))


def build_sources_metadata(context_chunks: list[ContextChunk]) -> list[dict]:
    """
    Build source metadata array for API response.

    Constructs structured metadata for each source chunk including:
    - Citation ID (1-indexed)
    - Filename
    - Page number (if available)
    - Preview of chunk text (truncated to 200 chars)
    - Relevance score

    Args:
        context_chunks: List of context chunks used for generation

    Returns:
        List of source metadata dictionaries

    Example:
        >>> chunks = [
        ...     ContextChunk(text="ML is...", filename="ml.pdf", page=1, score=0.95)
        ... ]
        >>> sources = build_sources_metadata(chunks)
        >>> sources[0]["id"]
        1
        >>> sources[0]["filename"]
        'ml.pdf'
    """
    sources = []

    for i, chunk in enumerate(context_chunks, start=1):
        # Truncate chunk text for preview
        chunk_preview = chunk.text
        if len(chunk_preview) > 200:
            chunk_preview = chunk_preview[:200] + "..."

        source = {
            "id": i,
            "filename": chunk.filename,
            "page": chunk.page,
            "chunk_text": chunk_preview,
            "score": round(chunk.score, 4) if chunk.score is not None else None,
        }

        sources.append(source)

    logger.debug(
        "Built source metadata",
        extra={"num_sources": len(sources)},
    )

    return sources
