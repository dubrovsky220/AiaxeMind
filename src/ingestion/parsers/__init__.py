"""
Document parsing module for AiaxeMind.

This module provides parsers for extracting text, metadata, and structure
from various document formats (PDF, DOCX, etc.).

Usage:
    from src.ingestion.parsers import ParserFactory

    factory = ParserFactory()
    document = factory.parse(Path("report.pdf"))

    for page in document.pages:
        print(f"Page {page.page_number}: {page.text[:100]}")
"""

from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)
from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    MetadataExtractionError,
    ParsingError,
    UnsupportedFileTypeError,
)
from src.ingestion.parsers.factory import ParserFactory
from src.ingestion.parsers.pymupdf_parser import PDFParser

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "PageContent",
    "DocumentMetadata",
    "PDFParser",
    "DOCXParser",
    "ParserFactory",
    "ParsingError",
    "UnsupportedFileTypeError",
    "CorruptedFileError",
    "MetadataExtractionError",
]
