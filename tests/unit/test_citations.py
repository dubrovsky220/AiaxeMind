"""
Unit tests for citation validation and source metadata utilities.
"""

import pytest

from src.generation.citations import (
    build_sources_metadata,
    has_citations,
    validate_citation_numbers,
)
from src.generation.models import ContextChunk


class TestValidateCitationNumbers:
    """Tests for validate_citation_numbers function."""

    def test_valid_single_citation(self):
        """Test answer with single valid citation."""
        answer = "Machine learning is a subset of AI [1]."
        assert validate_citation_numbers(answer, num_sources=2) is True

    def test_valid_multiple_citations(self):
        """Test answer with multiple valid citations."""
        answer = "ML is AI subset [1]. Deep learning uses neural networks [2]."
        assert validate_citation_numbers(answer, num_sources=2) is True

    def test_valid_repeated_citations(self):
        """Test answer with repeated citation numbers."""
        answer = "ML is AI subset [1]. It learns from data [1]."
        assert validate_citation_numbers(answer, num_sources=1) is True

    def test_valid_adjacent_citations(self):
        """Test answer with adjacent citations."""
        answer = "This concept is fundamental [1][2]."
        assert validate_citation_numbers(answer, num_sources=2) is True

    def test_no_citations(self):
        """Test answer without citations (valid for 'no information' responses)."""
        answer = "The provided context doesn't contain information about this topic."
        assert validate_citation_numbers(answer, num_sources=2) is True

    def test_invalid_citation_too_high(self):
        """Test answer with citation number exceeding num_sources."""
        answer = "Machine learning is a subset of AI [5]."
        assert validate_citation_numbers(answer, num_sources=2) is False

    def test_invalid_citation_zero(self):
        """Test answer with citation number 0."""
        answer = "Machine learning is a subset of AI [0]."
        assert validate_citation_numbers(answer, num_sources=2) is False

    def test_mixed_valid_invalid_citations(self):
        """Test answer with mix of valid and invalid citations."""
        answer = "ML is AI subset [1]. Deep learning is advanced [10]."
        assert validate_citation_numbers(answer, num_sources=2) is False

    def test_empty_answer(self):
        """Test empty answer."""
        assert validate_citation_numbers("", num_sources=2) is True

    def test_citation_at_boundary(self):
        """Test citation number exactly at num_sources."""
        answer = "This is the last source [3]."
        assert validate_citation_numbers(answer, num_sources=3) is True


class TestHasCitations:
    """Tests for has_citations function."""

    def test_has_single_citation(self):
        """Test answer with single citation."""
        answer = "Machine learning is a subset of AI [1]."
        assert has_citations(answer) is True

    def test_has_multiple_citations(self):
        """Test answer with multiple citations."""
        answer = "ML is AI subset [1]. Deep learning uses neural networks [2]."
        assert has_citations(answer) is True

    def test_has_adjacent_citations(self):
        """Test answer with adjacent citations."""
        answer = "This concept is fundamental [1][2]."
        assert has_citations(answer) is True

    def test_no_citations(self):
        """Test answer without citations."""
        answer = "Machine learning is a subset of AI."
        assert has_citations(answer) is False

    def test_empty_answer(self):
        """Test empty answer."""
        assert has_citations("") is False

    def test_false_positive_brackets(self):
        """Test that regular brackets don't count as citations."""
        answer = "Use array[index] to access elements."
        assert has_citations(answer) is False

    def test_citation_with_letters(self):
        """Test that [1a] doesn't count as citation."""
        answer = "See section [1a] for details."
        assert has_citations(answer) is False


class TestBuildSourcesMetadata:
    """Tests for build_sources_metadata function."""

    def test_single_source(self):
        """Test building metadata for single source."""
        chunks = [
            ContextChunk(
                text="Machine learning is a subset of AI.",
                filename="ml_intro.pdf",
                page=1,
                score=0.95,
            )
        ]

        sources = build_sources_metadata(chunks)

        assert len(sources) == 1
        assert sources[0]["id"] == 1
        assert sources[0]["filename"] == "ml_intro.pdf"
        assert sources[0]["page"] == 1
        assert sources[0]["chunk_text"] == "Machine learning is a subset of AI."
        assert sources[0]["score"] == 0.95

    def test_multiple_sources(self):
        """Test building metadata for multiple sources."""
        chunks = [
            ContextChunk(text="First chunk", filename="doc1.pdf", page=1, score=0.95),
            ContextChunk(text="Second chunk", filename="doc2.pdf", page=2, score=0.88),
            ContextChunk(text="Third chunk", filename="doc3.pdf", page=3, score=0.75),
        ]

        sources = build_sources_metadata(chunks)

        assert len(sources) == 3
        assert sources[0]["id"] == 1
        assert sources[1]["id"] == 2
        assert sources[2]["id"] == 3
        assert sources[0]["filename"] == "doc1.pdf"
        assert sources[1]["filename"] == "doc2.pdf"
        assert sources[2]["filename"] == "doc3.pdf"

    def test_long_chunk_truncation(self):
        """Test that long chunks are truncated to 200 chars."""
        long_text = "a" * 300
        chunks = [
            ContextChunk(text=long_text, filename="doc.pdf", page=1, score=0.9)
        ]

        sources = build_sources_metadata(chunks)

        assert len(sources[0]["chunk_text"]) == 203  # 200 + "..."
        assert sources[0]["chunk_text"].endswith("...")

    def test_short_chunk_no_truncation(self):
        """Test that short chunks are not truncated."""
        short_text = "Short text"
        chunks = [
            ContextChunk(text=short_text, filename="doc.pdf", page=1, score=0.9)
        ]

        sources = build_sources_metadata(chunks)

        assert sources[0]["chunk_text"] == short_text
        assert not sources[0]["chunk_text"].endswith("...")

    def test_chunk_at_200_chars(self):
        """Test chunk exactly at 200 chars boundary."""
        text_200 = "a" * 200
        chunks = [
            ContextChunk(text=text_200, filename="doc.pdf", page=1, score=0.9)
        ]

        sources = build_sources_metadata(chunks)

        assert sources[0]["chunk_text"] == text_200
        assert not sources[0]["chunk_text"].endswith("...")

    def test_none_page_number(self):
        """Test source with None page number."""
        chunks = [
            ContextChunk(text="Text", filename="doc.txt", page=None, score=0.9)
        ]

        sources = build_sources_metadata(chunks)

        assert sources[0]["page"] is None

    def test_none_score(self):
        """Test source with None score."""
        chunks = [
            ContextChunk(text="Text", filename="doc.pdf", page=1, score=0.0)
        ]

        sources = build_sources_metadata(chunks)

        assert sources[0]["score"] == 0.0

    def test_score_rounding(self):
        """Test that scores are rounded to 4 decimal places."""
        chunks = [
            ContextChunk(text="Text", filename="doc.pdf", page=1, score=0.123456789)
        ]

        sources = build_sources_metadata(chunks)

        assert sources[0]["score"] == 0.1235

    def test_empty_chunks_list(self):
        """Test building metadata for empty chunks list."""
        sources = build_sources_metadata([])
        assert sources == []
