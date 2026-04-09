"""Unit tests for DocumentChunker."""

import pytest

from src.ingestion.chunking.chunker import ChunkData, DocumentChunker
from src.ingestion.parsers.base import DocumentMetadata, PageContent, ParsedDocument


class TestDocumentChunker:
    """Test suite for DocumentChunker."""

    @pytest.fixture
    def chunker(self) -> DocumentChunker:
        """Create DocumentChunker instance with default settings."""
        return DocumentChunker(chunk_size=100, chunk_overlap=20)

    def test_initialization_valid_params(self) -> None:
        """Test chunker initialization with valid parameters."""
        chunker = DocumentChunker(chunk_size=512, chunk_overlap=64)
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 64

    def test_initialization_invalid_chunk_size(self) -> None:
        """Test chunker rejects invalid chunk_size."""
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            DocumentChunker(chunk_size=0, chunk_overlap=20)

        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            DocumentChunker(chunk_size=-10, chunk_overlap=20)

    def test_initialization_invalid_chunk_overlap(self) -> None:
        """Test chunker rejects invalid chunk_overlap."""
        with pytest.raises(ValueError, match="chunk_overlap must be >= 0"):
            DocumentChunker(chunk_size=100, chunk_overlap=-5)

    def test_initialization_overlap_exceeds_size(self) -> None:
        """Test chunker rejects overlap >= chunk_size."""
        with pytest.raises(ValueError, match="chunk_overlap.*must be < chunk_size"):
            DocumentChunker(chunk_size=100, chunk_overlap=100)

        with pytest.raises(ValueError, match="chunk_overlap.*must be < chunk_size"):
            DocumentChunker(chunk_size=100, chunk_overlap=150)

    def test_chunk_empty_document(self, chunker: DocumentChunker) -> None:
        """Test chunking document with no pages returns empty list."""
        parsed_doc = ParsedDocument(
            text="",
            metadata=DocumentMetadata(title="Empty", page_count=0),
            pages=[],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)
        assert chunks == []

    def test_chunk_document_with_empty_pages(self, chunker: DocumentChunker) -> None:
        """Test chunking document with only empty pages returns empty list."""
        parsed_doc = ParsedDocument(
            text="",
            metadata=DocumentMetadata(title="Empty Pages", page_count=2),
            pages=[
                PageContent(page_number=1, text="   ", headings=None),
                PageContent(page_number=2, text="\n\n", headings=None),
            ],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)
        assert chunks == []

    def test_chunk_short_document(self, chunker: DocumentChunker) -> None:
        """Test chunking document shorter than chunk_size returns single chunk."""
        text = "Short document with less than 100 characters."
        parsed_doc = ParsedDocument(
            text=text,
            metadata=DocumentMetadata(title="Short", page_count=1),
            pages=[PageContent(page_number=1, text=text, headings=None)],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].page == 1
        assert chunks[0].section_title is None
        assert chunks[0].chunk_index == 0

    def test_chunk_document_with_multiple_pages(self, chunker: DocumentChunker) -> None:
        """Test chunking multi-page document assigns correct page numbers."""
        page1_text = "A" * 80
        page2_text = "B" * 80
        page3_text = "C" * 80

        parsed_doc = ParsedDocument(
            text=f"{page1_text}\n\n{page2_text}\n\n{page3_text}",
            metadata=DocumentMetadata(title="Multi-page", page_count=3),
            pages=[
                PageContent(page_number=1, text=page1_text, headings=None),
                PageContent(page_number=2, text=page2_text, headings=None),
                PageContent(page_number=3, text=page3_text, headings=None),
            ],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) > 1
        assert all(chunk.page in [1, 2, 3] for chunk in chunks)
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))

    def test_chunk_document_with_headings(self, chunker: DocumentChunker) -> None:
        """Test chunking document with headings assigns section_title correctly."""
        page1_text = "Introduction section. " + "A" * 100
        page2_text = "Methods section. " + "B" * 100

        parsed_doc = ParsedDocument(
            text=f"{page1_text}\n\n{page2_text}",
            metadata=DocumentMetadata(title="With Headings", page_count=2),
            pages=[
                PageContent(page_number=1, text=page1_text, headings=["Introduction"]),
                PageContent(page_number=2, text=page2_text, headings=["Methods"]),
            ],
            section_titles=["Introduction", "Methods"],
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) > 0
        first_chunk = chunks[0]
        assert first_chunk.section_title == "Introduction"

    def test_chunk_indices_are_continuous(self, chunker: DocumentChunker) -> None:
        """Test chunk indices are sequential starting from 0."""
        text = "A" * 500
        parsed_doc = ParsedDocument(
            text=text,
            metadata=DocumentMetadata(title="Long", page_count=1),
            pages=[PageContent(page_number=1, text=text, headings=None)],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) > 1
        expected_indices = list(range(len(chunks)))
        actual_indices = [chunk.chunk_index for chunk in chunks]
        assert actual_indices == expected_indices

    def test_chunk_preserves_text_content(self, chunker: DocumentChunker) -> None:
        """Test that all chunks contain parts of original text."""
        text = "Word " * 100
        parsed_doc = ParsedDocument(
            text=text,
            metadata=DocumentMetadata(title="Test", page_count=1),
            pages=[PageContent(page_number=1, text=text, headings=None)],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) > 0
        for chunk in chunks:
            assert "Word" in chunk.text

    def test_chunk_respects_size_limit(self, chunker: DocumentChunker) -> None:
        """Test that most chunks respect the chunk_size limit."""
        text = "Word " * 200
        parsed_doc = ParsedDocument(
            text=text,
            metadata=DocumentMetadata(title="Test", page_count=1),
            pages=[PageContent(page_number=1, text=text, headings=None)],
            section_titles=None,
        )
        chunks = chunker.chunk(parsed_doc)

        oversized_chunks = [c for c in chunks if len(c.text) > chunker.chunk_size * 1.2]
        assert len(oversized_chunks) < len(chunks) * 0.1

    def test_chunk_data_structure(self) -> None:
        """Test ChunkData dataclass structure."""
        chunk = ChunkData(
            text="Sample text",
            page=1,
            section_title="Introduction",
            chunk_index=0,
        )
        assert chunk.text == "Sample text"
        assert chunk.page == 1
        assert chunk.section_title == "Introduction"
        assert chunk.chunk_index == 0

    def test_chunk_with_none_page(self) -> None:
        """Test ChunkData accepts None for page."""
        chunk = ChunkData(
            text="Sample text",
            page=None,
            section_title=None,
            chunk_index=0,
        )
        assert chunk.page is None
        assert chunk.section_title is None

    def test_chunk_repeated_text_across_pages(self, chunker: DocumentChunker) -> None:
        """Test chunking with identical text on different pages assigns correct page numbers."""
        repeated_text = "Key concept: This is an important definition. " * 3

        parsed_doc = ParsedDocument(
            text=f"{repeated_text}\n\n{repeated_text}\n\n{repeated_text}",
            metadata=DocumentMetadata(title="Repeated Text", page_count=3),
            pages=[
                PageContent(page_number=1, text=repeated_text, headings=["Section 1"]),
                PageContent(page_number=2, text=repeated_text, headings=["Section 2"]),
                PageContent(page_number=3, text=repeated_text, headings=["Section 3"]),
            ],
            section_titles=["Section 1", "Section 2", "Section 3"],
        )
        chunks = chunker.chunk(parsed_doc)

        assert len(chunks) >= 3

        pages_found = set(chunk.page for chunk in chunks)
        assert 1 in pages_found, "Should have chunks from page 1"
        assert 2 in pages_found, "Should have chunks from page 2"
        assert 3 in pages_found, "Should have chunks from page 3"

        sections_found = set(chunk.section_title for chunk in chunks if chunk.section_title)
        assert "Section 1" in sections_found, "Should have chunks with Section 1"
        assert "Section 2" in sections_found, "Should have chunks with Section 2"
        assert "Section 3" in sections_found, "Should have chunks with Section 3"
