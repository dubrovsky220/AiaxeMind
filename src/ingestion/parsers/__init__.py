"""
Document parsing module for AiaxeMind.

This module provides parsers for extracting text, metadata, and structure
from various document formats (PDF, DOCX, etc.).

Usage:
    from src.ingestion.parsers import ParserFactory

    factory = ParserFactory()
    document = factory.parse(Path("report.pdf"))

    for element in document.elements:
        print(f"Page {element.page_number}: {element.text}")
"""

from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    ParsedDocument,
    ParsedElement,
)
from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    MetadataExtractionError,
    ParsingError,
    UnsupportedFileTypeError,
)
from src.ingestion.parsers.factory import ParserFactory
from src.ingestion.parsers.unstructured_parser import UnstructuredParser

__all__ = [
    # Base classes and data structures
    "BaseParser",
    "ParsedDocument",
    "ParsedElement",
    "DocumentMetadata",
    # Concrete implementations
    "UnstructuredParser",
    "ParserFactory",
    # Exceptions
    "ParsingError",
    "UnsupportedFileTypeError",
    "CorruptedFileError",
    "MetadataExtractionError",
]
