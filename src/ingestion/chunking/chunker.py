"""
Document chunking implementation for AiaxeMind.

This module provides intelligent document chunking with page-aware splitting,
metadata preservation, and cross-page overlap support for optimal RAG retrieval.

Key Features:
- Page-aware chunking: Tracks page numbers and section titles
- Cross-page overlap: Maintains context across page boundaries
- Configurable chunk size and overlap via environment variables
- Closest heading tracking: Associates each chunk with its nearest section title
- Edge case handling: Empty pages, short documents, missing metadata
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.logging_config import get_logger
from src.ingestion.parsers.base import PageContent, ParsedDocument

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)

# Configuration from environment variables with sensible defaults
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))


@dataclass
class ChunkData:
    """
    Data structure for a single chunk with metadata.

    Attributes:
        text: The chunk text content
        page: Page number where chunk originates (1-indexed, None if unknown)
        section_title: Closest section heading to this chunk (None if no headings)
        chunk_index: Sequential index of this chunk in the document (0-indexed)
    """

    text: str
    page: int | None
    section_title: str | None
    chunk_index: int


class DocumentChunker:
    """
    Document chunker with page-aware splitting and metadata preservation.

    Uses LangChain's RecursiveCharacterTextSplitter for intelligent text splitting
    while preserving document structure (pages, sections) for accurate citations.

    Strategy:
    1. Concatenate all pages into a single text stream with page markers
    2. Split using RecursiveCharacterTextSplitter with configured size/overlap
    3. Track page boundaries to assign page numbers to each chunk
    4. Find closest section heading for each chunk based on position
    5. Handle cross-page overlap naturally through concatenated text

    Example:
        chunker = DocumentChunker(chunk_size=512, chunk_overlap=64)
        chunks = chunker.chunk(parsed_document)
        for chunk in chunks:
            print(f"Page {chunk.page}: {chunk.text[:50]}...")
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        """
        Initialize DocumentChunker with configurable parameters.

        Args:
            chunk_size: Maximum characters per chunk (default from CHUNK_SIZE env var)
            chunk_overlap: Overlap between consecutive chunks (default from CHUNK_OVERLAP env var)

        Raises:
            ValueError: If chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be >= 0, got {chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be < chunk_size ({chunk_size})")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                r"\n\n",
                r"(?<=[.?!])\s+",
                r" ",
                r""
            ],
            is_separator_regex=True,
            add_start_index=True,
            keep_separator=True,
            strip_whitespace=False,
        )

        logger.info(
            "DocumentChunker initialized",
            extra={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
        )

    def chunk(self, parsed_doc: ParsedDocument) -> list[ChunkData]:
        """
        Chunk a parsed document into smaller fragments with metadata.

        Process:
        1. Filter out empty pages
        2. Build page position map (char offset -> page number)
        3. Build heading position map (char offset -> section title)
        4. Concatenate all page texts with newlines
        5. Split using RecursiveCharacterTextSplitter
        6. Assign page numbers and section titles based on chunk positions

        Args:
            parsed_doc: Parsed document with pages and metadata

        Returns:
            List of ChunkData objects with text, page, section_title, chunk_index

        Edge Cases:
        - Empty pages: Skipped (no chunks created)
        - Short documents (<chunk_size): Returns single chunk
        - Pages without headings: section_title = None
        - Cross-page chunks: Assigned to page where chunk starts
        """
        logger.info(
            "Starting document chunking",
            extra={
                "page_count": len(parsed_doc.pages),
                "total_chars": len(parsed_doc.text),
            },
        )

        # Filter out empty pages
        non_empty_pages = [page for page in parsed_doc.pages if page.text.strip()]

        if not non_empty_pages:
            logger.warning("Document has no non-empty pages, returning empty chunk list")
            return []

        page_map, heading_map = self._build_maps(non_empty_pages)

        # Concatenate all page texts
        full_text = " ".join(page.text for page in non_empty_pages)

        # Split text into chunks with position tracking
        raw_chunks = self.text_splitter.create_documents([full_text])

        # Create ChunkData objects with metadata
        chunks = []
        for idx, chunk_doc in enumerate(raw_chunks):
            # Use LangChain's tracked start_index instead of find()
            chunk_start = chunk_doc.metadata.get("start_index", 0)

            # Assign page number based on chunk start position
            page_num = self._find_page_for_position(chunk_start, page_map)

            # Find closest section title before chunk start
            section_title = self._find_closest_heading(chunk_start, heading_map)

            chunks.append(
                ChunkData(
                    text=chunk_doc.page_content.strip(),
                    page=page_num,
                    section_title=section_title,
                    chunk_index=idx,
                )
            )

        logger.info(
            "Document chunking completed",
            extra={
                "chunk_count": len(chunks),
                "avg_chunk_size": sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0,
            },
        )

        return chunks

    def _build_maps(self, pages: list[PageContent]) -> tuple[list[tuple[int, int]], list[tuple[int, str]]]:
        """
        Build maps of character positions to page numbers and character positions to section headings.
        """
        page_map = []
        heading_map = []
        current_offset = 0

        for page in pages:
            page_map.append((current_offset, page.page_number))

            if page.headings:
                for heading in page.headings:
                    heading_map.append((current_offset, heading))

            # + 1 for " " in " ".join(page.text for page in non_empty_pages)
            current_offset += len(page.text) + 1

        return page_map, heading_map

    def _find_page_for_position(self, position: int, page_map: list[tuple[int, int]]) -> int | None:
        """
        Find the page number for a given character position.

        Args:
            position: Character offset in concatenated text
            page_map: List of (char_offset, page_number) tuples

        Returns:
            Page number (1-indexed) or None if position is invalid
        """
        if position < 0 or not page_map:
            return None

        # Find the last page whose offset is <= position
        for i in range(len(page_map) - 1, -1, -1):
            offset, page_num = page_map[i]
            if offset <= position:
                return page_num

        return page_map[0][1] if page_map else None

    def _find_closest_heading(
        self, position: int, heading_map: list[tuple[int, str]]
    ) -> str | None:
        """
        Find the closest section heading before a given position.

        Args:
            position: Character offset in concatenated text
            heading_map: List of (char_offset, heading_text) tuples

        Returns:
            Heading text or None if no heading found before position
        """
        if not heading_map:
            return None

        # Find the last heading whose offset is <= position
        closest_heading = None
        for offset, heading in heading_map:
            if offset <= position:
                closest_heading = heading
            else:
                break

        return closest_heading


def main() -> None:
    """
    Manual test for DocumentChunker.

    Usage:
        uv run python -m src.ingestion.chunking.chunker <path_to_document>

    Example:
        uv run python -m src.ingestion.chunking.chunker tests/fixtures/documents/simple.pdf
    """
    import sys
    import time
    from pathlib import Path

    from src.core.logging_config import setup_logging
    from src.ingestion.parsers.factory import ParserFactory

    setup_logging(level="INFO")

    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.chunking.chunker <path_to_document>")
        print("\nExample:")
        print(
            "  uv run python -m src.ingestion.chunking.chunker tests/fixtures/documents/simple.pdf"
        )
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print("MANUAL CHUNKER TEST")
    print(f"{'=' * 80}")
    print(f"File: {file_path}")
    print(f"{'=' * 80}\n")

    # Step 1: Parse document
    print("Step 1: Parsing document...")
    parse_start = time.time()
    parser_factory = ParserFactory()
    parser = parser_factory.get_parser(file_path)
    parsed_doc = parser.parse(file_path)
    parse_time = time.time() - parse_start

    print("✓ Parsed successfully")
    print(f"  - Title: {parsed_doc.metadata.title}")
    print(f"  - Pages: {parsed_doc.metadata.page_count}")
    print(f"  - Total chars: {len(parsed_doc.text)}")
    print(
        f"  - Section titles: {len(parsed_doc.section_titles) if parsed_doc.section_titles else 0}"
    )
    print(f"  - Parse time: {parse_time:.3f}s")

    # Step 2: Chunk document
    print("\nStep 2: Chunking document...")
    chunk_start = time.time()
    chunker = DocumentChunker()
    chunks = chunker.chunk(parsed_doc)
    chunk_time = time.time() - chunk_start

    print("✓ Chunked successfully")
    print(f"  - Total chunks: {len(chunks)}")
    if chunks:
        print(f"  - Avg chunk size: {sum(len(c.text) for c in chunks) // len(chunks)} chars")
    print(f"  - Chunk time: {chunk_time:.3f}s")
    print(f"  - Total time: {parse_time + chunk_time:.3f}s")

    # Step 3: Display chunk details
    print(f"\n{'=' * 80}")
    print("CHUNK DETAILS")
    print(f"{'=' * 80}\n")

    for chunk in chunks[:5]:  # Show first 5 chunks
        print(f"Chunk #{chunk.chunk_index}")
        print(f"  Page: {chunk.page}")
        print(f"  Section: {chunk.section_title or '(no heading)'}")
        print(f"  Length: {len(chunk.text)} chars")
        print(f"  Preview: {chunk.text[:100].replace(chr(10), ' ')}...")
        print()

    if len(chunks) > 5:
        print(f"... and {len(chunks) - 5} more chunks\n")

    # Step 4: Verify edge cases
    print(f"{'=' * 80}")
    print("EDGE CASE VERIFICATION")
    print(f"{'=' * 80}\n")

    # Check page coverage
    pages_with_chunks = set(c.page for c in chunks if c.page is not None)
    print(f"✓ Pages with chunks: {sorted(pages_with_chunks)}")

    # Check section title coverage
    chunks_with_sections = [c for c in chunks if c.section_title is not None]
    print(f"✓ Chunks with section titles: {len(chunks_with_sections)}/{len(chunks)}")

    # Check chunk index continuity
    expected_indices = list(range(len(chunks)))
    actual_indices = [c.chunk_index for c in chunks]
    if expected_indices == actual_indices:
        print(f"✓ Chunk indices are continuous (0 to {len(chunks) - 1})")
    else:
        print("✗ Chunk indices have gaps!")

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
