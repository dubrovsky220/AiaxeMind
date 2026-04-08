"""
Base parser interface for document parsing in AiaxeMind.

This module defines the abstract base class that all document parsers
must implement, ensuring a consistent interface across different
document formats (PDF, DOCX, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PageContent:
    """
    Content from a single page of a document.

    Attributes:
        page_number: Page number (1-indexed)
        text: All text content from this page
        headings: Section headings found on this page
        images: Images on this page (for future multi-modal support)
        tables: Tables on this page (for future multi-modal support)
    """

    page_number: int
    text: str
    headings: list[str] | None = None
    images: list[Any] | None = None
    tables: list[Any] | None = None


@dataclass
class DocumentMetadata:
    """
    Metadata extracted from a document.

    Attributes:
        title: Document title (from metadata or inferred from filename)
        author: Document author (if available)
        page_count: Total number of pages
        file_type: File format (e.g., '.pdf', '.docx')
        file_size: File size in bytes
        additional: Any additional format-specific metadata
    """

    title: str | None = None
    author: str | None = None
    page_count: int | None = None
    file_type: str | None = None
    file_size: int | None = None
    additional: dict[str, Any] | None = None


@dataclass
class ParsedDocument:
    """
    Complete result of document parsing.

    Attributes:
        text: Full document text (concatenated from all pages)
        metadata: Document metadata (title, author, page count, etc.)
        pages: Page-by-page content with headings (for citations)
        section_titles: All section/heading titles in document order
    """

    text: str
    metadata: DocumentMetadata
    pages: list[PageContent]
    section_titles: list[str] | None = None


class BaseParser(ABC):
    """
    Abstract base class for document parsers.

    All parser implementations must inherit from this class and implement
    the parse() method. This ensures a consistent interface for parsing
    different document formats.

    Example:
        class PDFParser(BaseParser):
            def parse(self, file_path: Path) -> ParsedDocument:
                # Implementation for PDF parsing
                pass
    """

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse a document and extract its content and metadata.

        Args:
            file_path: Path to the document file to parse

        Returns:
            ParsedDocument containing elements, metadata, and section titles

        Raises:
            UnsupportedFileTypeError: If the file type is not supported
            CorruptedFileError: If the file is corrupted or malformed
            ParsingError: For other parsing-related errors

        Note:
            Implementations should:
            - Validate file type before parsing
            - Extract text content preserving structure
            - Capture page numbers for each element
            - Extract metadata (title, author, page count)
            - Identify section titles/headings
            - Handle errors gracefully with descriptive messages
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """
        Return the set of file extensions this parser supports.

        Returns:
            Set of lowercase file extensions (e.g., {'.pdf', '.docx'})

        Example:
            def supported_extensions(self) -> set[str]:
                return {'.pdf'}
        """
        pass

    def supports_file_type(self, file_path: Path) -> bool:
        """
        Check if this parser supports the given file type.

        Args:
            file_path: Path to the file to check

        Returns:
            True if this parser can handle the file, False otherwise

        Note:
            Default implementation checks file extension. Subclasses
            can override to add more sophisticated detection (e.g.,
            magic number validation).
        """
        return file_path.suffix.lower() in self.supported_extensions()
