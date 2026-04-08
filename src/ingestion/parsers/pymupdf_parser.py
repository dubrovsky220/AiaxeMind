"""
PDFParser implementation using PyMuPDF (fitz).

Fast, high-quality text extraction from PDF files with page-level organization
for accurate citations.
"""

import os
from pathlib import Path

import fitz

from src.core.logging_config import get_logger
from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)
from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    UnsupportedFileTypeError,
)

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents using PyMuPDF (fitz)."""

    def __init__(self) -> None:
        logger.info("PDFParser initialized")

    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info("Starting PDF parsing", extra={"file_path": str(file_path)})

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports_file_type(file_path):
            raise UnsupportedFileTypeError(file_path=str(file_path), file_type=file_path.suffix)

        try:
            doc = fitz.open(file_path)
            pages = self._extract_pages(doc)
            metadata = self._extract_metadata(file_path, doc)
            section_titles = self._extract_section_titles(pages)
            full_text = "\n\n".join(page.text for page in pages)
            doc.close()

            logger.info(
                "PDF parsing completed",
                extra={
                    "file_path": str(file_path),
                    "page_count": len(pages),
                    "section_count": len(section_titles) if section_titles else 0,
                },
            )

            return ParsedDocument(
                text=full_text,
                metadata=metadata,
                pages=pages,
                section_titles=section_titles,
            )

        except fitz.FileDataError as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                logger.error("PDF is encrypted", extra={"file_path": str(file_path)})
                raise CorruptedFileError(
                    file_path=str(file_path),
                    original_error=Exception("PDF is encrypted"),
                )
            logger.error("PDF file is corrupted", extra={"file_path": str(file_path)})
            raise CorruptedFileError(file_path=str(file_path), original_error=e)

        except UnsupportedFileTypeError:
            raise

        except Exception as e:
            logger.error("PDF parsing failed", extra={"file_path": str(file_path), "error": str(e)})
            raise CorruptedFileError(file_path=str(file_path), original_error=e)

    def _extract_pages(self, doc: fitz.Document) -> list[PageContent]:
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            headings = self._extract_headings_from_page(page)

            pages.append(
                PageContent(
                    page_number=page_num + 1,
                    text=text,
                    headings=headings if headings else None,
                    images=None,
                    tables=None,
                )
            )

        return pages

    def _extract_headings_from_page(self, page: fitz.Page) -> list[str]:
        headings = []
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    flags = span.get("flags", 0)

                    is_bold = flags & 2**4
                    is_potential_heading = (
                        size > 12 and is_bold and len(text) < 100 and text and text[0].isupper()
                    )

                    if is_potential_heading and text not in headings:
                        headings.append(text)

        return headings

    def _extract_section_titles(self, pages: list[PageContent]) -> list[str] | None:
        all_titles = []
        for page in pages:
            if page.headings:
                all_titles.extend(page.headings)
        return all_titles if all_titles else None

    def _extract_metadata(self, file_path: Path, doc: fitz.Document) -> DocumentMetadata:
        try:
            file_size = os.path.getsize(file_path)
            pdf_metadata = doc.metadata

            title = pdf_metadata.get("title") or None
            if title:
                title = title.strip()
            if not title:
                title = file_path.stem

            author = pdf_metadata.get("author") or None
            if author:
                author = author.strip()
                if not author:
                    author = None

            page_count = len(doc)

            additional = {}
            if pdf_metadata.get("subject"):
                additional["subject"] = pdf_metadata["subject"]
            if pdf_metadata.get("creator"):
                additional["creator"] = pdf_metadata["creator"]

            return DocumentMetadata(
                title=title,
                author=author,
                page_count=page_count,
                file_type=".pdf",
                file_size=file_size,
                additional=additional if additional else None,
            )

        except Exception as e:
            logger.warning("PDF metadata extraction failed", extra={"error": str(e)})
            return DocumentMetadata(
                title=file_path.stem,
                file_type=".pdf",
                file_size=os.path.getsize(file_path) if file_path.exists() else None,
                page_count=len(doc) if doc else None,
            )
