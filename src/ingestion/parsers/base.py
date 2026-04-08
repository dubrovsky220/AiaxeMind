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
class ParsedElement:
    """
    Represents a single parsed element from a document.

    Elements can be text blocks, titles, tables, etc. Each element
    preserves its position in the document for citation purposes.

    Attributes:
        text: The text content of the element
        element_type: Type of element (e.g., 'text', 'title', 'table')
        page_number: Page number where this element appears (1-indexed)
        metadata: Additional element-specific metadata
    """

    text: str
    element_type: str
    page_number: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class DocumentMetadata:
    """
    Metadata extracted from a document.

    Attributes:
        title: Document title (from metadata or inferred)
        author: Document author (if available)
        page_count: Total number of pages
        file_type: File format (e.g., 'pdf', 'docx')
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

    Contains all parsed elements and extracted metadata, providing
    a unified structure for downstream processing (chunking, embedding).

    Attributes:
        elements: List of parsed elements in document order
        metadata: Document metadata
        section_titles: List of section/heading titles found in the document
    """

    elements: list[ParsedElement]
    metadata: DocumentMetadata
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

