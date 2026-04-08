"""
UnstructuredParser implementation for PDF and DOCX documents.

This parser uses the unstructured.io library to extract text, metadata,
and structure from PDF and DOCX files, preserving page numbers and
section titles for citation purposes.
"""

import os
from pathlib import Path
from typing import Any

from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf

from src.core.logging_config import get_logger
from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    ParsedDocument,
    ParsedElement,
)
from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    UnsupportedFileTypeError,
)

logger = get_logger(__name__)


class UnstructuredParser(BaseParser):
    """
    Parser for PDF and DOCX documents using unstructured.io.

    Features:
    - Extracts text content with preserved structure
    - Captures page numbers for each element (citations)
    - Identifies section titles and headings
    - Extracts document metadata (title, author, page count)
    - Handles tables and preserves formatting

    Supported formats:
    - PDF (.pdf)
    - Microsoft Word (.docx, .doc)

    Example:
        parser = UnstructuredParser()
        document = parser.parse(Path("report.pdf"))

        for element in document.elements:
            print(f"Page {element.page_number}: {element.text[:50]}")
    """

    def __init__(self, strategy: str = "hi_res") -> None:
        """
        Initialize UnstructuredParser.

        Args:
            strategy: Parsing strategy for PDFs
                - "hi_res": Best quality, uses layout analysis (slower)
                - "fast": Fast text extraction (for extractable text)
                - "ocr_only": OCR for scanned documents
                - "auto": Automatically choose based on content
        """
        self.strategy = strategy
        logger.info("UnstructuredParser initialized", extra={"strategy": strategy})

    def supported_extensions(self) -> set[str]:
        """
        Return supported file extensions.

        Returns:
            Set of lowercase file extensions
        """
        return {".pdf", ".docx", ".doc"}

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse a PDF or DOCX document.

        Args:
            file_path: Path to the document file

        Returns:
            ParsedDocument with elements, metadata, and section titles

        Raises:
            UnsupportedFileTypeError: If file type is not PDF or DOCX
            CorruptedFileError: If file is corrupted or cannot be parsed

        Note:
            - Page numbers are 1-indexed
            - Section titles are extracted from Title elements
            - Metadata extraction is best-effort (may return None for missing fields)
        """
        logger.info(
            "Starting document parsing",
            extra={"file_path": str(file_path), "strategy": self.strategy},
        )

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate file type
        if not self.supports_file_type(file_path):
            raise UnsupportedFileTypeError(file_path=str(file_path), file_type=file_path.suffix)

        try:
            # Parse based on file type
            if file_path.suffix.lower() == ".pdf":
                elements = self._parse_pdf(file_path)
            elif file_path.suffix.lower() in {".docx", ".doc"}:
                elements = self._parse_docx(file_path)
            else:
                raise UnsupportedFileTypeError(file_path=str(file_path), file_type=file_path.suffix)

            # Extract parsed elements
            parsed_elements = self._extract_elements(elements)

            # Extract section titles
            section_titles = self._extract_section_titles(elements)

            # Extract metadata
            metadata = self._extract_metadata(file_path, elements)

            logger.info(
                "Document parsing completed",
                extra={
                    "file_path": str(file_path),
                    "element_count": len(parsed_elements),
                    "section_count": len(section_titles) if section_titles else 0,
                    "page_count": metadata.page_count,
                },
            )

            return ParsedDocument(
                elements=parsed_elements, metadata=metadata, section_titles=section_titles
            )

        except UnsupportedFileTypeError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(
                "Document parsing failed", extra={"file_path": str(file_path), "error": str(e)}
            )
            raise CorruptedFileError(file_path=str(file_path), original_error=e)

    def _parse_pdf(self, file_path: Path) -> list[Any]:
        """
        Parse PDF using unstructured.io.

        Args:
            file_path: Path to PDF file

        Returns:
            List of unstructured elements
        """
        logger.debug("Parsing PDF", extra={"file_path": str(file_path), "strategy": self.strategy})

        return partition_pdf(
            filename=str(file_path),
            strategy=self.strategy,
            include_page_breaks=True,  # Preserve page numbers
            infer_table_structure=True,  # Extract tables
            coordinates=True,  # Enable bounding box extraction
        )

    def _parse_docx(self, file_path: Path) -> list[Any]:
        """
        Parse DOCX using unstructured.io.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of unstructured elements
        """
        logger.debug("Parsing DOCX", extra={"file_path": str(file_path)})

        return partition_docx(
            filename=str(file_path),
            include_page_breaks=True,  # Preserve page numbers
        )

    def _extract_elements(self, elements: list[Any]) -> list[ParsedElement]:
        """
        Convert unstructured elements to ParsedElement objects.

        Args:
            elements: List of unstructured elements

        Returns:
            List of ParsedElement objects
        """
        parsed_elements = []

        for element in elements:
            # Skip page breaks (they're markers, not content)
            if element.category == "PageBreak":
                continue

            # Extract page number
            page_number = None
            if hasattr(element.metadata, "page_number"):
                page_number = element.metadata.page_number

            # Extract additional metadata
            element_metadata: dict[str, Any] = {}

            # Add coordinates if available
            if hasattr(element.metadata, "coordinates") and element.metadata.coordinates:
                element_metadata["coordinates"] = element.metadata.coordinates.points

            # Add HTML representation for tables
            if element.category == "Table" and hasattr(element.metadata, "text_as_html"):
                element_metadata["html"] = element.metadata.text_as_html

            parsed_element = ParsedElement(
                text=element.text,
                element_type=element.category,
                page_number=page_number,
                metadata=element_metadata if element_metadata else None,
            )
            parsed_elements.append(parsed_element)

        return parsed_elements

    def _extract_section_titles(self, elements: list[Any]) -> list[str] | None:
        """
        Extract section titles from Title elements.

        Args:
            elements: List of unstructured elements

        Returns:
            List of section title strings, or None if no titles found
        """
        titles = []

        for element in elements:
            if element.category == "Title":
                titles.append(element.text)

        logger.debug("Extracted section titles", extra={"title_count": len(titles)})

        return titles if titles else None

    def _extract_metadata(self, file_path: Path, elements: list[Any]) -> DocumentMetadata:
        """
        Extract document metadata.

        Args:
            file_path: Path to the document
            elements: List of unstructured elements

        Returns:
            DocumentMetadata object

        Note:
            Metadata extraction is best-effort. Missing fields will be None.
        """
        try:
            # Get file size
            file_size = os.path.getsize(file_path)

            # Infer title from first Title element
            title = None
            for element in elements:
                if element.category == "Title":
                    title = element.text
                    break

            # Count pages by finding max page_number
            page_count = None
            max_page = 0
            for element in elements:
                if hasattr(element.metadata, "page_number") and element.metadata.page_number:
                    max_page = max(max_page, element.metadata.page_number)
            if max_page > 0:
                page_count = max_page

            # Extract author and other metadata from first element
            author = None
            additional_metadata: dict[str, Any] = {}

            if elements:
                first_element = elements[0]

                # Try to get filename and filetype
                if hasattr(first_element.metadata, "filename"):
                    additional_metadata["filename"] = first_element.metadata.filename
                if hasattr(first_element.metadata, "filetype"):
                    additional_metadata["filetype"] = first_element.metadata.filetype
                if hasattr(first_element.metadata, "languages"):
                    additional_metadata["languages"] = first_element.metadata.languages

            metadata = DocumentMetadata(
                title=title,
                author=author,  # unstructured.io doesn't extract author
                page_count=page_count,
                file_type=file_path.suffix.lower(),
                file_size=file_size,
                additional=additional_metadata if additional_metadata else None,
            )

            logger.debug(
                "Extracted metadata",
                extra={"title": title, "page_count": page_count, "file_size": file_size},
            )

            return metadata

        except Exception as e:
            logger.warning("Metadata extraction failed, using defaults", extra={"error": str(e)})
            # Return minimal metadata on failure
            return DocumentMetadata(
                file_type=file_path.suffix.lower(),
                file_size=os.path.getsize(file_path) if file_path.exists() else None,
            )
